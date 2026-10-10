"""Dataset untuk ML: fitur dari data sampai hari t, label dari hari-hari sesudahnya."""
import pandas as pd

from idxbot.pipeline import prepare_signals

FEATURES = [
    "dist_ma_fast", "dist_ma_slow", "ma_ratio", "rsi",
    "vol_ratio", "ret_1", "ret_5", "ret_20",
]


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Fitur hari t hanya memakai data sampai hari t."""
    out = pd.DataFrame(index=df.index)
    out["dist_ma_fast"] = df["close"] / df["ma_fast"] - 1
    out["dist_ma_slow"] = df["close"] / df["ma_slow"] - 1
    out["ma_ratio"] = df["ma_fast"] / df["ma_slow"] - 1
    out["rsi"] = df["rsi"]
    out["vol_ratio"] = df["vol_ratio"]
    out["ret_1"] = df["close"].pct_change(1)
    out["ret_5"] = df["close"].pct_change(5)
    out["ret_20"] = df["close"].pct_change(20)
    return out


def forward_return(df: pd.DataFrame, horizon: int, cost: float) -> pd.Series:
    """Beli di open t+1, jual di close t+horizon, dikurangi biaya pulang-pergi."""
    entry = df["open"].shift(-1)
    exit_ = df["close"].shift(-horizon)
    return exit_ / entry - 1 - cost


def build_dataset(ticker: str, settings: dict) -> pd.DataFrame:
    horizon = settings["ml"]["horizon_days"]
    cost = settings["ml"]["round_trip_cost"]
    df = prepare_signals(ticker, settings, "daily")
    data = build_features(df)
    data["fwd_return"] = forward_return(df, horizon, cost)
    data["label"] = (data["fwd_return"] > 0).astype(int)
    data["signal"] = df["signal"]
    data["ticker"] = ticker
    # baris tanpa fitur lengkap atau tanpa masa depan (horizon hari terakhir) dibuang
    return data.dropna(subset=FEATURES + ["fwd_return"])
