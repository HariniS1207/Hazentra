"""
database.py
------------
Lightweight SQLite persistence for sensor readings and disaster alerts.
"""

import sqlite3
import time
from contextlib import contextmanager

DB_PATH = "disaster_alert.db"


def init_db(db_path: str = DB_PATH):
    with _connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cycle INTEGER,
                accel REAL,
                temp REAL,
                gas INTEGER,
                dist REAL,
                soil INTEGER,
                timestamp REAL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                disaster_type TEXT,
                trigger_value REAL,
                timestamp REAL,
                resolved_timestamp REAL
            )
        """)
        conn.commit()


@contextmanager
def _connect(db_path: str = DB_PATH):
    conn = sqlite3.connect(db_path)
    try:
        yield conn
    finally:
        conn.close()


def save_reading(data: dict, db_path: str = DB_PATH):
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT INTO readings (cycle, accel, temp, gas, dist, soil, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (data["cycle"], data["accel"], data["temp"], data["gas"],
             data["dist"], data["soil"], data["timestamp"]),
        )
        conn.commit()


def open_alert(disaster_type: str, trigger_value: float, db_path: str = DB_PATH):
    with _connect(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO alerts (disaster_type, trigger_value, timestamp, resolved_timestamp) "
            "VALUES (?, ?, ?, NULL)",
            (disaster_type, trigger_value, time.time()),
        )
        conn.commit()
        return cur.lastrowid


def resolve_open_alerts(disaster_type: str, db_path: str = DB_PATH):
    with _connect(db_path) as conn:
        conn.execute(
            "UPDATE alerts SET resolved_timestamp = ? "
            "WHERE disaster_type = ? AND resolved_timestamp IS NULL",
            (time.time(), disaster_type),
        )
        conn.commit()


def get_recent_readings(limit: int = 100, db_path: str = DB_PATH):
    with _connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM readings ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in reversed(rows)]


def get_alert_history(limit: int = 50, db_path: str = DB_PATH):
    with _connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM alerts ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
