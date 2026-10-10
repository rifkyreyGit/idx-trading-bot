"""Jalankan backtest tiap saham dan tampilkan ringkasan awal."""
from idxbot.backtest.engine import BacktestParams, run_backtest
from idxbot.config import get_db_path, load_settings
from idxbot.data.cleaning import clean_prices
from idxbot.data.storage import load_prices
from idxbot.indicators import add_indicators
from idxbot.strategy import StrategyParams, generate_signals


def main() -> None:
    settings = load_settings()
    db_path = get_db_path(settings)
    sp = StrategyParams.from_settings(settings)
    bp = BacktestParams.from_settings(settings)

    for ticker in settings["data"]["tickers"]:
        df = clean_prices(load_prices(db_path, ticker))
        df = add_indicators(df, **settings["indicators"])
        df = df.dropna(subset=["ma_slow"])  # mulai saat indikator lengkap
        df = generate_signals(df, sp)

        hasil = run_backtest(df, bp)
        akhir = hasil.equity["equity"].iloc[-1]
        ret = (akhir / bp.initial_capital - 1) * 100
        bh = (df["close"].iloc[-1] / df["open"].iloc[0] - 1) * 100

        print(f"\n=== {ticker} | {df.index[0].date()} s/d {df.index[-1].date()} ===")
        print(f"Modal awal        : Rp{bp.initial_capital:,.0f}")
        print(f"Nilai akhir       : Rp{akhir:,.0f}  ({ret:+.1f}%)")
        print(f"Transaksi selesai : {len(hasil.trades)}")
        print(f"Buy & hold (kasar, tanpa biaya, semua modal): {bh:+.1f}%")
        if hasil.open_position:
            op = hasil.open_position
            print(f"Posisi terbuka    : {op['shares']} lembar sejak "
                  f"{op['entry_date'].date()} (unrealized Rp{op['unrealized_pnl']:,.0f})")
        if not hasil.trades.empty:
            print("3 transaksi terakhir:")
            kolom = ["entry_date", "exit_date", "entry_price", "exit_price", "lots", "pnl"]
            print(hasil.trades[kolom].tail(3).round(0).to_string(index=False))


if __name__ == "__main__":
    main()
