"""Bandingkan 3 varian keluar: A (tanpa), B (stop 2%, target 4%), C (stop 2%, target 5%)."""
from dataclasses import replace

import pandas as pd

from idxbot.backtest.engine import BacktestParams
from idxbot.backtest.metrics import compute_metrics
from idxbot.config import load_settings
from idxbot.pipeline import prepare_signals
from idxbot.portfolio import PortfolioParams, run_portfolio

pd.set_option("display.width", 170)

VARIAN = {
    "A tanpa": (None, None),
    "B 2%/4%": (0.02, 0.04),
    "C 2%/5%": (0.02, 0.05),
}


def potong(df, nama, split):
    if nama == "Latih":
        return df[df.index < split]
    if nama == "Uji":
        return df[df.index >= split]
    return df


def main() -> None:
    settings = load_settings()
    bp = BacktestParams.from_settings(settings)
    dasar = PortfolioParams.from_settings(settings)
    split = pd.Timestamp(settings["evaluation"]["split_date"])
    tickers = settings["data"]["tickers"]
    full = {t: prepare_signals(t, settings, "daily") for t in tickers}

    rows = []
    for nama in ("Penuh", "Latih", "Uji"):
        frames = {t: potong(f, nama, split) for t, f in full.items()}
        for label, (sl, tp) in VARIAN.items():
            pp = replace(dasar, stop_loss_pct=sl, take_profit_pct=tp)
            hasil = run_portfolio(frames, bp, pp)
            m = compute_metrics(hasil, bp.initial_capital)
            jenis = hasil.trades["exit_type"].value_counts() if not hasil.trades.empty else {}
            rows.append(
                {
                    "periode": nama, "varian": label,
                    "return%": m["return_pct"], "maxDD%": m["max_drawdown_pct"],
                    "transaksi": m["n_trades"], "winrate%": m["win_rate"], "PF": m["profit_factor"],
                    "stop": int(jenis.get("stop", 0)),
                    "target": int(jenis.get("target", 0)),
                    "sinyal": int(jenis.get("sinyal", 0)),
                }
            )

    print(pd.DataFrame(rows).to_string(index=False, float_format=lambda x: f"{x:.1f}"))
    print("\nStop 2% bisa lebih besar saat gap turun (keluar di open). Tanpa dividen.")


if __name__ == "__main__":
    main()