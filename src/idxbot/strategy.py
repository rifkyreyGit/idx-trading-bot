"""Strategi teknikal berbasis aturan: sinyal BUY / SELL / HOLD beserta alasannya.

Sinyal pada tanggal t hanya memakai indikator tanggal t.
Eksekusi (di harga t+1) ditangani oleh backtest, bukan di sini.
"""
from dataclasses import dataclass

import pandas as pd

REQUIRED = ["ma_fast", "ma_slow", "rsi", "vol_ratio"]


@dataclass(frozen=True)
class StrategyParams:
    buy_min_confirmations: int = 2
    sell_min_confirmations: int = 1
    rsi_buy_min: float = 45.0
    rsi_buy_max: float = 70.0
    rsi_sell_below: float = 45.0
    volume_ratio_min: float = 1.0

    @classmethod
    def from_settings(cls, settings: dict) -> "StrategyParams":
        return cls(**settings["strategy"])


def _join(names: list[str]) -> str:
    return "; ".join(names) if names else "tidak ada"


def evaluate_row(row: pd.Series, p: StrategyParams) -> tuple[str, str]:
    """Kembalikan (sinyal, alasan) untuk satu hari."""
    if any(pd.isna(row.get(col)) for col in REQUIRED):
        return "HOLD", "Data indikator belum cukup."

    close = row["close"]
    mf, ms = row["ma_fast"], row["ma_slow"]
    rsi, vr = row["rsi"], row["vol_ratio"]
    vol_text = f"volume {vr:.2f}x rata-rata (min {p.volume_ratio_min:.1f}x)"

    if mf > ms:  # tren naik -> cek peluang BUY
        checks = [
            ("close di atas MA cepat", close > mf),
            (f"RSI {rsi:.1f} di zona {p.rsi_buy_min:.0f}-{p.rsi_buy_max:.0f}",
             p.rsi_buy_min <= rsi <= p.rsi_buy_max),
            (vol_text, vr >= p.volume_ratio_min),
        ]
        passed = [name for name, ok in checks if ok]
        failed = [name for name, ok in checks if not ok]
        if len(passed) >= p.buy_min_confirmations:
            return "BUY", (
                f"Tren naik (MA cepat {mf:,.0f} > MA lambat {ms:,.0f}). "
                f"Konfirmasi {len(passed)}/3: {_join(passed)}."
            )
        return "HOLD", (
            f"Tren naik, tetapi konfirmasi hanya {len(passed)}/3 "
            f"(butuh {p.buy_min_confirmations}). Belum terpenuhi: {_join(failed)}."
        )

    if mf < ms:  # tren turun -> cek peluang SELL
        checks = [
            ("close di bawah MA cepat", close < mf),
            (f"RSI {rsi:.1f} di bawah {p.rsi_sell_below:.0f}", rsi < p.rsi_sell_below),
            (vol_text, vr >= p.volume_ratio_min),
        ]
        passed = [name for name, ok in checks if ok]
        failed = [name for name, ok in checks if not ok]
        if len(passed) >= p.sell_min_confirmations:
            return "SELL", (
                f"Tren turun (MA cepat {mf:,.0f} < MA lambat {ms:,.0f}). "
                f"Konfirmasi {len(passed)}/3: {_join(passed)}."
            )
        return "HOLD", (
            f"Tren turun, tetapi konfirmasi hanya {len(passed)}/3 "
            f"(butuh {p.sell_min_confirmations}). Belum terpenuhi: {_join(failed)}."
        )

    return "HOLD", "MA cepat sama dengan MA lambat, tren tidak jelas."


def generate_signals(df: pd.DataFrame, p: StrategyParams) -> pd.DataFrame:
    """Tambahkan kolom 'signal' dan 'reason' ke tabel yang sudah punya indikator."""
    hasil = [evaluate_row(row, p) for _, row in df.iterrows()]
    out = df.copy()
    out["signal"] = [s for s, _ in hasil]
    out["reason"] = [r for _, r in hasil]
    return out
