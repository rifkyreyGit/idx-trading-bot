"""Indikator teknikal: MA, RSI (Wilder), dan volume.

Semua nilai pada tanggal t hanya memakai data sampai tanggal t
(tidak ada look-ahead bias).
"""
import pandas as pd


def sma(series: pd.Series, window: int) -> pd.Series:
    """Simple Moving Average. Kosong (NaN) sampai data cukup."""
    return series.rolling(window=window, min_periods=window).mean()


def rsi_wilder(close: pd.Series, period: int = 14) -> pd.Series:
    """RSI dengan smoothing Wilder (sama konsepnya dengan TradingView)."""
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)

    # Wilder smoothing = rata-rata eksponensial dengan alpha = 1/period
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def add_indicators(
    df: pd.DataFrame,
    ma_fast: int = 20,
    ma_slow: int = 50,
    rsi_period: int = 14,
    volume_window: int = 20,
) -> pd.DataFrame:
    """Tambahkan kolom indikator ke tabel harga yang sudah dibersihkan."""
    out = df.copy()
    out["ma_fast"] = sma(out["close"], ma_fast)
    out["ma_slow"] = sma(out["close"], ma_slow)
    out["rsi"] = rsi_wilder(out["close"], rsi_period)
    out["vol_ma"] = sma(out["volume"], volume_window)
    out["vol_ratio"] = out["volume"] / out["vol_ma"]  # >1 = volume di atas rata-rata
    return out
