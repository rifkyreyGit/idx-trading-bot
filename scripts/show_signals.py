"""Tampilkan sinyal terbaru tiap saham beserta alasannya."""
from idxbot.config import get_db_path, load_settings
from idxbot.data.cleaning import clean_prices
from idxbot.data.storage import load_prices
from idxbot.indicators import add_indicators
from idxbot.strategy import StrategyParams, generate_signals


def main() -> None:
    settings = load_settings()
    db_path = get_db_path(settings)
    ind = settings["indicators"]
    params = StrategyParams.from_settings(settings)

    for ticker in settings["data"]["tickers"]:
        df = clean_prices(load_prices(db_path, ticker))
        df = add_indicators(df, **ind)
        df = generate_signals(df, params)

        last = df.iloc[-1]
        print(f"\n=== {ticker} | {df.index[-1].date()} | close {last['close']:,.0f} ===")
        print(f"Sinyal : {last['signal']}")
        print(f"Alasan : {last['reason']}")
        counts = df["signal"].value_counts()
        print("Distribusi seluruh riwayat:",
              {k: int(counts.get(k, 0)) for k in ["BUY", "SELL", "HOLD"]})


if __name__ == "__main__":
    main()
