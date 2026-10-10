"""Menyimpan dan membaca data harga di SQLite."""
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(db_path)


def init_db(db_path: Path) -> None:
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS prices (
                ticker    TEXT NOT NULL,
                date      TEXT NOT NULL,
                open      REAL,
                high      REAL,
                low       REAL,
                close     REAL,
                adj_close REAL,
                volume    INTEGER,
                PRIMARY KEY (ticker, date)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS data_updates (
                ticker     TEXT PRIMARY KEY,
                fetched_at TEXT NOT NULL,
                n_rows     INTEGER NOT NULL
            )
            """
        )


def save_prices(db_path: Path, ticker: str, df: pd.DataFrame) -> int:
    """Simpan harga. Baris yang sudah ada akan ditimpa (tidak dobel)."""
    rows = [
        (
            ticker,
            idx.strftime("%Y-%m-%d"),
            float(r.open),
            float(r.high),
            float(r.low),
            float(r.close),
            float(r.adj_close),
            int(r.volume),
        )
        for idx, r in df.iterrows()
    ]
    with connect(db_path) as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO prices VALUES (?,?,?,?,?,?,?,?)", rows
        )
        conn.execute(
            "INSERT OR REPLACE INTO data_updates VALUES (?,?,?)",
            (ticker, datetime.now().isoformat(timespec="seconds"), len(rows)),
        )
    return len(rows)


def load_prices(db_path: Path, ticker: str) -> pd.DataFrame:
    """Baca harga satu saham dari database, urut tanggal."""
    with connect(db_path) as conn:
        df = pd.read_sql_query(
            "SELECT date, open, high, low, close, adj_close, volume "
            "FROM prices WHERE ticker = ? ORDER BY date",
            conn,
            params=(ticker,),
            parse_dates=["date"],
        )
    return df.set_index("date")


def get_last_update(db_path: Path, ticker: str) -> str | None:
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT fetched_at FROM data_updates WHERE ticker = ?", (ticker,)
        ).fetchone()
    return row[0] if row else None
