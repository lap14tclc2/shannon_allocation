"""Unit + sanity tests for the joint optimizer (P4).

Run:  cd python && python -m pytest backtest/tests/test_optimizer.py -q
"""

from __future__ import annotations

import random

import pandas as pd
import pytest

from backtest import BacktestParams, load_panel
from backtest.candidate import (
    Candidate,
    assert_valid_candidate,
    random_allocation_days,
    random_candidate,
    repair_allocation_days,
    resolve_allocation_dates,
    validate_candidate,
)
from backtest.optimize.nsga2 import dominates, nsga2, fast_non_dominated_sort
from backtest.optimize.robustness import timing_neighbourhood
from backtest.optimize.walkforward import halving, make_windows
from backtest.optimize.search import random_search
from backtest.optimize.evaluate import EvaluationCache, config_fingerprint, evaluate_candidate, objectives
from backtest.simulation import simulate_combination

UNIVERSE = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L"]
GOOD = Candidate(("A", "B", "C", "D", "E"), (40, 100, 160, 220))


# --------------------------------------------------------------------------- candidate
class TestCandidateValidation:
    def test_valid(self):
        assert validate_candidate(GOOD, set(UNIVERSE)) == []

    def test_too_few_symbols(self):
        c = Candidate(("A", "B", "C", "D"), (40, 100, 160, 220))
        assert any("symbol count" in e for e in validate_candidate(c, set(UNIVERSE)))

    def test_duplicate_symbols(self):
        c = Candidate(("A", "B", "B", "C", "D", "E"), (40, 100, 160, 220))
        assert any("duplicate" in e for e in validate_candidate(c, set(UNIVERSE)))

    def test_symbol_not_in_universe(self):
        c = Candidate(("A", "B", "C", "D", "ZZZ"), (40, 100, 160, 220))
        assert any("not in universe" in e for e in validate_candidate(c, set(UNIVERSE)))

    def test_wrong_number_of_times(self):
        c = Candidate(("A", "B", "C", "D", "E"), (40, 100, 160))
        assert any("exactly 4" in e for e in validate_candidate(c, set(UNIVERSE)))

    def test_unordered_times(self):
        c = Candidate(("A", "B", "C", "D", "E"), (100, 40, 160, 220))
        assert any("not ordered" in e for e in validate_candidate(c, set(UNIVERSE)))

    def test_min_gap(self):
        c = Candidate(("A", "B", "C", "D", "E"), (40, 42, 160, 220))
        assert any("minimum gap" in e for e in validate_candidate(c, set(UNIVERSE)))

    def test_assert_valid_raises(self):
        with pytest.raises(ValueError):
            assert_valid_candidate(Candidate(("A",), (40, 100, 160, 220)), set(UNIVERSE))


class TestGeneratorsAndMapping:
    def test_random_candidate_always_valid(self):
        rng = random.Random(7)
        for _ in range(200):
            c = random_candidate(rng, UNIVERSE, min_gap=40, max_day=252)
            assert validate_candidate(c, set(UNIVERSE), 252, 40) == []

    def test_random_allocation_days_respected(self):
        rng = random.Random(3)
        for _ in range(100):
            days = random_allocation_days(rng, 40, 252)
            assert len(days) == 4
            assert days == sorted(days)
            assert all(1 <= d <= 252 for d in days)
            assert all(b - a >= 40 for a, b in zip(days, days[1:]))

    def test_repair(self):
        assert repair_allocation_days([10, 11, 30, 200], 40, 252) is not None
        assert repair_allocation_days([10, 11, 12, 13], 200, 252) is None

    def test_resolve_mapping(self):
        import pandas as pd

        dates = [pd.Timestamp(f"2023-{m:02d}-{d:02d}") for m in (1, 1, 1, 1) for d in (2, 3, 4, 5)]
        dates = sorted(set(dates))[:20]
        resolved, mapping = resolve_allocation_dates(GOOD, dates)
        assert len(resolved) == 4
        assert mapping[0]["requested_index"] == GOOD.allocation_days[0]
        assert mapping[0]["resolved_date"]
        # resolved dates must be trading days present in the calendar
        assert all(pd.Timestamp(x) in set(dates) for x in resolved)


# --------------------------------------------------------------------------- operators / nsga2
class TestNsga2:
    def test_dominates(self):
        assert dominates([1, 2, 3], [1, 2, 2])
        assert not dominates([1, 2, 2], [1, 2, 3])
        assert not dominates([1, 2, 3], [1, 2, 3])

    def test_sort(self):
        fronts = fast_non_dominated_sort([[0, 0], [1, 1], [0.5, 0.5]])
        assert len(fronts) == 3

    def test_nsga2_beats_random_on_planted_problem(self):
        """Plant one good timing region; NSGA-II should find better max objective than random search."""
        rng_opt = random.Random(1)
        rng_rand = random.Random(1)

        def planted(c):
            # objective peaks at an achievable schedule (gaps >= 40)
            target = [40, 100, 160, 220]
            dist = sum(abs(a - b) for a, b in zip(c.allocation_days, target))
            return [100.0 - dist]

        init = [random_candidate(rng_opt, UNIVERSE, 40, 252) for _ in range(60)]
        pop, fit, _ = nsga2(init, planted, UNIVERSE, rng_opt, population_size=30, generations=20,
                            progress=False)
        best_nsga = max(f[0] for f in fit)

        random_cands = [random_candidate(rng_rand, UNIVERSE, 40, 252) for _ in range(30 * 20)]
        best_rand = max(planted(c)[0] for c in random_cands)

        assert best_nsga >= best_rand
        assert best_nsga > 80  # found near the planted optimum


class TestCostsAndLookahead:
    @pytest.fixture(scope="class")
    def data(self):
        params = BacktestParams(fee_buy_bps=15, fee_sell_bps=15, tax_sell_bps=10, slippage_bps=5,
                                execution_lag=1)
        prices, universe = load_panel(params)
        return params, prices, universe

    def test_net_le_gross(self, data):
        params, prices, universe = data
        r = simulate_combination(["BMP", "BWE", "HHV", "MBB", "MSB", "VSH"], prices, params)
        assert r.twr_annualized - r.gross_twr_annualized <= 1e-9

    def test_no_lookahead_execution(self, data):
        params, prices, universe = data
        r = simulate_combination(["BMP", "BWE", "HHV", "MBB", "MSB", "VSH"], prices, params)
        for a in r.allocations:
            assert a["execution_date"] > a["signal_date"]
        # execution price must be the NEXT trading day's close
        dates = list(prices.index)
        by_date = {d.normalize(): i for i, d in enumerate(dates)}
        for a in r.allocations:
            sig = pd.Timestamp(a["signal_date"])
            nxt = dates[by_date[sig] + 1]
            for rec in a["recommendations"]:
                if rec["execution_price"] is not None:
                    assert rec["execution_date"] == str(nxt.date())

    def test_costs_tracked(self, data):
        params, prices, universe = data
        r = simulate_combination(["BMP", "BWE", "HHV", "MBB", "MSB", "VSH"], prices, params)
        assert r.transaction_cost > 0
        assert r.cost_pct_of_nav > 0

    def test_zero_costs_net_equals_gross(self, data):
        params = BacktestParams(fee_buy_bps=0, fee_sell_bps=0, tax_sell_bps=0, slippage_bps=0,
                                execution_lag=1)
        prices, universe = load_panel(params)
        r = simulate_combination(["BMP", "BWE", "HHV", "MBB", "MSB", "VSH"], prices, params)
        assert r.transaction_cost == 0.0
        assert abs(r.twr_annualized - r.gross_twr_annualized) < 1e-6

    def test_invalid_candidate_cannot_evaluate(self, data):
        params, prices, universe = data
        bad = Candidate(("A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K"), (40, 100, 160, 220))
        with pytest.raises(ValueError):
            assert_valid_candidate(bad, set(universe), 252, 40)


# --------------------------------------------------------------------------- walk-forward / halving / robustness
class TestRobustness:
    def test_make_windows(self):
        import pandas as pd

        dates = [pd.Timestamp("2023-01-01") + pd.Timedelta(days=i) for i in range(1000)]
        ws = make_windows(dates, 300, 200, 200, 100)
        assert len(ws) >= 3
        assert ws[0]["train"][0] < ws[0]["val"][0] < ws[0]["test"][0]

    def test_halving_reduces(self):
        rng = random.Random(1)
        cands = [random_candidate(rng, UNIVERSE, 40, 252) for _ in range(50)]

        def fake_eval(c, level):
            return {"robust_return": float(sum(c.allocation_days) % 100)}

        kept, eliminated = halving(cands, fake_eval, rng, cutoffs=(25, 10), progress=False)
        assert len(kept) == 10

    def test_timing_spike_detected(self):
        base = Candidate(("A", "B", "C", "D", "E"), (70, 111, 152, 193))
        spike_schedule = (70, 112, 152, 193)  # +1 on day2 stays within min-gap

        def spike_eval(c):
            if c.allocation_days == spike_schedule:
                return {"net_twr_annualized_pct": 40.0}
            return {"net_twr_annualized_pct": 5.0}

        res = timing_neighbourhood(base, spike_eval, radius=2)
        assert res["isolated_spike"] is True


# --------------------------------------------------------------------------- reproducibility
class TestReproducibility:
    def test_same_seed_same_random_search(self):
        def run(seed):
            rng = random.Random(seed)
            keys = []
            for _ in range(20):
                keys.append(random_candidate(rng, UNIVERSE, 40, 252).key())
            return keys

        assert run(1) == run(1)
        assert run(1) != run(2)

    def test_fingerprint_stable(self):
        assert config_fingerprint(BacktestParams()) == config_fingerprint(BacktestParams())
        assert config_fingerprint(BacktestParams(fee_buy_bps=50)) != config_fingerprint(BacktestParams())


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))