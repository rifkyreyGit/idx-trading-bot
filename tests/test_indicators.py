import pandas as pd
from pandas.testing import assert_frame_equal

from idxbot.indicators import add_indicators, rsi_wilder, sma


def make_df(closes):
    idx = pd.bdate_range("2024-01-01", periods=len(closes))
    return pd.DataFrame(
        {"close": [float(c) for c in closes], "volume": [1000.0] * len(closes)},
        index=idx,
    )


def test_sma_nilai_benar():
    s = pd.Series(range(1, 31), dtype=float)  # 1..30
    hasil = sma(s, 20)
    assert pd.isna(hasil.iloc[18])        # belum cukup 20 data
    assert hasil.iloc[19] == 10.5         # rata-rata 1..20


def test_rsi_naik_terus_adalah_100():
    close = pd.Series(range(1, 60), dtype=float)
    assert rsi_wilder(close, 14).iloc[-1] == 100


def test_rsi_turun_terus_mendekati_0():
    close = pd.Series(range(60, 1, -1), dtype=float)
    assert rsi_wilder(close, 14).iloc[-1] < 1


def test_tidak_ada_look_ahead():
    """Mengubah data masa depan tidak boleh mengubah indikator masa lalu."""
    penuh = add_indicators(make_df(range(1, 201)))
    closes = list(range(1, 101)) + [9999] * 100
    diubah = add_indicators(make_df(closes))
    assert_frame_equal(
        penuh.drop(columns=["close"]).iloc[:100],
        diubah.drop(columns=["close"]).iloc[:100],
    )
