"""Rangkaian siap pakai: data -> bersih -> (mingguan) -> indikator -> sinyal."""
import pandas as pd

from idxbot.config import get_db_path
from idxbot.data.cleaning import clean_prices
from idxbot.data.storage import load_prices
from idxbot.indicators import add_indicators
from idxbot.resample import resample_weekly
from idxbot.strategy import StrategyParams, generate_signals


def prepare_signals(ticker: str, settings: dict, timeframe: str = "daily") -> pd.DataFrame:
    df = clean_prices(load_prices(get_db_path(settings), ticker))
    if timeframe == "weekly":
        df = resample_weekly(df)
    elif timeframe != "daily":
        raise ValueError(f"Timeframe tidak dikenal: {timeframe}")
    df = add_indicators(df, **settings["indicators"])
    df = df.dropna(subset=["ma_slow"])
    return generate_signals(df, StrategyParams.from_settings(settings))


def buy_and_hold_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Benchmark: beli di awal, tahan terus."""
    b = df.copy()
    b["signal"] = "HOLD"
    b["reason"] = "buy & hold"
    b.iloc[0, b.columns.get_loc("signal")] = "BUY"
    return b