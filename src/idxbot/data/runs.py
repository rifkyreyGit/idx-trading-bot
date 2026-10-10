"""Menyimpan dan membaca riwayat simulasi (paper trading) di SQLite."""
import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from idxbot.data.storage import connect

TRADE_COLS = [
    "ticker", "entry_date", "exit_date", "entry_price", "exit_price",
    "shares", "lots", "pnl", "return_pct", "holding_days",
    "entry_reason", "exit_reason", "exit_type",
]
EQUITY_COLS = ["date", "equity", "cash", "invested", "n_positions"]


def init_run_tables(db_path: Path) -> None:
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sim_runs (
                run_id       INTEGER PRIMARY KEY AUTOINCREMENT,
                name         TEXT NOT NULL,
                created_at   TEXT NOT NULL,
                params_json  TEXT NOT NULL,
                metrics_json TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sim_trades (
                run_id INTEGER NOT NULL,
                ticker TEXT, entry_date TEXT, exit_date TEXT,
                entry_price REAL, exit_price REAL,
                shares INTEGER, lots INTEGER,
                pnl REAL, return_pct REAL, holding_days INTEGER,
                entry_reason TEXT, exit_reason TEXT, exit_type TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sim_equity (
                run_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                equity REAL, cash REAL, invested REAL, n_positions INTEGER
            )
            """
        )


def _metrics_jsonable(metrics: dict) -> dict:
    out = {}
    for k, v in metrics.items():
        try:
            f = float(v)
        except (TypeError, ValueError):
            out[k] = None
            continue
        out[k] = None if f != f else f  # NaN -> None
    return out


def save_run(db_path: Path, name: str, params: dict, result, metrics: dict) -> int:
    """Simpan satu simulasi. Mengembalikan run_id."""
    init_run_tables(db_path)
    with connect(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO sim_runs (name, created_at, params_json, metrics_json) "
            "VALUES (?,?,?,?)",
            (
                name,
                datetime.now().isoformat(timespec="seconds"),
                json.dumps(params, default=str),
                json.dumps(_metrics_jsonable(metrics)),
            ),
        )
        run_id = cur.lastrowid

        if not result.trades.empty:
            t = result.trades.copy()
            if "exit_type" not in t.columns:
                t["exit_type"] = "sinyal"
            for c in ("entry_date", "exit_date"):
                t[c] = pd.to_datetime(t[c]).dt.strftime("%Y-%m-%d")
            t = t[TRADE_COLS].copy()
            t.insert(0, "run_id", run_id)
            t.to_sql("sim_trades", conn, if_exists="append", index=False)

        e = result.equity.reset_index()
        e["date"] = pd.to_datetime(e["date"]).dt.strftime("%Y-%m-%d")
        e = e[EQUITY_COLS].copy()
        e.insert(0, "run_id", run_id)
        e.to_sql("sim_equity", conn, if_exists="append", index=False)
    return run_id


def list_runs(db_path: Path) -> pd.DataFrame:
    init_run_tables(db_path)
    with connect(db_path) as conn:
        return pd.read_sql_query(
            "SELECT run_id, name, created_at, params_json, metrics_json "
            "FROM sim_runs ORDER BY run_id",
            conn,
        )


def load_run_trades(db_path: Path, run_id: int) -> pd.DataFrame:
    with connect(db_path) as conn:
        return pd.read_sql_query(
            "SELECT * FROM sim_trades WHERE run_id = ? ORDER BY entry_date",
            conn, params=(run_id,),
        )


def load_run_equity(db_path: Path, run_id: int) -> pd.DataFrame:
    with connect(db_path) as conn:
        return pd.read_sql_query(
            "SELECT * FROM sim_equity WHERE run_id = ? ORDER BY date",
            conn, params=(run_id,), parse_dates=["date"],
        ).set_index("date")