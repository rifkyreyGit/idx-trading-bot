import pandas as pd
import pytest

from idxbot.backtest.engine import BacktestParams, round_to_tick, run_backtest

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


def test_pembulatan_fraksi_harga():
    assert round_to_tick(2003, "up") == 2010
    assert round_to_tick(2003, "down") == 2000
    assert round_to_tick(1002, "up") == 1005
    assert round_to_tick(6012, "down") == 6000


def test_eksekusi_di_open_hari_berikutnya():
    df = frame(
        opens=[1000, 1000, 1100, 1100],
        closes=[1000, 1050, 1100, 1100],
        signals=["BUY", "SELL", "HOLD", "HOLD"],
    )
    hasil = run_backtest(df, BERSIH)
    assert len(hasil.trades) == 1
    t = hasil.trades.iloc[0]
    assert t["entry_date"] == df.index[1] and t["entry_price"] == 1000
    assert t["exit_date"] == df.index[2] and t["exit_price"] == 1100
    assert t["lots"] == 10
    assert t["pnl"] == pytest.approx(100_000)
    assert hasil.equity["equity"].iloc[-1] == pytest.approx(1_100_000)
    assert hasil.open_position is None


def test_biaya_dan_pembulatan_lot():
    p = BacktestParams(
        initial_capital=1_000_000, fee_buy=0.0015, fee_sell=0, slippage=0,
        lot_size=100, max_position_pct=1.0,
    )
    df = frame(
        opens=[1000, 1000, 1100, 1100],
        closes=[1000, 1050, 1100, 1100],
        signals=["BUY", "SELL", "HOLD", "HOLD"],
    )
    hasil = run_backtest(df, p)
    # fee membuat 10 lot tidak cukup -> hanya 9 lot (900 lembar)
    assert hasil.trades.iloc[0]["lots"] == 9
    assert hasil.equity["equity"].iloc[-1] == pytest.approx(1_088_650)


def test_sinyal_hari_terakhir_tidak_dieksekusi():
    df = frame([1000] * 3, [1000] * 3, ["HOLD", "HOLD", "BUY"])
    hasil = run_backtest(df, BERSIH)
    assert hasil.trades.empty
    assert hasil.open_position is None
    assert hasil.equity["equity"].iloc[-1] == 1_000_000


def test_sell_tanpa_posisi_diabaikan():
    df = frame([1000] * 3, [1000] * 3, ["SELL", "SELL", "HOLD"])
    hasil = run_backtest(df, BERSIH)
    assert hasil.trades.empty
    assert (hasil.equity["equity"] == 1_000_000).all()


def test_tidak_look_ahead():
    sinyal = ["BUY", "HOLD", "HOLD", "SELL", "HOLD", "BUY"] + ["HOLD"] * 4
    asli = frame([1000] * 10, [1000] * 10, sinyal)
    # ubah drastis semua data mulai baris ke-7 (indeks 6)
    opens = [1000] * 6 + [5000] * 4
    closes = [1000] * 6 + [5000] * 4
    sinyal2 = sinyal[:6] + ["SELL"] * 4
    diubah = frame(opens, closes, sinyal2)

    a = run_backtest(asli, BERSIH).equity["equity"].iloc[:6]
    b = run_backtest(diubah, BERSIH).equity["equity"].iloc[:6]
    pd.testing.assert_series_equal(a, b)
