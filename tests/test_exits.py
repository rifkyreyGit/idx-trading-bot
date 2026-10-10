import pandas as pd
import pytest

from idxbot.backtest.engine import BacktestParams
from idxbot.portfolio import PortfolioParams, run_portfolio

BERSIH = BacktestParams(
    initial_capital=1_000_000, fee_buy=0, fee_sell=0, slippage=0,
    lot_size=100, max_position_pct=1.0,
)
PP = PortfolioParams(
    max_positions=1, max_position_pct=1.0, stop_loss_pct=0.02, take_profit_pct=0.04
)


def frame(opens, highs, lows, closes, signals):
    idx = pd.bdate_range("2024-01-01", periods=len(opens))
    return pd.DataFrame(
        {
            "open": [float(x) for x in opens],
            "high": [float(x) for x in highs],
            "low": [float(x) for x in lows],
            "close": [float(x) for x in closes],
            "signal": signals,
            "reason": ["tes"] * len(opens),
        },
        index=idx,
    )


def test_stop_loss_tersentuh():
    f = frame([1000] * 3, [1000, 1005, 1000], [1000, 970, 1000],
              [1000, 990, 1000], ["BUY", "HOLD", "HOLD"])
    t = run_portfolio({"A": f}, BERSIH, PP).trades.iloc[0]
    assert t["exit_type"] == "stop" and t["exit_price"] == 980
    assert t["pnl"] == pytest.approx(-20_000)


def test_take_profit_tercapai():
    f = frame([1000] * 3, [1000, 1045, 1000], [1000, 995, 1000],
              [1000, 1040, 1000], ["BUY", "HOLD", "HOLD"])
    t = run_portfolio({"A": f}, BERSIH, PP).trades.iloc[0]
    assert t["exit_type"] == "target" and t["exit_price"] == 1040
    assert t["pnl"] == pytest.approx(40_000)


def test_stop_dan_target_di_hari_sama_stop_menang():
    f = frame([1000] * 3, [1000, 1050, 1000], [1000, 970, 1000],
              [1000, 1000, 1000], ["BUY", "HOLD", "HOLD"])
    t = run_portfolio({"A": f}, BERSIH, PP).trades.iloc[0]
    assert t["exit_type"] == "stop"


def test_gap_turun_keluar_di_open():
    f = frame([1000, 1000, 950, 950], [1000, 1005, 960, 950],
              [1000, 990, 940, 950], [1000, 1000, 945, 950],
              ["BUY", "HOLD", "HOLD", "HOLD"])
    t = run_portfolio({"A": f}, BERSIH, PP).trades.iloc[0]
    assert t["exit_price"] == 950  # bukan 980


def test_tidak_beli_lagi_selama_sinyal_buy_yang_sama():
    f = frame([1000] * 5, [1000, 1005, 1005, 1005, 1005],
              [1000, 970, 995, 995, 995], [1000, 990, 1000, 1000, 1000],
              ["BUY"] * 5)
    hasil = run_portfolio({"A": f}, BERSIH, PP)
    assert len(hasil.trades) == 1
    assert hasil.open_positions == []