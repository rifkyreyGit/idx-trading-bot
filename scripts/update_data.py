"""Unduh data semua saham di settings.yaml lalu simpan ke SQLite."""
from idxbot.config import get_db_path, load_settings
from idxbot.data.fetcher import fetch_history
from idxbot.data.storage import init_db, save_prices


def main() -> None:
    settings = load_settings()
    db_path = get_db_path(settings)
    init_db(db_path)

    start = settings["data"]["start_date"]
    ok, gagal = [], []

    for ticker in settings["data"]["tickers"]:
        try:
            df = fetch_history(ticker, start)
            n = save_prices(db_path, ticker, df)
            print(
                f"[OK]    {ticker}: {n} baris, "
                f"{df.index.min().date()} s/d {df.index.max().date()}, "
                f"close terakhir = {df['close'].iloc[-1]:,.0f}"
            )
            ok.append(ticker)
        except Exception as e:  # satu saham gagal, yang lain tetap jalan
            print(f"[GAGAL] {ticker}: {e}")
            gagal.append(ticker)

    print(f"\nSelesai. Berhasil: {len(ok)}, gagal: {len(gagal)}")
    print(f"Database: {db_path}")


if __name__ == "__main__":
    main()
