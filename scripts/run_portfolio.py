"""Simulasi portofolio paper trading: strategi vs buy & hold (Penuh/Latih/Uji)."""
import pandas as pd

from idxbot.backtest.engine import BacktestParams
from idxbot.backtest.metrics import compute_metrics
from idxbot.config import load_settings
from idxbot.pipeline import buy_and_hold_frame, prepare_signals
from idxbot.portfolio import PortfolioParams, run_portfolio

pd.set_option("display.width", 170)


def slice_period(df, nama, split):
    if nama == "Latih":
        return df[df.index < split]
    if nama == "Uji":
        return df[df.index >= split]
    return df


def main() -> None:
    settings = load_settings()
    bp = BacktestParams.from_settings(settings)
    pp = PortfolioParams.from_settings(settings)
    split = pd.Timestamp(settings["evaluation"]["split_date"])
    tickers = settings["data"]["tickers"]

    full = {t: prepare_signals(t, settings, "daily") for t in tickers}
    rows = []
    penuh = None

    for nama in ("Penuh", "Latih", "Uji"):
        potong = {t: slice_period(f, nama, split) for t, f in full.items()}
        varian = (
            ("Strategi", potong),
            ("Buy&Hold", {t: buy_and_hold_frame(f) for t, f in potong.items()}),
        )
        for model, frames in varian:
            hasil = run_portfolio(frames, bp, pp)
            m = compute_metrics(hasil, bp.initial_capital)
            inv = (hasil.equity["invested"] / hasil.equity["equity"]).mean() * 100
            rows.append(
                {
                    "periode": nama, "model": model,
                    "akhir(Rp)": hasil.equity["equity"].iloc[-1],
                    "return%": m["return_pct"], "maxDD%": m["max_drawdown_pct"],
                    "investasi%": inv, "transaksi": m["n_trades"],
                    "winrate%": m["win_rate"], "PF": m["profit_factor"],
                }
            )
            if nama == "Penuh" and model == "Strategi":
                penuh = hasil

    print(pd.DataFrame(rows).to_string(index=False, float_format=lambda x: f"{x:,.1f}"))
    print(f"\nTickers: {tickers} | Modal awal: Rp{bp.initial_capital:,.0f}")
    print(f"Maks posisi: {pp.max_positions} | Maks porsi per saham: {pp.max_position_pct:.0%}")

    if penuh is not None:
        if not penuh.trades.empty:
            print("\nTransaksi per saham (Strategi, Penuh):")
            print(penuh.trades.groupby("ticker")["pnl"].agg(["count", "sum"]).round(0).to_string())
        print("\nPosisi terbuka di akhir data:")
        for p in penuh.open_positions or []:
            print(f"  {p['ticker']}: {p['shares']} lembar sejak {p['entry_date'].date()}")
        if not penuh.open_positions:
            print("  tidak ada")


if __name__ == "__main__":
    main()