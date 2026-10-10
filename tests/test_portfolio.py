import pandas as pd
import pytest

from idxbot.backtest.engine import BacktestParams
from idxbot.portfolio import PortfolioParams, run_portfolio

BERSIH = BacktestParams(
    initial_capital=1_000_000, fee_buy=0, fee_sell=0, slippage=0,
    lot_size=100, max_position_pct=1.0,
)


def frame(opens, closes, signals):
    idx = pd.bdate_range("2024-01-01", periods=len(opens))
    return pd.DataFrame(
        {
            "open": [float(x) for x in opens],
            "close": [float(x) for x in closes],
            "signal": signals,
            "reason": ["tes"] * len(opens),
        },
        index=idx,
    )


def test_batas_jumlah_posisi():
    sinyal = ["BUY", "HOLD", "HOLD"]
    frames = {
        "A": frame([1000] * 3, [1000] * 3, sinyal),
        "B": frame([1000] * 3, [1000] * 3, sinyal),
    }
    hasil = run_portfolio(frames, BERSIH, PortfolioParams(max_positions=1, max_position_pct=1.0))
    assert [p["ticker"] for p in hasil.open_positions] == ["A"]


def test_batas_porsi_per_saham():
    frames = {"A": frame([1000] * 3, [1000] * 3, ["BUY", "HOLD", "HOLD"])}
    hasil = run_portfolio(frames, BERSIH, PortfolioParams(max_positions=3, max_position_pct=0.5))
    assert hasil.open_positions[0]["shares"] == 500


def test_lot_tidak_terjangkau_dilewati():
    frames = {"A": frame([6000] * 3, [6000] * 3, ["BUY", "HOLD", "HOLD"])}
    hasil = run_portfolio(frames, BERSIH, PortfolioParams(max_positions=3, max_position_pct=0.5))
    assert hasil.open_positions == []
    assert hasil.equity["equity"].iloc[-1] == 1_000_000


def test_round_trip_dan_pnl():
    frames = {
        "A": frame(
            [1000, 1000, 1100, 1100],
            [1000, 1050, 1100, 1100],
            ["BUY", "SELL", "HOLD", "HOLD"],
        )
    }
    hasil = run_portfolio(frames, BERSIH, PortfolioParams(max_positions=3, max_position_pct=1.0))
    assert len(hasil.trades) == 1
    t = hasil.trades.iloc[0]
    assert t["ticker"] == "A"
    assert t["pnl"] == pytest.approx(100_000)
    assert hasil.equity["equity"].iloc[-1] == pytest.approx(1_100_000)


def test_tidak_look_ahead():
    sinyal = ["BUY", "HOLD", "HOLD", "SELL", "HOLD", "BUY"] + ["HOLD"] * 4
    asli = {k: frame([1000] * 10, [1000] * 10, sinyal) for k in ("A", "B")}
    sinyal2 = sinyal[:6] + ["SELL"] * 4
    harga2 = [1000] * 6 + [5000] * 4
    diubah = {k: frame(harga2, harga2, sinyal2) for k in ("A", "B")}
    pp = PortfolioParams(max_positions=2, max_position_pct=0.5)
    a = run_portfolio(asli, BERSIH, pp).equity["equity"].iloc[:6]
    b = run_portfolio(diubah, BERSIH, pp).equity["equity"].iloc[:6]
    pd.testing.assert_series_equal(a, b)


def test_hanya_tanggal_yang_dimiliki_semua_saham():
    a = frame([1000] * 5, [1000] * 5, ["HOLD"] * 5)
    b = frame([1000] * 5, [1000] * 5, ["HOLD"] * 5)
    b = b.drop(b.index[2])
    hasil = run_portfolio({"A": a, "B": b}, BERSIH, PortfolioParams())
    assert len(hasil.equity) == 4


def test_kas_tidak_pernah_negatif():
    opens = [1000 + 10 * i for i in range(10)]
    sinyal = ["BUY", "HOLD", "SELL", "BUY", "HOLD", "SELL", "BUY", "HOLD", "SELL", "HOLD"]
    frames = {k: frame(opens, opens, sinyal) for k in ("A", "B")}
    hasil = run_portfolio(frames, BacktestParams(), PortfolioParams())
    assert (hasil.equity["cash"] >= 0).all()
    assert len(hasil.trades) >= 3