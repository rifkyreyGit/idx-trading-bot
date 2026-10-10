"""Metrik performa dari hasil backtest."""
import numpy as np
import pandas as pd


def max_drawdown_pct(equity: pd.Series) -> float:
    """Penurunan terdalam dari puncak ke lembah, dalam persen (angka negatif)."""
    if equity.empty:
        return 0.0
    puncak = equity.cummax()
    return float((equity / puncak - 1).min() * 100)


def trade_stats(trades: pd.DataFrame) -> dict:
    """Statistik dari daftar transaksi yang sudah selesai."""
    n = len(trades)
    if n == 0:
        return {
            "n_trades": 0, "win_rate": np.nan, "avg_win": np.nan,
            "avg_loss": np.nan, "risk_reward": np.nan,
            "profit_factor": np.nan, "avg_holding_days": np.nan,
        }
    wins = trades.loc[trades["pnl"] > 0, "pnl"]
    losses = trades.loc[trades["pnl"] <= 0, "pnl"]
    avg_win = wins.mean()      # NaN jika tidak ada transaksi menang
    avg_loss = losses.mean()   # NaN jika tidak ada transaksi kalah

    risk_reward = np.nan
    if len(wins) and len(losses) and avg_loss != 0:
        risk_reward = avg_win / abs(avg_loss)

    gross_loss = abs(losses.sum())
    profit_factor = wins.sum() / gross_loss if gross_loss > 0 else np.nan

    return {
        "n_trades": n,
        "win_rate": len(wins) / n * 100,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "risk_reward": risk_reward,
        "profit_factor": profit_factor,
        "avg_holding_days": trades["holding_days"].mean(),
    }


def compute_metrics(result, initial_capital: float) -> dict:
    """Gabungkan return, drawdown, dan statistik transaksi."""
    eq = result.equity["equity"]
    akhir = float(eq.iloc[-1]) if len(eq) else float(initial_capital)
    # sertakan modal awal supaya drawdown dihitung dari titik awal yang benar
    kurva = pd.concat(
        [pd.Series([float(initial_capital)]), eq.reset_index(drop=True)],
        ignore_index=True,
    )
    out = {
        "return_pct": (akhir / initial_capital - 1) * 100,
        "max_drawdown_pct": max_drawdown_pct(kurva),
    }
    out.update(trade_stats(result.trades))
    return out


def exposure_pct(result) -> float:
    """Persentase hari/minggu ketika strategi memegang saham."""
    eq = result.equity
    if eq.empty:
        return 0.0
    return float((eq["shares"] > 0).mean() * 100)
