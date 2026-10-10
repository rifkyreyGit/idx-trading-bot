"""Mengubah candle harian menjadi candle mingguan."""
import pandas as pd

AGG = {
    "open": "first",
    "high": "max",
    "low": "min",
    "close": "last",
    "adj_close": "last",
    "volume": "sum",
}


def resample_weekly(df: pd.DataFrame, drop_incomplete: bool = True) -> pd.DataFrame:
    """Gabungkan candle harian menjadi mingguan (minggu berakhir Jumat).

    Tanggal tiap candle = hari bursa terakhir pada minggu itu.
    Candle minggu berjalan dibuang jika data terakhir bukan hari Jumat,
    supaya sinyal tidak dibuat dari minggu yang belum selesai.
    """
    if df.empty:
        return df.copy()

    weekly = df.resample("W-FRI").agg(AGG)
    last_day = df.index.to_series().resample("W-FRI").last()

    weekly = weekly.dropna(subset=["close"])  # buang minggu tanpa perdagangan
    weekly.index = pd.DatetimeIndex(last_day.loc[weekly.index])
    weekly.index.name = "date"

    if drop_incomplete and df.index[-1].dayofweek < 4:
        weekly = weekly.iloc[:-1]
    return weekly
