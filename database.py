"""
database.py — قاعدة البيانات (SQLite)
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

DB_FILE = Path(__file__).parent / "shadowrotate.db"


# ============================================================
# إنشاء الجداول
# ============================================================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # جدول المستخدمين
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            first_seen TEXT,
            trial_used INTEGER DEFAULT 0,
            subscription_type TEXT,
            subscription_expires TEXT,
            total_orders INTEGER DEFAULT 0,
            total_spent REAL DEFAULT 0,
            is_banned INTEGER DEFAULT 0
        )
    ''')

    # جدول الطلبات
    c.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            user_id INTEGER,
            plan TEXT,
            amount REAL,
            method TEXT,
            tx_id TEXT,
            screenshot TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            confirmed_at TEXT
        )
    ''')

    # جدول الجلسات
    c.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            user_id INTEGER,
            accounts_count INTEGER,
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            finished_at TEXT
        )
    ''')

    conn.commit()
    conn.close()
    print("[DB] Initialized")


# ============================================================
# المستخدمين
# ============================================================
def get_user(user_id: int):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()

    if not row:
        return None

    return {
        "user_id": row[0],
        "username": row[1],
        "first_name": row[2],
        "first_seen": row[3],
        "trial_used": row[4],
        "subscription_type": row[5],
        "subscription_expires": row[6],
        "total_orders": row[7],
        "total_spent": row[8],
        "is_banned": row[9],
    }


def create_user(user_id: int, username: str, first_name: str = ""):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    now = datetime.now().isoformat(timespec="seconds")
    c.execute('''
        INSERT OR IGNORE INTO users
        (user_id, username, first_name, first_seen)
        VALUES (?, ?, ?, ?)
    ''', (user_id, username, first_name, now))
    conn.commit()
    conn.close()


def update_user(user_id: int, **kwargs):
    if not kwargs:
        return

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    fields = ", ".join(f"{k} = ?" for k in kwargs.keys())
    values = list(kwargs.values()) + [user_id]
    c.execute(f"UPDATE users SET {fields} WHERE user_id = ?", values)
    conn.commit()
    conn.close()


def user_exists(user_id: int) -> bool:
    return get_user(user_id) is not None


def is_subscribed(user_id: int) -> bool:
    user = get_user(user_id)
    if not user:
        return False
    if not user["subscription_expires"]:
        return False
    try:
        expires = datetime.fromisoformat(user["subscription_expires"])
        return datetime.now() < expires
    except Exception:
        return False


def activate_subscription(user_id: int, plan: str, duration_days: int):
    expires = datetime.now() + timedelta(days=duration_days)
    update_user(
        user_id,
        subscription_type=plan,
        subscription_expires=expires.isoformat(timespec="seconds"),
    )


# ============================================================
# الطلبات
# ============================================================
def create_order(order_id: str, user_id: int, plan: str, amount: float, method: str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    now = datetime.now().isoformat(timespec="seconds")
    c.execute('''
        INSERT INTO orders
        (order_id, user_id, plan, amount, method, status, created_at)
        VALUES (?, ?, ?, ?, ?, 'pending', ?)
    ''', (order_id, user_id, plan, amount, method, now))
    conn.commit()
    conn.close()


def get_order(order_id: str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,))
    row = c.fetchone()
    conn.close()

    if not row:
        return None

    return {
        "order_id": row[0],
        "user_id": row[1],
        "plan": row[2],
        "amount": row[3],
        "method": row[4],
        "tx_id": row[5],
        "screenshot": row[6],
        "status": row[7],
        "created_at": row[8],
        "confirmed_at": row[9],
    }


def update_order(order_id: str, **kwargs):
    if not kwargs:
        return

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    fields = ", ".join(f"{k} = ?" for k in kwargs.keys())
    values = list(kwargs.values()) + [order_id]
    c.execute(f"UPDATE orders SET {fields} WHERE order_id = ?", values)
    conn.commit()
    conn.close()


def get_user_orders(user_id: int, limit: int = 10):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit)
    )
    rows = c.fetchall()
    conn.close()
    return rows


def get_pending_orders():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM orders WHERE status = 'pending' ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return rows


def get_all_users(limit: int = 100):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM users ORDER BY first_seen DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return rows


def get_stats():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM users WHERE subscription_expires > ?",
              (datetime.now().isoformat(timespec="seconds"),))
    active_subs = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM orders WHERE status = 'confirmed'")
    total_orders = c.fetchone()[0]

    c.execute("SELECT COALESCE(SUM(amount), 0) FROM orders WHERE status = 'confirmed'")
    total_revenue = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM orders WHERE status = 'pending'")
    pending_orders = c.fetchone()[0]

    conn.close()

    return {
        "total_users": total_users,
        "active_subs": active_subs,
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "pending_orders": pending_orders,
    }


# ============================================================
# الجلسات
# ============================================================
def create_session(session_id: str, user_id: int, accounts_count: int):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    now = datetime.now().isoformat(timespec="seconds")
    c.execute('''
        INSERT INTO sessions (session_id, user_id, accounts_count, created_at)
        VALUES (?, ?, ?, ?)
    ''', (session_id, user_id, accounts_count, now))
    conn.commit()
    conn.close()


def finish_session(session_id: str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    now = datetime.now().isoformat(timespec="seconds")
    c.execute(
        "UPDATE sessions SET status = 'finished', finished_at = ? WHERE session_id = ?",
        (now, session_id)
    )
    conn.commit()
    conn.close()