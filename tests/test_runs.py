import pandas as pd

from idxbot.data.runs import (
    init_run_tables, list_runs, load_run_equity, load_run_trades, save_run,
)
from idxbot.portfolio import PortfolioResult


def test_simpan_dan_baca_run(tmp_path):
    db = tmp_path / "tes.db"
    init_run_tables(db)

    trades = pd.DataFrame(
        [
            {
                "ticker": "AAA",
                "entry_date": pd.Timestamp("2024-01-02"),
                "exit_date": pd.Timestamp("2024-02-01"),
                "entry_price": 1000.0, "exit_price": 1100.0,
                "shares": 100, "lots": 1, "pnl": 9000.0, "return_pct": 9.0,
                "holding_days": 30, "entry_reason": "a", "exit_reason": "b",
                "exit_type": "sinyal",
            }
        ]
    )
    idx = pd.bdate_range("2024-01-01", periods=3, name="date")
    equity = pd.DataFrame(
        {
            "equity": [1_000_000.0, 1_010_000.0, 1_009_000.0],
            "cash": [1_000_000.0, 900_000.0, 1_009_000.0],
            "invested": [0.0, 110_000.0, 0.0],
            "n_positions": [0, 1, 0],
        },
        index=idx,
    )
    hasil = PortfolioResult(trades=trades, equity=equity, open_positions=[])

    run_id = save_run(
        db, "tes", {"timeframe": "daily"}, hasil,
        {"return_pct": 0.9, "win_rate": float("nan")},
    )

    runs = list_runs(db)
    assert len(runs) == 1 and runs.iloc[0]["name"] == "tes"
    t = load_run_trades(db, run_id)
    assert len(t) == 1 and t.iloc[0]["ticker"] == "AAA"
    assert len(load_run_equity(db, run_id)) == 3