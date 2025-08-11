import sqlite3
from contextlib import contextmanager
from typing import List, Dict, Any

DB_PATH = "crm.sqlite3"

CONTACT_FIELDS = [
    "name","phone","email","source","interest","status","tags","assigned","notes",
    "action_needed","action_taken","username","password","date","country","province","city"
]

@contextmanager
def connect():
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    try:
        yield con
    finally:
        con.commit()
        con.close()

def init_db():
    with connect() as con:
        cur = con.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                phone TEXT,
                email TEXT,
                source TEXT,
                interest TEXT,
                status TEXT,
                tags TEXT,
                assigned TEXT,
                notes TEXT,
                action_needed TEXT,
                action_taken TEXT,
                username TEXT,
                password TEXT,
                date TEXT,
                country TEXT,
                province TEXT,
                city TEXT
            )
        """)
        # Auto-migrate: ensure all expected columns exist
        cur.execute("PRAGMA table_info(contacts)")
        existing = {row[1] for row in cur.fetchall()}
        for col in CONTACT_FIELDS:
            if col not in existing:
                cur.execute(f"ALTER TABLE contacts ADD COLUMN {col} TEXT")

def get_contacts(filters: Dict[str, Any]=None) -> List[Dict[str, Any]]:
    filters = filters or {}
    where = []
    params = []
    for k, v in filters.items():
        if v:
            where.append(f"{k} LIKE ?")
            params.append(f"%{v}%")
    q = "SELECT {} FROM contacts".format(",".join(CONTACT_FIELDS))
    if where:
        q += " WHERE " + " AND ".join(where)
    with connect() as con:
        con.row_factory = sqlite3.Row
        rows = con.execute(q, params).fetchall()
        return [dict(r) for r in rows]

def upsert_contacts(items: List[Dict[str, Any]]):
    if not items:
        return 0
    with connect() as con:
        cur = con.cursor()
        cols = CONTACT_FIELDS
        q = "INSERT INTO contacts ({}) VALUES ({})".format(
            ",".join(cols), ",".join(["?"]*len(cols))
        )
        data = []
        for it in items:
            row = [it.get(c, "") for c in cols]
            data.append(row)
        cur.executemany(q, data)
        return cur.rowcount

def export_contacts() -> List[Dict[str, Any]]:
    return get_contacts()

def clear_all():
    with connect() as con:
        con.execute("DELETE FROM contacts")
