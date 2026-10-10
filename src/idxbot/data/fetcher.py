"""Mengambil data harga harian saham BEI dari Yahoo Finance (yfinance).

Sumber ini tidak resmi dari BEI. Dipakai untuk edukasi/proyek pribadi.
Jika nanti ganti sumber data, cukup ubah file ini.
"""
import pandas as pd
import yfinance as yf

COLUMNS = ["open", "high", "low", "close", "adj_close", "volume"]


def fetch_history(ticker: str, start: str, end: str | None = None) -> pd.DataFrame:
    """Unduh data harian untuk satu saham. Contoh ticker: 'BBCA'."""
    symbol = f"{ticker}.JK"  # akhiran .JK = Bursa Efek Indonesia di Yahoo
    raw = yf.Ticker(symbol).history(start=start, end=end, auto_adjust=False)

    if raw.empty:
        raise ValueError(f"Tidak ada data untuk {symbol}. Cek kode saham/koneksi.")

    df = raw.rename(
        columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Adj Close": "adj_close",
            "Volume": "volume",
        }
    )
    if "adj_close" not in df.columns:
        df["adj_close"] = df["close"]

    df = df[COLUMNS].copy()
    # Buang zona waktu, sisakan tanggal saja
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    df.index.name = "date"
    df = df[~df.index.duplicated(keep="last")]
    df = df.dropna(subset=["close"])
    return df.sort_index()
