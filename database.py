"""
database.py
-----------
Database initialization, schema creation, and CSV seeding for the
AI-Based Network Capacity Planning System.
"""

import sqlite3
import os
import csv
import json
from datetime import datetime

DB_PATH = os.path.join("database", "network.db")
CSV_PATH = os.path.join("data", "network_metrics.csv")


# ── Devices seed data ────────────────────────────────────────────────────────
SEED_DEVICES = [
    (1,  "Core-Router-01",   "Router",       "DataCenter-A", "192.168.1.1",  100, 32,  1000, "Active"),
    (2,  "Core-Router-02",   "Router",       "DataCenter-B", "192.168.1.2",  100, 32,  1000, "Active"),
    (3,  "Dist-Switch-01",   "Switch",       "Floor-1",      "192.168.2.1",  100, 16,  500,  "Active"),
    (4,  "Dist-Switch-02",   "Switch",       "Floor-2",      "192.168.2.2",  100, 16,  500,  "Active"),
    (5,  "Edge-Firewall-01", "Firewall",     "DMZ",          "10.0.0.1",     100, 64,  2000, "Active"),
    (6,  "App-Server-01",    "Server",       "DataCenter-A", "192.168.10.1", 100, 128, 10000,"Active"),
    (7,  "App-Server-02",    "Server",       "DataCenter-A", "192.168.10.2", 100, 128, 10000,"Active"),
    (8,  "DB-Server-01",     "Server",       "DataCenter-B", "192.168.10.3", 100, 256, 10000,"Active"),
    (9,  "WiFi-AP-01",       "Access Point", "Office-Area",  "192.168.3.1",  100, 4,   300,  "Active"),
    (10, "WiFi-AP-02",       "Access Point", "Conference",   "192.168.3.2",  100, 4,   300,  "Active"),
]


def get_connection():
    """Return a SQLite connection with row_factory set to dict-like rows."""
    os.makedirs("database", exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=60.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 60000")
    return conn


def init_db():
    """Create all tables and seed initial data."""
    conn = get_connection()
    c = conn.cursor()

    # ── devices ──────────────────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS devices (
            id                 INTEGER PRIMARY KEY,
            device_name        TEXT    NOT NULL UNIQUE,
            device_type        TEXT    NOT NULL,
            location           TEXT,
            ip_address         TEXT    UNIQUE,
            cpu_capacity       REAL    DEFAULT 100,
            memory_capacity    REAL    DEFAULT 32,
            bandwidth_capacity REAL    DEFAULT 1000,
            status             TEXT    DEFAULT 'Active',
            created_at         TEXT    DEFAULT (datetime('now'))
        )
    """)

    # ── network_metrics ──────────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS network_metrics (
            id                      INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id               INTEGER NOT NULL,
            timestamp               TEXT    NOT NULL,
            cpu_utilization         REAL,
            memory_utilization      REAL,
            bandwidth_utilization   REAL,
            network_traffic         REAL,
            latency                 REAL,
            packet_loss             REAL,
            storage_utilization     REAL,
            FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_metrics_device_ts ON network_metrics(device_id, timestamp)")

    # ── predictions ──────────────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id        INTEGER NOT NULL,
            resource_type    TEXT    NOT NULL,
            prediction_date  TEXT    NOT NULL,
            predicted_value  REAL,
            risk_level       TEXT,
            created_at       TEXT    DEFAULT (datetime('now')),
            FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
        )
    """)

    # ── alerts ───────────────────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id       INTEGER,
            device_name     TEXT,
            resource        TEXT,
            current_value   REAL,
            predicted_value REAL,
            risk_level      TEXT,
            message         TEXT,
            timestamp       TEXT    DEFAULT (datetime('now')),
            recommendation  TEXT,
            status          TEXT    DEFAULT 'Active',
            FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE SET NULL
        )
    """)

    # ── Seed devices if empty ─────────────────────────────────────────────────
    existing = c.execute("SELECT COUNT(*) FROM devices").fetchone()[0]
    if existing == 0:
        c.executemany(
            "INSERT OR IGNORE INTO devices "
            "(id, device_name, device_type, location, ip_address, "
            " cpu_capacity, memory_capacity, bandwidth_capacity, status) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            SEED_DEVICES,
        )
        print(f"  [OK] Seeded {len(SEED_DEVICES)} devices")

    conn.commit()

    # ── Seed metrics from CSV ─────────────────────────────────────────────────
    metric_count = c.execute("SELECT COUNT(*) FROM network_metrics").fetchone()[0]
    if metric_count == 0:
        if os.path.exists(CSV_PATH):
            _import_csv(conn, c)
        else:
            print(f"  [WARN] CSV not found at {CSV_PATH} — run generate_dataset.py first")

    conn.close()


def _import_csv(conn, c):
    """Bulk-import network_metrics.csv into the database."""
    print(f"  Importing metrics from {CSV_PATH} ...")
    rows = []
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append((
                int(row["device_id"]),
                row["timestamp"],
                float(row["cpu_utilization"]),
                float(row["memory_utilization"]),
                float(row["bandwidth_utilization"]),
                float(row["network_traffic"]),
                float(row["latency"]),
                float(row["packet_loss"]),
                float(row["storage_utilization"]),
            ))
    c.executemany(
        "INSERT INTO network_metrics "
        "(device_id, timestamp, cpu_utilization, memory_utilization, "
        " bandwidth_utilization, network_traffic, latency, packet_loss, storage_utilization) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        rows,
    )
    conn.commit()
    print(f"  [OK] Imported {len(rows):,} metric records")


def row_to_dict(row):
    """Convert sqlite3.Row to plain dict."""
    return dict(row) if row else None


def rows_to_list(rows):
    """Convert list of sqlite3.Row to list of dicts."""
    return [dict(r) for r in rows]


if __name__ == "__main__":
    print("Initializing database …")
    init_db()
    print("Done.")
