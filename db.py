
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).with_name("crm.sqlite3")

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS contacts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  phone TEXT,
  email TEXT,
  source TEXT,
  interest TEXT,
  status TEXT,              -- New, Warm, Hot, Customer, Inactive
  tags TEXT,
  assigned TEXT,
  notes TEXT,
  action_needed TEXT,
  action_taken TEXT,
  username TEXT,
  password TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS orders (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  contact_id INTEGER NOT NULL,
  product TEXT,
  quantity INTEGER DEFAULT 1,
  amount REAL,
  status TEXT,              -- Pending, Paid, Shipped, Delivered
  pop_url TEXT,
  notes TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(contact_id) REFERENCES contacts(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS campaigns (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  date TEXT DEFAULT CURRENT_TIMESTAMP,
  channel TEXT,
  name TEXT,
  audience TEXT,
  message TEXT,
  outcome TEXT,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS activities (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  contact_id INTEGER,
  activity_date TEXT DEFAULT CURRENT_TIMESTAMP,
  type TEXT,
  summary TEXT,
  details TEXT,
  FOREIGN KEY(contact_id) REFERENCES contacts(id) ON DELETE CASCADE
);
"""

@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA_SQL)
        # try to add new columns if upgrading
        cols = [r[1] for r in conn.execute("PRAGMA table_info(contacts)").fetchall()]
        for col, sql in [
            ("action_needed","ALTER TABLE contacts ADD COLUMN action_needed TEXT"),
            ("action_taken","ALTER TABLE contacts ADD COLUMN action_taken TEXT"),
            ("username","ALTER TABLE contacts ADD COLUMN username TEXT"),
            ("password","ALTER TABLE contacts ADD COLUMN password TEXT"),
        ]:
            if col not in cols:
                try:
                    conn.execute(sql)
                except Exception:
                    pass

def insert_contact(data: dict) -> int:
    keys = ["name","phone","email","source","interest","status","tags","assigned","notes","action_needed","action_taken","username","password"]
    vals = [data.get(k) for k in keys]
    with get_conn() as conn:
        cur = conn.execute(f"""
            INSERT INTO contacts ({",".join(keys)})
            VALUES ({",".join(["?"]*len(keys))})
        """, vals)
        return cur.lastrowid

def update_contact(contact_id: int, data: dict):
    keys = ["name","phone","email","source","interest","status","tags","assigned","notes","action_needed","action_taken","username","password"]
    sets = ",".join([f"{k}=?" for k in keys])
    vals = [data.get(k) for k in keys] + [contact_id]
    with get_conn() as conn:
        conn.execute(f"UPDATE contacts SET {sets} WHERE id=?", vals)

def delete_contact(contact_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM contacts WHERE id=?", (contact_id,))

def fetch_contacts(search: str = "", status: str = "", tag: str = ""):
    q = "SELECT id,name,phone,email,source,interest,status,tags,assigned,notes,action_needed,action_taken,username,password,created_at FROM contacts"
    conds, params = [], []
    if search:
        conds.append("(name LIKE ? OR phone LIKE ? OR email LIKE ? OR interest LIKE ? OR notes LIKE ? OR action_needed LIKE ? OR action_taken LIKE ?)")
        like = f"%{search}%"
        params += [like, like, like, like, like, like, like]
    if status:
        conds.append("status = ?")
        params.append(status)
    if tag:
        conds.append("tags LIKE ?")
        params.append(f"%{tag}%")
    if conds:
        q += " WHERE " + " AND ".join(conds)
    q += " ORDER BY created_at DESC"
    with get_conn() as conn:
        rows = conn.execute(q, params).fetchall()
    return rows

def insert_order(data: dict) -> int:
    keys = ["contact_id","product","quantity","amount","status","pop_url","notes"]
    vals = [data.get(k) for k in keys]
    with get_conn() as conn:
        cur = conn.execute(f"""
            INSERT INTO orders ({",".join(keys)})
            VALUES ({",".join(["?"]*len(keys))})
        """, vals)
        return cur.lastrowid

def fetch_orders(contact_id: int = None):
    q = """SELECT o.id, o.contact_id, c.name, o.product, o.quantity, o.amount, o.status, o.pop_url, o.notes, o.created_at
           FROM orders o
           LEFT JOIN contacts c ON c.id = o.contact_id"""
    params = []
    if contact_id:
        q += " WHERE o.contact_id = ?"
        params.append(contact_id)
    q += " ORDER BY o.created_at DESC"
    with get_conn() as conn:
        rows = conn.execute(q, params).fetchall()
    return rows

def insert_campaign(data: dict) -> int:
    keys = ["date","channel","name","audience","message","outcome","notes"]
    vals = [data.get(k) for k in keys]
    with get_conn() as conn:
        cur = conn.execute(f"""
            INSERT INTO campaigns ({",".join(keys)})
            VALUES ({",".join(["?"]*len(keys))})
        """, vals)
        return cur.lastrowid

def fetch_campaigns(search: str = ""):
    q = "SELECT id, date, channel, name, audience, message, outcome, notes FROM campaigns"
    params = []
    if search:
        q += " WHERE (name LIKE ? OR audience LIKE ? OR message LIKE ? OR notes LIKE ?)"
        like = f"%{search}%"
        params += [like, like, like, like]
    q += " ORDER BY date DESC"
    with get_conn() as conn:
        rows = conn.execute(q, params).fetchall()
    return rows

def insert_activity(data: dict) -> int:
    keys = ["contact_id","activity_date","type","summary","details"]
    vals = [data.get(k) for k in keys]
    with get_conn() as conn:
        cur = conn.execute(f"""
            INSERT INTO activities ({",".join(keys)})
            VALUES ({",".join(["?"]*len(keys))})
        """, vals)
        return cur.lastrowid

def fetch_activities(contact_id: int):
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT id, activity_date, type, summary, details
            FROM activities
            WHERE contact_id = ?
            ORDER BY activity_date DESC
        """, (contact_id,)).fetchall()
    return rows

def kpis():
    with get_conn() as conn:
        total_contacts = conn.execute("SELECT COUNT(*) FROM contacts").fetchone()[0]
        customers = conn.execute("SELECT COUNT(*) FROM contacts WHERE status='Customer'").fetchone()[0]
        hot = conn.execute("SELECT COUNT(*) FROM contacts WHERE status='Hot'").fetchone()[0]
        orders = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        revenue = conn.execute("SELECT IFNULL(SUM(amount),0) FROM orders WHERE status IN ('Paid','Delivered','Shipped')").fetchone()[0]
    return dict(total_contacts=total_contacts, customers=customers, hot=hot, orders=orders, revenue=revenue)
