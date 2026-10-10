"""Simulasi portofolio paper trading beberapa saham dengan satu modal bersama.

- Sinyal hari t dieksekusi di harga OPEN hari t+1 (tanpa look-ahead).
- Jual diproses lebih dulu, lalu beli (urutan prioritas = urutan di frames).
- Stop loss / take profit (opsional) dicek tiap hari dengan low dan high.
  Jika keduanya tersentuh di hari yang sama, stop dihitung lebih dulu.
- Setelah keluar karena stop/target, tidak beli lagi sampai ada sinyal baru
  (sinyal harus sempat bukan BUY dulu).
"""
from dataclasses import dataclass

import pandas as pd

from idxbot.backtest.engine import BacktestParams, round_to_tick


@dataclass(frozen=True)
class PortfolioParams:
    max_positions: int = 3
    max_position_pct: float = 0.7
    stop_loss_pct: float | None = None
    take_profit_pct: float | None = None

    @classmethod
    def from_settings(cls, settings: dict) -> "PortfolioParams":
        return cls(**settings["portfolio"])


@dataclass
class PortfolioResult:
    trades: pd.DataFrame
    equity: pd.DataFrame
    open_positions: list


def run_portfolio(frames: dict, bp: BacktestParams, pp: PortfolioParams) -> PortfolioResult:
    """frames: {ticker: DataFrame dengan kolom open, high, low, close, signal, reason}."""
    tickers = list(frames)

    common = None
    for f in frames.values():
        idx = set(f.index)
        common = idx if common is None else common & idx
    dates = sorted(common)
    if not dates:
        raise ValueError("Tidak ada tanggal yang dimiliki semua saham.")
    data = {t: f.loc[dates] for t, f in frames.items()}

    use_exits = pp.stop_loss_pct is not None or pp.take_profit_pct is not None
    cash = float(bp.initial_capital)
    positions: dict = {}
    pending: dict = {}
    blocked: dict = {}
    trades: list = []
    curve: list = []
    rows: dict = {}

    def close_position(t, date, fill, reason, kind):
        nonlocal cash
        pos = positions.pop(t)
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
                "exit_reason": reason,
                "exit_type": kind,
                "lots": pos["shares"] // bp.lot_size,
                "pnl": pnl,
                "return_pct": pnl / pos["entry_cost"] * 100,
                "holding_days": (date - pos["entry_date"]).days,
            }
        )

    for date in dates:
        rows = {t: data[t].loc[date] for t in tickers}

        # 1) JUAL karena sinyal (keputusan kemarin, harga open hari ini)
        for t in tickers:
            sig = pending.get(t)
            if sig and sig[0] == "SELL" and t in positions:
                fill = round_to_tick(rows[t]["open"] * (1 - bp.slippage), "down")
                close_position(t, date, fill, sig[1], "sinyal")

        # 2) BELI, sesuai urutan prioritas dan batas posisi
        equity_open = cash + sum(
            pos["shares"] * rows[t]["open"] for t, pos in positions.items()
        )
        for t in tickers:
            sig = pending.get(t)
            if not sig or sig[0] != "BUY" or t in positions:
                continue
            if blocked.get(t):
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
            stop = None
            target = None
            if pp.stop_loss_pct is not None:
                stop = round_to_tick(fill * (1 - pp.stop_loss_pct), "up")
            if pp.take_profit_pct is not None:
                target = round_to_tick(fill * (1 + pp.take_profit_pct), "up")
            positions[t] = {
                "entry_date": date,
                "entry_price": fill,
                "shares": shares,
                "entry_cost": cost,
                "entry_reason": sig[1],
                "stop_price": stop,
                "target_price": target,
            }

        # 3) Stop loss / take profit (low dan high hari ini)
        if use_exits:
            for t in list(positions):
                pos = positions[t]
                r = rows[t]
                if pos["stop_price"] is not None and r["low"] <= pos["stop_price"]:
                    base = min(pos["stop_price"], r["open"])  # gap turun: keluar di open
                    fill = round_to_tick(base * (1 - bp.slippage), "down")
                    close_position(
                        t, date, fill,
                        f"Stop loss {pp.stop_loss_pct * 100:g}% tersentuh", "stop",
                    )
                    blocked[t] = True
                elif pos["target_price"] is not None and r["high"] >= pos["target_price"]:
                    fill = max(pos["target_price"], r["open"])  # order limit
                    close_position(
                        t, date, fill,
                        f"Take profit {pp.take_profit_pct * 100:g}% tercapai", "target",
                    )
                    blocked[t] = True

        # 4) Catat nilai portofolio di akhir hari (harga close)
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

        # 5) Sinyal hari ini baru dieksekusi besok
        for t in tickers:
            if rows[t]["signal"] != "BUY":
                blocked[t] = False
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