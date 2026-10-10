"""Membersihkan data harga mentah sebelum dipakai analisis."""
import pandas as pd


def clean_prices(df: pd.DataFrame) -> pd.DataFrame:
    """Buang hari tanpa perdagangan (volume 0 atau kosong) dan harga tidak valid.

    Data mentah di database tidak diubah; pembersihan dilakukan saat dibaca.
    """
    out = df.copy()
    out = out.dropna(subset=["open", "high", "low", "close", "volume"])
    out = out[out["volume"] > 0]
    out = out[(out[["open", "high", "low", "close"]] > 0).all(axis=1)]
    return out.sort_index()
