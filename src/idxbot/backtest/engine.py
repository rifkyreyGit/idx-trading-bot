"""Mesin backtest long-only satu saham.

Aturan utama:
- Sinyal hari t dieksekusi di harga OPEN hari t+1 (tanpa look-ahead).
- Beli dalam kelipatan lot; slippage dan fraksi harga BEI diterapkan.
- Posisi terbuka di akhir data tidak dipaksa ditutup.
"""
import math
from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class BacktestParams:
    initial_capital: float = 1_000_000
    fee_buy: float = 0.0015
    fee_sell: float = 0.0025
    slippage: float = 0.001
    lot_size: int = 100
    max_position_pct: float = 1.0

    @classmethod
    def from_settings(cls, settings: dict) -> "BacktestParams":
        return cls(**settings["backtest"])


@dataclass
class BacktestResult:
    trades: pd.DataFrame
    equity: pd.DataFrame
    open_position: dict | None


def tick_size(price: float) -> int:
    """Fraksi harga reguler BEI. Periksa aturan BEI jika ada perubahan."""
    if price < 200:
        return 1
    if price < 500:
        return 2
    if price < 2000:
        return 5
    if price < 5000:
        return 10
    return 25


def round_to_tick(price: float, direction: str) -> float:
    tick = tick_size(price)
    ratio = round(price / tick, 6)  # hindari error pecahan desimal
    if direction == "up":
        return math.ceil(ratio) * tick
    return math.floor(ratio) * tick


def run_backtest(df: pd.DataFrame, p: BacktestParams) -> BacktestResult:
    """df wajib punya kolom: open, close, signal, reason (index = tanggal)."""
    cash = float(p.initial_capital)
    shares = 0
    entry: dict | None = None
    pending: tuple[str, str] | None = None  # keputusan kemarin, dieksekusi hari ini
    trades: list[dict] = []
    curve: list[dict] = []

    for date, row in df.iterrows():
        # 1) Eksekusi keputusan kemarin di harga open hari ini
        if pending is not None:
            sig, reason = pending

            if sig == "BUY" and shares == 0:
                fill = round_to_tick(row["open"] * (1 + p.slippage), "up")
                budget = cash * p.max_position_pct
                lots = int(budget // (fill * p.lot_size * (1 + p.fee_buy)))
                if lots >= 1:
                    shares = lots * p.lot_size
                    gross = shares * fill
                    cost = gross + gross * p.fee_buy
                    cash -= cost
                    entry = {
                        "entry_date": date,
                        "entry_price": fill,
                        "shares": shares,
                        "entry_cost": cost,
                        "entry_reason": reason,
                    }

            elif sig == "SELL" and shares > 0:
                fill = round_to_tick(row["open"] * (1 - p.slippage), "down")
                gross = shares * fill
                proceeds = gross - gross * p.fee_sell
                cash += proceeds
                pnl = proceeds - entry["entry_cost"]
                trades.append(
                    {
                        **entry,
                        "exit_date": date,
                        "exit_price": fill,
                        "exit_reason": reason,
                        "lots": shares // p.lot_size,
                        "pnl": pnl,
                        "return_pct": pnl / entry["entry_cost"] * 100,
                        "holding_days": (date - entry["entry_date"]).days,
                    }
                )
                shares, entry = 0, None

        # 2) Catat nilai portofolio di akhir hari (harga close)
        curve.append(
            {
                "date": date,
                "equity": cash + shares * row["close"],
                "cash": cash,
                "shares": shares,
            }
        )

        # 3) Sinyal hari ini baru dieksekusi besok
        pending = (row["signal"], row["reason"]) if row["signal"] in ("BUY", "SELL") else None

    equity = pd.DataFrame(curve).set_index("date")
    trades_df = pd.DataFrame(trades)

    open_position = None
    if shares > 0:
        last_close = df["close"].iloc[-1]
        open_position = {
            **entry,
            "last_close": last_close,
            "unrealized_pnl": shares * last_close - entry["entry_cost"],
        }

    return BacktestResult(trades=trades_df, equity=equity, open_position=open_position)
