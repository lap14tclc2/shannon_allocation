from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from backtest.alpha import alpha_score_table, select_alpha_symbols
from backtest.config import BacktestParams
from backtest.optimize.eligibility import assess_live_eligibility, live_risk_reward_score


class TestDynamicAlpha(unittest.TestCase):
    def _panel(self, n=420):
        dates = pd.bdate_range("2023-01-02", periods=n)
        t = np.arange(n, dtype=float)
        # Three persistent leaders, two correlated clones, and slower diversifiers.
        data = {
            "AAA": 100 * np.exp(0.0015 * t),
            "AAB": 100 * np.exp(0.00148 * t) * (1 + 0.001 * np.sin(t / 7)),
            "BBB": 100 * np.exp(0.0012 * t) * (1 + 0.01 * np.sin(t / 11)),
            "CCC": 100 * np.exp(0.0010 * t) * (1 + 0.012 * np.cos(t / 13)),
            "DDD": 100 * np.exp(0.0007 * t) * (1 + 0.015 * np.sin(t / 9)),
            "EEE": 100 * np.exp(0.0004 * t),
            "FFF": 100 * np.exp(-0.0001 * t) * (1 + 0.02 * np.sin(t / 5)),
        }
        return pd.DataFrame(data, index=dates)

    def _params(self):
        return BacktestParams(
            dynamic_alpha_enabled=True,
            dynamic_alpha_portfolio_size=5,
            alpha_min_observations=60,
            alpha_short_lookback=63,
            alpha_medium_lookback=126,
            alpha_long_lookback=252,
            alpha_correlation_lookback=126,
            alpha_max_pair_correlation=0.80,
        )

    def test_selection_is_strictly_past(self):
        panel = self._panel()
        params = self._params()
        pos = 300
        before = select_alpha_symbols(panel, list(panel.columns), pos, params)

        mutated = panel.copy()
        # Change only rows at/after the signal position. A look-ahead bug would
        # allow these absurd future prices to alter the historical selection.
        mutated.iloc[pos:, mutated.columns.get_loc("FFF")] *= 1000.0
        after = select_alpha_symbols(mutated, list(mutated.columns), pos, params)
        self.assertEqual(before.symbols, after.symbols)
        self.assertEqual(before.scores, after.scores)

    def test_growth_leaders_rank_above_loser(self):
        panel = self._panel()
        params = self._params()
        table = alpha_score_table(panel, list(panel.columns), 350, params)
        self.assertGreater(table.loc["AAA", "alpha_score"], table.loc["FFF", "alpha_score"])
        selected = select_alpha_symbols(panel, list(panel.columns), 350, params)
        self.assertEqual(len(selected.symbols), 5)
        self.assertIn("AAA", selected.symbols)

    def test_correlation_filter_can_defer_near_clone(self):
        panel = self._panel()
        params = self._params()
        params.alpha_max_pair_correlation = 0.70
        selected = select_alpha_symbols(panel, list(panel.columns), 350, params, portfolio_size=5)
        self.assertEqual(len(selected.symbols), 5)
        # AAA/AAB are almost identical. At least one should require a relaxed
        # threshold or be displaced by a more diversifying name.
        accepted = selected.diagnostics.get("accepted_at_threshold", {})
        if "AAA" in selected.symbols and "AAB" in selected.symbols:
            self.assertTrue(
                accepted.get("AAA", 0) > 0.70 or accepted.get("AAB", 0) > 0.70
            )


class TestSoftLivePolicy(unittest.TestCase):
    def test_low_calmar_is_soft_not_binary_failure(self):
        train = {
            "net_twr_annualized_pct": 3.0,
            "max_drawdown_pct": -25.0,
            "calmar": 0.12,
        }
        validation = {
            "p10_net_twr": 4.0,
            "median_net_twr": 8.0,
            "worst_mdd": -20.0,
        }
        recent = {
            "net_twr_annualized_pct": 1.0,
            "max_drawdown_pct": -15.0,
            "calmar": 0.07,
        }
        eligible, reasons = assess_live_eligibility(
            train, validation, recent,
            min_train_twr_pct=0.0,
            min_validation_p10_twr_pct=0.0,
            min_recent_twr_pct=0.0,
        )
        self.assertTrue(eligible, reasons)
        quality = live_risk_reward_score(train, validation, recent)
        self.assertGreaterEqual(quality["overall"], 0.0)
        self.assertLess(quality["overall"], 60.0)

    def test_catastrophic_recent_loss_remains_hard_failure(self):
        train = {"net_twr_annualized_pct": 10.0, "calmar": 1.0}
        validation = {"p10_net_twr": 5.0, "median_net_twr": 10.0, "worst_mdd": -10.0}
        recent = {"net_twr_annualized_pct": -8.0, "max_drawdown_pct": -15.0, "calmar": -0.5}
        eligible, reasons = assess_live_eligibility(
            train, validation, recent,
            min_validation_p10_twr_pct=0.0,
            min_recent_twr_pct=0.0,
        )
        self.assertFalse(eligible)
        self.assertTrue(any("recent_validation_twr_below_-5%" in r for r in reasons))


if __name__ == "__main__":
    unittest.main()
