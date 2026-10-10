import pandas as pd
from pandas.testing import assert_frame_equal

from idxbot.resample import resample_weekly


def make_daily():
    """12 hari bursa: minggu 1 penuh, minggu 2 libur Jumat, minggu 3 baru Rabu."""
    idx = (
        pd.bdate_range("2024-01-01", "2024-01-05")
        .append(pd.bdate_range("2024-01-08", "2024-01-11"))
        .append(pd.bdate_range("2024-01-15", "2024-01-17"))
    )
    n = len(idx)
    opens = [100.0 + i for i in range(n)]
    return pd.DataFrame(
        {
            "open": opens,
            "high": [o + 5 for o in opens],
            "low": [o - 5 for o in opens],
            "close": [o + 1 for o in opens],
            "adj_close": [o + 1 for o in opens],
            "volume": [1000.0] * n,
        },
        index=idx,
    )


def test_agregasi_ohlcv_benar():
    w = resample_weekly(make_daily())
    assert len(w) == 2
    m1, m2 = w.iloc[0], w.iloc[1]
    assert (m1["open"], m1["high"], m1["low"], m1["close"], m1["volume"]) == (
        100.0, 109.0, 95.0, 105.0, 5000.0)
    assert (m2["open"], m2["high"], m2["low"], m2["close"], m2["volume"]) == (
        105.0, 113.0, 100.0, 109.0, 4000.0)
    # tanggal = hari bursa terakhir tiap minggu (minggu 2 berakhir Kamis)
    assert w.index[0] == pd.Timestamp("2024-01-05")
    assert w.index[1] == pd.Timestamp("2024-01-11")


def test_minggu_berjalan_dibuang_tapi_bisa_dipertahankan():
    df = make_daily()
    assert len(resample_weekly(df)) == 2
    assert len(resample_weekly(df, drop_incomplete=False)) == 3


def test_minggu_berakhir_jumat_dipertahankan():
    df = make_daily().iloc[:5]  # Senin-Jumat minggu 1
    assert len(resample_weekly(df)) == 1


def test_data_berakhir_kamis_dibuang_secara_konservatif():
    df = make_daily().iloc[:9]  # minggu 2 berakhir Kamis
    assert len(resample_weekly(df)) == 1


def test_candle_lama_tidak_berubah_oleh_data_baru():
    df = make_daily()
    diubah = df.copy()
    diubah.iloc[5:] = diubah.iloc[5:] * 10  # ubah drastis data setelah minggu 1
    a = resample_weekly(df, drop_incomplete=False).iloc[:1]
    b = resample_weekly(diubah, drop_incomplete=False).iloc[:1]
    assert_frame_equal(a, b)
