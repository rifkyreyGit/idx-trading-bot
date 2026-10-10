import pandas as pd
from pandas.testing import assert_series_equal

from idxbot.indicators import add_indicators
from idxbot.strategy import StrategyParams, evaluate_row, generate_signals

P = StrategyParams()


def row(**kw):
    dasar = dict(close=100.0, ma_fast=100.0, ma_slow=100.0, rsi=50.0, vol_ratio=1.0)
    dasar.update(kw)
    return pd.Series(dasar)


def test_buy_saat_tren_naik_dan_konfirmasi_cukup():
    sinyal, alasan = evaluate_row(
        row(ma_fast=110, ma_slow=100, close=115, rsi=55, vol_ratio=1.2), P
    )
    assert sinyal == "BUY"
    assert "Tren naik" in alasan


def test_tren_naik_tanpa_konfirmasi_adalah_hold():
    sinyal, _ = evaluate_row(
        row(ma_fast=110, ma_slow=100, close=105, rsi=80, vol_ratio=0.5), P
    )
    assert sinyal == "HOLD"


def test_satu_konfirmasi_saja_tidak_cukup_untuk_buy():
    # hanya close > MA cepat yang terpenuhi; RSI dan volume gagal
    sinyal, _ = evaluate_row(
        row(ma_fast=110, ma_slow=100, close=115, rsi=80, vol_ratio=0.5), P
    )
    assert sinyal == "HOLD"


def test_sell_saat_tren_turun_dan_ada_konfirmasi():
    sinyal, alasan = evaluate_row(
        row(ma_fast=90, ma_slow=100, close=85, rsi=35, vol_ratio=1.5), P
    )
    assert sinyal == "SELL"
    assert "Tren turun" in alasan


def test_rsi_rendah_saja_tanpa_tren_turun_bukan_sell():
    sinyal, _ = evaluate_row(
        row(ma_fast=110, ma_slow=100, close=95, rsi=30, vol_ratio=0.5), P
    )
    assert sinyal != "SELL"


def test_data_belum_cukup_adalah_hold():
    sinyal, alasan = evaluate_row(row(ma_slow=float("nan")), P)
    assert sinyal == "HOLD"
    assert "belum cukup" in alasan


def test_sinyal_tidak_look_ahead():
    def buat(closes):
        idx = pd.bdate_range("2024-01-01", periods=len(closes))
        return pd.DataFrame(
            {"close": [float(c) for c in closes], "volume": [1000.0] * len(closes)},
            index=idx,
        )

    asli = generate_signals(add_indicators(buat(range(1, 201))), P)
    diubah = generate_signals(
        add_indicators(buat(list(range(1, 101)) + [9999] * 100)), P
    )
    assert_series_equal(asli["signal"].iloc[:100], diubah["signal"].iloc[:100])
