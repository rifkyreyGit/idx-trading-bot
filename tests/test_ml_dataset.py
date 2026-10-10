import pandas as pd
from pandas.testing import assert_frame_equal

from idxbot.indicators import add_indicators
from idxbot.ml.dataset import build_features, forward_return


def make_df(closes):
    idx = pd.bdate_range("2024-01-01", periods=len(closes))
    return pd.DataFrame(
        {
            "open": [float(c) for c in closes],
            "close": [float(c) for c in closes],
            "volume": [1000.0] * len(closes),
        },
        index=idx,
    )


def test_fitur_tidak_look_ahead():
    asli = build_features(add_indicators(make_df(range(1, 201))))
    diubah = build_features(
        add_indicators(make_df(list(range(1, 101)) + [9999] * 100))
    )
    assert_frame_equal(asli.iloc[:100], diubah.iloc[:100])


def test_label_memakai_open_besok_dan_close_horizon():
    df = pd.DataFrame(
        {
            "open": [10.0, 20.0, 30.0, 40.0, 50.0],
            "close": [11.0, 21.0, 31.0, 41.0, 51.0],
        },
        index=pd.bdate_range("2024-01-01", periods=5),
    )
    fwd = forward_return(df, horizon=2, cost=0.0)
    assert fwd.iloc[0] == 31.0 / 20.0 - 1  # open t+1 = 20, close t+2 = 31
    assert pd.isna(fwd.iloc[-1]) and pd.isna(fwd.iloc[-2])
