import numpy as np
import pandas as pd
import pytest

from idxbot.backtest.engine import BacktestResult
from idxbot.backtest.metrics import compute_metrics, max_drawdown_pct, trade_stats


def test_max_drawdown():
    eq = pd.Series([100.0, 120.0, 90.0, 110.0])
    assert max_drawdown_pct(eq) == pytest.approx(-25.0)


def test_max_drawdown_nol_jika_selalu_naik():
    assert max_drawdown_pct(pd.Series([100.0, 110.0, 120.0])) == 0


def test_trade_stats():
    trades = pd.DataFrame(
        {"pnl": [100.0, -50.0, 200.0, -50.0], "holding_days": [10, 5, 20, 5]}
    )
    s = trade_stats(trades)
    assert s["n_trades"] == 4
    assert s["win_rate"] == pytest.approx(50.0)
    assert s["avg_win"] == pytest.approx(150.0)
    assert s["avg_loss"] == pytest.approx(-50.0)
    assert s["risk_reward"] == pytest.approx(3.0)
    assert s["profit_factor"] == pytest.approx(3.0)


def test_tanpa_transaksi():
    s = trade_stats(pd.DataFrame())
    assert s["n_trades"] == 0
    assert np.isnan(s["win_rate"])


def test_compute_metrics_return():
    idx = pd.bdate_range("2024-01-01", periods=3)
    equity = pd.DataFrame(
        {"equity": [1_000_000.0, 1_050_000.0, 1_100_000.0]}, index=idx
    )
    hasil = BacktestResult(trades=pd.DataFrame(), equity=equity, open_position=None)
    m = compute_metrics(hasil, 1_000_000)
    assert m["return_pct"] == pytest.approx(10.0)
    assert m["max_drawdown_pct"] == 0
