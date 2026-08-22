"""Unit + sanity tests for the joint growth optimizer.

Run: cd python && python -m pytest backtest/tests/test_optimizer.py -q
"""

from __future__ import annotations

import random

import pandas as pd
import pytest

from backtest import BacktestParams, load_panel
from backtest.candidate import (
    Candidate,
    MAX_ALLOCATIONS,
    MIN_ALLOCATIONS,
    assert_valid_candidate,
    random_allocation_days,
    random_candidate,
    repair_allocation_days,
    resolve_allocation_dates,
    schedule_for_window,
    validate_candidate,
)
from backtest.optimize.evaluate import config_fingerprint
from backtest.optimize.nsga2 import dominates, fast_non_dominated_sort, nsga2
from backtest.optimize.robustness import timing_neighbourhood
from backtest.optimize.walkforward import evaluate_robust, halving, make_windows
from backtest.simulation import simulate_combination

UNIVERSE = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L"]
GOOD = Candidate(("A", "B", "C", "D", "E"), (40, 100, 160, 220))


class TestCandidateValidation:
    def test_four_event_legacy_schedule_still_valid(self):
        assert validate_candidate(GOOD, set(UNIVERSE)) == []

    def test_variable_event_counts_are_valid(self):
        one = Candidate(("A", "B", "C", "D", "E"), (120,))
        three = Candidate(("A", "B", "C", "D", "E"), (30, 115, 200))
        six = Candidate(("A", "B", "C", "D", "E"), (1, 41, 81, 121, 161, 201))
        assert validate_candidate(one, set(UNIVERSE)) == []
        assert validate_candidate(three, set(UNIVERSE)) == []
        assert validate_candidate(six, set(UNIVERSE)) == []

    def test_too_many_allocation_events_rejected(self):
        c = Candidate(("A", "B", "C", "D", "E"), (1, 36, 71, 106, 141, 176, 211))
        assert any("allocation count" in e for e in validate_candidate(c, set(UNIVERSE), 252, 30))

    def test_too_few_symbols(self):
        c = Candidate(("A", "B", "C", "D"), (120,))
        assert any("symbol count" in e for e in validate_candidate(c, set(UNIVERSE)))

    def test_duplicate_symbols(self):
        c = Candidate(("A", "B", "B", "C", "D", "E"), (120,))
        assert any("duplicate" in e for e in validate_candidate(c, set(UNIVERSE)))

    def test_symbol_not_in_universe(self):
        c = Candidate(("A", "B", "C", "D", "ZZZ"), (120,))
        assert any("not in universe" in e for e in validate_candidate(c, set(UNIVERSE)))

    def test_unordered_times(self):
        c = Candidate(("A", "B", "C", "D", "E"), (120, 40, 200))
        assert any("not ordered" in e for e in validate_candidate(c, set(UNIVERSE)))

    def test_min_gap(self):
        c = Candidate(("A", "B", "C", "D", "E"), (40, 42, 160))
        assert any("minimum gap" in e for e in validate_candidate(c, set(UNIVERSE)))

    def test_cyclic_min_gap_violation(self):
        c = Candidate(("A", "B", "C", "D", "E"), (22, 93, 203, 252))
        assert any("cyclic" in e for e in validate_candidate(c, set(UNIVERSE), 252, 40))

    def test_assert_valid_raises(self):
        with pytest.raises(ValueError):
            assert_valid_candidate(Candidate(("A",), (120,)), set(UNIVERSE))


class TestGeneratorsAndMapping:
    def test_random_candidate_always_valid_and_explores_frequency(self):
        rng = random.Random(7)
        counts = set()
        for _ in range(300):
            c = random_candidate(rng, UNIVERSE, min_gap=40, max_day=252)
            counts.add(len(c.allocation_days))
            assert validate_candidate(c, set(UNIVERSE), 252, 40) == []
        assert min(counts) == MIN_ALLOCATIONS
        assert max(counts) == MAX_ALLOCATIONS
        assert len(counts) >= 4

    def test_random_allocation_days_respects_variable_count_and_cyclic_gap(self):
        rng = random.Random(3)
        for _ in range(200):
            days = random_allocation_days(rng, 40, 252)
            assert MIN_ALLOCATIONS <= len(days) <= MAX_ALLOCATIONS
            assert days == sorted(days)
            assert all(1 <= d <= 252 for d in days)
            if len(days) >= 2:
                assert all(b - a >= 40 for a, b in zip(days, days[1:]))
                assert 252 + days[0] - days[-1] >= 40

    def test_explicit_allocation_count(self):
        rng = random.Random(11)
        for n in range(1, 7):
            days = random_allocation_days(rng, 40, 252, allocation_count=n)
            assert len(days) == n
            c = Candidate(("A", "B", "C", "D", "E"), tuple(days))
            assert validate_candidate(c, set(UNIVERSE), 252, 40) == []

    def test_non_252_calendar(self):
        rng = random.Random(11)
        for _ in range(200):
            days = random_allocation_days(rng, 40, 241)
            c = Candidate(("A", "B", "C", "D", "E"), tuple(days))
            assert validate_candidate(c, set(UNIVERSE), 241, 40) == []

    def test_repair_variable_schedule(self):
        assert repair_allocation_days([10], 40, 252) == (10,)
        assert repair_allocation_days([10, 60, 120], 40, 252) is not None
        assert repair_allocation_days([10, 11, 12, 13], 200, 252) is None

    def test_resolve_mapping_variable_count(self):
        dates = list(pd.bdate_range("2023-01-02", periods=252))
        c = Candidate(("A", "B", "C", "D", "E"), (30, 115, 200))
        resolved, mapping = resolve_allocation_dates(c, dates)
        assert len(resolved) == 3
        assert len(mapping) == 3
        assert [m["requested_index"] for m in mapping] == [30, 115, 200]
        assert all(pd.Timestamp(x) in set(dates) for x in resolved)


class TestNsga2:
    def test_dominates(self):
        assert dominates([1, 2, 3], [1, 2, 2])
        assert not dominates([1, 2, 2], [1, 2, 3])
        assert not dominates([1, 2, 3], [1, 2, 3])

    def test_sort(self):
        fronts = fast_non_dominated_sort([[0, 0], [1, 1], [0.5, 0.5]])
        assert len(fronts) == 3

    def test_nsga2_keeps_variable_schedules_valid(self):
        rng = random.Random(1)
        init = [random_candidate(rng, UNIVERSE, 40, 252, portfolio_size=7) for _ in range(30)]

        def planted(c):
            # Reward growth proxy plus a mild preference for three events. The
            # purpose is validity/evolution, not proving an investment edge.
            return [20.0 - abs(len(c.allocation_days) - 3) * 2.0 + sum(c.allocation_days) / 1000.0]

        pop, fit, _ = nsga2(
            init, planted, UNIVERSE, rng,
            population_size=24, generations=8, progress=False, portfolio_size=7,
        )
        assert len(pop) == 24
        for c in pop:
            assert len(c.symbols) == 7
            assert MIN_ALLOCATIONS <= len(c.allocation_days) <= MAX_ALLOCATIONS
            assert validate_candidate(c, set(UNIVERSE), 252, 40, portfolio_size=7) == []

    def test_nsga2_timing_only_keeps_symbols_fixed(self):
        rng = random.Random(3)
        fixed = ("A", "B", "C", "D", "E")
        init = [random_candidate(rng, UNIVERSE, 40, 252, fixed_symbols=list(fixed)) for _ in range(20)]

        def objective(c):
            return [10.0 + len(c.allocation_days)]

        pop, _fit, _ = nsga2(
            init, objective, UNIVERSE, rng,
            population_size=20, generations=8, progress=False,
            fixed_symbols=list(fixed),
        )
        for c in pop:
            assert c.symbols == fixed
            assert validate_candidate(c, set(UNIVERSE), 252, 40) == []


class TestCostsAndLookahead:
    """Real-data/local tests; CI excludes this class because private VN data is absent."""

    @pytest.fixture(scope="class")
    def data(self):
        params = BacktestParams(
            fee_buy_bps=15, fee_sell_bps=15, tax_sell_bps=10,
            slippage_bps=5, execution_lag=1,
        )
        prices, universe = load_panel(params)
        return params, prices, universe

    def test_net_le_gross(self, data):
        params, prices, _ = data
        r = simulate_combination(["BMP", "BWE", "HHV", "MBB", "MSB", "VSH"], prices, params)
        assert r.twr_annualized - r.gross_twr_annualized <= 1e-9

    def test_no_lookahead_execution(self, data):
        params, prices, _ = data
        r = simulate_combination(["BMP", "BWE", "HHV", "MBB", "MSB", "VSH"], prices, params)
        dates = list(prices.index)
        by_date = {d.normalize(): i for i, d in enumerate(dates)}
        for a in r.allocations:
            assert a["execution_date"] > a["signal_date"]
            sig = pd.Timestamp(a["signal_date"])
            nxt = dates[by_date[sig] + 1]
            for rec in a["recommendations"]:
                if rec["execution_price"] is not None:
                    assert rec["execution_date"] == str(nxt.date())

    def test_costs_tracked(self, data):
        params, prices, _ = data
        r = simulate_combination(["BMP", "BWE", "HHV", "MBB", "MSB", "VSH"], prices, params)
        assert r.transaction_cost > 0
        assert r.cost_pct_of_nav > 0

    def test_zero_costs_net_equals_gross(self, data):
        params = BacktestParams(
            fee_buy_bps=0, fee_sell_bps=0, tax_sell_bps=0,
            slippage_bps=0, execution_lag=1,
        )
        prices, _ = load_panel(params)
        r = simulate_combination(["BMP", "BWE", "HHV", "MBB", "MSB", "VSH"], prices, params)
        assert r.transaction_cost == 0.0
        assert abs(r.twr_annualized - r.gross_twr_annualized) < 1e-6


class TestRobustness:
    def test_make_windows(self):
        dates = [pd.Timestamp("2023-01-01") + pd.Timedelta(days=i) for i in range(1000)]
        ws = make_windows(dates, 300, 200, 200, 100)
        assert len(ws) >= 3
        assert ws[0]["train"][0] < ws[0]["val"][0] < ws[0]["test"][0]

    def test_halving_reduces(self):
        rng = random.Random(1)
        cands = [random_candidate(rng, UNIVERSE, 40, 252) for _ in range(50)]

        def fake_eval(c, level):
            return {"robust_return": float(sum(c.allocation_days) % 100)}

        kept, _eliminated = halving(cands, fake_eval, rng, cutoffs=(25, 10), progress=False)
        assert len(kept) == 10

    def test_robust_coverage_policy_rejects_partial(self):
        def flaky(_c, w):
            if w["val"] == 1:
                return None
            return {
                "net_twr_annualized_pct": 10.0,
                "sharpe": 1.0,
                "max_drawdown_pct": -5.0,
                "cdar95_pct": -4.0,
            }

        c = random_candidate(random.Random(2), UNIVERSE, 40, 252)
        windows = [{"val": 0}, {"val": 1}, {"val": 2}]
        assert evaluate_robust(c, flaky, windows, min_windows=3) is None
        rob = evaluate_robust(c, flaky, windows, min_windows=None)
        assert rob is not None and rob["n_windows"] == 2

    def test_timing_neighbourhood_handles_non_four_schedule(self):
        base = Candidate(("A", "B", "C", "D", "E"), (30, 115, 200))

        def fake(c):
            return {"net_twr_annualized_pct": 10.0 + sum(c.allocation_days) / 1000.0}

        res = timing_neighbourhood(base, fake, radius=2)
        assert res["n_neighbours"] > 0


def _synthetic_panel(n=261, seed=7, syms=("A", "B", "C", "D", "E")):
    import numpy as np

    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2021-01-04", periods=n)
    return pd.DataFrame(
        {s: 10000.0 * np.cumprod(1 + 0.0005 * rng.standard_normal(n)) for s in syms},
        index=dates,
    )


class TestEvaluationMethodology:
    def test_quarterly_baseline_remains_valid_benchmark(self):
        from backtest.optimize.run import _quarterly_baseline

        for max_day in (252, 241, 230):
            days = _quarterly_baseline(max_day)
            errs = validate_candidate(
                Candidate(("A", "B", "C", "D", "E"), days),
                set(UNIVERSE), max_day, 40,
            )
            assert errs == []

    def test_variable_schedule_can_drive_simulation(self):
        prices = _synthetic_panel(n=420)
        c = Candidate(("A", "B", "C", "D", "E"), (40, 130, 220))
        alloc_dates = schedule_for_window(c, prices.index)
        params = BacktestParams(
            minimum_observations=20,
            lookback_days=63,
            risk_overlay_enabled=False,
        )
        result = simulate_combination(
            list(c.symbols), prices, params, allocation_dates=alloc_dates,
        )
        assert result.error is None
        assert result.allocation_schedule


class TestReproducibility:
    def test_same_seed_same_random_search_space(self):
        def run(seed):
            rng = random.Random(seed)
            return [random_candidate(rng, UNIVERSE, 40, 252).key() for _ in range(30)]

        assert run(1) == run(1)
        assert run(1) != run(2)

    def test_fingerprint_stable(self):
        assert config_fingerprint(BacktestParams()) == config_fingerprint(BacktestParams())
        assert config_fingerprint(BacktestParams(fee_buy_bps=50)) != config_fingerprint(BacktestParams())


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
