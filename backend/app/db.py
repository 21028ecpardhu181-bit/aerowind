"""
backend/app/db.py — SQLite Database Layer for Projects and Authentication.

Provides:
- Lightweight, zero-config SQLite persistence
- User authentication & password hashing (PBKDF2-HMAC-SHA256)
- Project save, update, retrieve, list, and delete
- Automatic seeding of real prototype wind farm projects
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
    DB_DIR = Path("/tmp/aeroquantum_data")
else:
    DB_DIR = Path(__file__).resolve().parent.parent / "data"

try:
    DB_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    DB_DIR = Path("/tmp/aeroquantum_data")
    DB_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DB_DIR / "aeroquantum.db"


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), 100000)
    return f"{salt}:{key.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    try:
        salt, key_hex = hashed.split(":")
        test_key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), 100000)
        return hmac.compare_digest(test_key.hex(), key_hex)
    except Exception:
        return False


def init_db() -> None:
    """Initialize database schema and seed default projects if empty."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Projects table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                user_id INTEGER,
                name TEXT NOT NULL,
                location_name TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                area_km2 REAL,
                turbine_count INTEGER DEFAULT 12,
                turbine_model TEXT DEFAULT 'GE 2.5-120',
                rotor_diameter REAL DEFAULT 120,
                hub_height REAL DEFAULT 110,
                spacing_d REAL DEFAULT 5.0,
                wind_speed REAL DEFAULT 7.1,
                wind_direction REAL DEFAULT 300,
                suitability TEXT DEFAULT 'Good',
                gross_aep REAL,
                net_aep REAL,
                wake_loss_percent REAL,
                turbines_json TEXT,
                boundary_json TEXT,
                status TEXT DEFAULT 'configured',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
            )
        """)

        # Sessions table for tokenless/bearer auth
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                expires_at REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)

        conn.commit()

        # Seed initial projects if table is empty
        cursor.execute("SELECT COUNT(*) FROM projects")
        if cursor.fetchone()[0] == 0:
            seed_default_projects(conn)


def seed_default_projects(conn: sqlite3.Connection) -> None:
    """Seed benchmark engineering projects for instant Screen 0 loading."""
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    cursor = conn.cursor()

    projects = [
        (
            "proj-kanyakumari-01",
            None,
            "Kanyakumari Wind Complex",
            "Kanyakumari, Tamil Nadu, India",
            8.0883,
            77.5385,
            11.0,
            12,
            "GE 2.5-120",
            120,
            110,
            5.0,
            7.1,
            300,
            "Good",
            92.0,
            83.2,
            9.5,
            json.dumps([]),
            json.dumps([]),
            "optimized",
            now,
            now,
        ),
        (
            "proj-jaisalmer-02",
            None,
            "Jaisalmer Desert Array",
            "Jaisalmer, Rajasthan, India",
            26.9157,
            70.9083,
            16.5,
            16,
            "Siemens Gamesa SG 3.4-132",
            132,
            120,
            5.5,
            7.8,
            245,
            "Good",
            112.4,
            102.5,
            8.8,
            json.dumps([]),
            json.dumps([]),
            "simulated",
            now,
            now,
        ),
        (
            "proj-kutch-03",
            None,
            "Kutch Coastal Farm",
            "Kutch, Gujarat, India",
            23.7337,
            69.8597,
            22.0,
            20,
            "Vestas V110-2.0MW",
            110,
            100,
            5.0,
            8.2,
            270,
            "Good",
            149.3,
            134.1,
            10.2,
            json.dumps([]),
            json.dumps([]),
            "configured",
            now,
            now,
        ),
    ]

    cursor.executemany("""
        INSERT INTO projects (
            id, user_id, name, location_name, latitude, longitude, area_km2,
            turbine_count, turbine_model, rotor_diameter, hub_height, spacing_d,
            wind_speed, wind_direction, suitability, gross_aep, net_aep,
            wake_loss_percent, turbines_json, boundary_json, status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, projects)
    conn.commit()


# Initialize database when module is imported
init_db()
