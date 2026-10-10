"""Tampilkan indikator terbaru tiap saham untuk dicek ke TradingView."""
import pandas as pd

from idxbot.config import get_db_path, load_settings
from idxbot.data.cleaning import clean_prices
from idxbot.data.storage import load_prices
from idxbot.indicators import add_indicators

pd.set_option("display.width", 140)


def main() -> None:
    settings = load_settings()
    db_path = get_db_path(settings)
    ind = settings["indicators"]

    for ticker in settings["data"]["tickers"]:
        raw = load_prices(db_path, ticker)
        df = clean_prices(raw)
        df = add_indicators(
            df,
            ma_fast=ind["ma_fast"],
            ma_slow=ind["ma_slow"],
            rsi_period=ind["rsi_period"],
            volume_window=ind["volume_window"],
        )
        print(f"\n=== {ticker} | mentah: {len(raw)} baris, "
              f"setelah dibersihkan: {len(df)} baris ===")
        cols = ["close", "ma_fast", "ma_slow", "rsi", "volume", "vol_ratio"]
        print(df[cols].tail(3).round(2))


if __name__ == "__main__":
    main()
