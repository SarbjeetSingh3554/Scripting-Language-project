import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "main.db")


def get_db_connection():
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row  # allows dict-like access
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    except Exception as err:
        print(f"Error connecting to database: {err}")
        return None


def _convert_query(query):
    """Convert MySQL-style %s placeholders to SQLite ? placeholders."""
    return query.replace("%s", "?")


def execute_query(query, params=None, fetch=False, fetchall=False, commit=False):
    conn = get_db_connection()
    if not conn:
        return None

    query = _convert_query(query)
    cursor = conn.cursor()
    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        result = None
        if fetch:
            row = cursor.fetchone()
            result = dict(row) if row else None
        elif fetchall:
            rows = cursor.fetchall()
            result = [dict(row) for row in rows]

        if commit:
            conn.commit()

        return result

    except Exception as err:
        print(f"Database error executing {query}: {err}")
        if commit:
            conn.rollback()
        return None

    finally:
        cursor.close()
        conn.close()