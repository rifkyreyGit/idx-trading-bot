"""Simulasi portofolio paper trading beberapa saham dengan satu modal bersama.

- Sinyal hari t dieksekusi di harga OPEN hari t+1 (tanpa look-ahead).
- Jual diproses lebih dulu, lalu beli (urutan prioritas = urutan di frames).
- Beli kelipatan lot; slippage dan fraksi harga BEI diterapkan.
- Hanya tanggal yang dimiliki semua saham yang disimulasikan.
"""
from dataclasses import dataclass

import pandas as pd

from idxbot.backtest.engine import BacktestParams, round_to_tick


@dataclass(frozen=True)
class PortfolioParams:
    max_positions: int = 3
    max_position_pct: float = 0.7

    @classmethod
    def from_settings(cls, settings: dict) -> "PortfolioParams":
        return cls(**settings["portfolio"])


@dataclass
class PortfolioResult:
    trades: pd.DataFrame
    equity: pd.DataFrame
    open_positions: list


def run_portfolio(frames: dict, bp: BacktestParams, pp: PortfolioParams) -> PortfolioResult:
    """frames: {ticker: DataFrame dengan kolom open, close, signal, reason}."""
    tickers = list(frames)

    common = None
    for f in frames.values():
        idx = set(f.index)
        common = idx if common is None else common & idx
    dates = sorted(common)
    if not dates:
        raise ValueError("Tidak ada tanggal yang dimiliki semua saham.")
    data = {t: f.loc[dates] for t, f in frames.items()}

    cash = float(bp.initial_capital)
    positions: dict = {}
    pending: dict = {}
    trades: list = []
    curve: list = []
    rows: dict = {}

    for date in dates:
        rows = {t: data[t].loc[date] for t in tickers}

        # 1) JUAL dulu (keputusan kemarin, harga open hari ini)
        for t in tickers:
            sig = pending.get(t)
            if sig and sig[0] == "SELL" and t in positions:
                pos = positions.pop(t)
                fill = round_to_tick(rows[t]["open"] * (1 - bp.slippage), "down")
                gross = pos["shares"] * fill
                proceeds = gross * (1 - bp.fee_sell)
                cash += proceeds
                pnl = proceeds - pos["entry_cost"]
                trades.append(
                    {
                        "ticker": t,
                        **pos,
                        "exit_date": date,
                        "exit_price": fill,
                        "exit_reason": sig[1],
                        "lots": pos["shares"] // bp.lot_size,
                        "pnl": pnl,
                        "return_pct": pnl / pos["entry_cost"] * 100,
                        "holding_days": (date - pos["entry_date"]).days,
                    }
                )

        # 2) BELI, sesuai urutan prioritas dan batas posisi
        equity_open = cash + sum(
            pos["shares"] * rows[t]["open"] for t, pos in positions.items()
        )
        for t in tickers:
            sig = pending.get(t)
            if not sig or sig[0] != "BUY" or t in positions:
                continue
            if len(positions) >= pp.max_positions:
                break
            fill = round_to_tick(rows[t]["open"] * (1 + bp.slippage), "up")
            budget = min(cash, equity_open * pp.max_position_pct)
            lots = int(budget // (fill * bp.lot_size * (1 + bp.fee_buy)))
            if lots < 1:
                continue
            shares = lots * bp.lot_size
            cost = shares * fill * (1 + bp.fee_buy)
            cash -= cost
            positions[t] = {
                "entry_date": date,
                "entry_price": fill,
                "shares": shares,
                "entry_cost": cost,
                "entry_reason": sig[1],
            }

        # 3) Catat nilai portofolio di akhir hari (harga close)
        invested = sum(pos["shares"] * rows[t]["close"] for t, pos in positions.items())
        curve.append(
            {
                "date": date,
                "equity": cash + invested,
                "cash": cash,
                "invested": invested,
                "n_positions": len(positions),
            }
        )

        # 4) Sinyal hari ini baru dieksekusi besok
        pending = {
            t: (rows[t]["signal"], rows[t]["reason"])
            for t in tickers
            if rows[t]["signal"] in ("BUY", "SELL")
        }

    open_positions = []
    for t, pos in positions.items():
        last_close = rows[t]["close"]
        open_positions.append(
            {
                "ticker": t,
                **pos,
                "last_close": last_close,
                "unrealized_pnl": pos["shares"] * last_close - pos["entry_cost"],
            }
        )

    return PortfolioResult(
        trades=pd.DataFrame(trades),
        equity=pd.DataFrame(curve).set_index("date"),
        open_positions=open_positions,
    )