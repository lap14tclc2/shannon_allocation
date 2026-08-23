from portfolio.analytics import drawdown_from_twr_indices, period_returns


def test_single_snapshot_is_baseline_not_zero_performance():
    snapshot = {
        "snapshot_date": "2026-08-24",
        "daily_return": None,
        "twr_index": 1.0,
    }
    returns = period_returns([snapshot])
    assert returns == {"daily": None, "mtd": None, "ytd": None, "since_inception": None}
    assert drawdown_from_twr_indices([1.0]) == (None, None)


def test_two_snapshots_allow_observed_return_and_drawdown():
    rows = [
        {"snapshot_date": "2026-08-24", "daily_return": None, "twr_index": 1.0},
        {"snapshot_date": "2026-08-25", "daily_return": -0.05, "twr_index": 0.95},
    ]
    returns = period_returns(rows)
    assert returns["daily"] == -0.05
    assert abs(returns["since_inception"] + 0.05) < 1e-12
    current, worst = drawdown_from_twr_indices([1.0, 0.95])
    assert abs(current + 0.05) < 1e-12
    assert abs(worst + 0.05) < 1e-12
