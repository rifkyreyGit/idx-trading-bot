"""Laporan: strategi vs buy & hold, periode penuh / latih / uji."""
import pandas as pd

from idxbot.backtest.engine import BacktestParams, run_backtest
from idxbot.backtest.metrics import compute_metrics
from idxbot.config import get_db_path, load_settings
from idxbot.data.cleaning import clean_prices
from idxbot.data.storage import load_prices
from idxbot.indicators import add_indicators
from idxbot.strategy import StrategyParams, generate_signals

pd.set_option("display.width", 160)


def prepare(ticker: str, settings: dict) -> pd.DataFrame:
    df = clean_prices(load_prices(get_db_path(settings), ticker))
    df = add_indicators(df, **settings["indicators"])
    df = df.dropna(subset=["ma_slow"])
    return generate_signals(df, StrategyParams.from_settings(settings))


def buy_and_hold_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Benchmark: beli di awal, tahan terus. Memakai aturan lot/biaya yang sama."""
    b = df.copy()
    b["signal"] = "HOLD"
    b["reason"] = "buy & hold"
    b.iloc[0, b.columns.get_loc("signal")] = "BUY"
    return b


def main() -> None:
    settings = load_settings()
    bp = BacktestParams.from_settings(settings)
    split = pd.Timestamp(settings["evaluation"]["split_date"])
    rows = []

    for ticker in settings["data"]["tickers"]:
        df = prepare(ticker, settings)
        segmen = {
            "Penuh": df,
            "Latih": df[df.index < split],
            "Uji": df[df.index >= split],
        }
        for nama, bagian in segmen.items():
            if bagian.empty:
                continue
            for model, frame in (
                ("Strategi", bagian),
                ("Buy&Hold", buy_and_hold_frame(bagian)),
            ):
                m = compute_metrics(run_backtest(frame, bp), bp.initial_capital)
                rows.append(
                    {
                        "saham": ticker, "periode": nama, "model": model,
                        "return%": m["return_pct"], "maxDD%": m["max_drawdown_pct"],
                        "transaksi": m["n_trades"], "winrate%": m["win_rate"],
                        "R/R": m["risk_reward"], "PF": m["profit_factor"],
                    }
                )

    tabel = pd.DataFrame(rows)
    for ticker, grup in tabel.groupby("saham", sort=False):
        print(f"\n=== {ticker} ===")
        print(grup.drop(columns="saham").to_string(
            index=False, float_format=lambda x: f"{x:.1f}"))

    print(f"\nLatih: sebelum {split.date()} | Uji: mulai {split.date()}")
    print("Buy&Hold: beli di awal periode (aturan lot sama), tanpa biaya jual, tanpa dividen.")


if __name__ == "__main__":
    main()
