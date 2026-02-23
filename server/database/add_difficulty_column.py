"""
Migration: Add difficulty column to questions table

This fixes older databases created before per-question difficulty was introduced.
Safe to run multiple times.
"""
import sys
import os
import sqlite3

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from server.core.database import DATABASE_PATH


def add_difficulty_column():
    """Add difficulty column to questions table if it doesn't exist."""
    print("=" * 60)
    print("Migration: Adding difficulty column to questions table...")
    print("=" * 60)
    print(f"Database: {DATABASE_PATH}")

    if not os.path.exists(DATABASE_PATH):
        print("[INFO] Database file not found yet. It will be created on first run.")
        return

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute("PRAGMA table_info(questions)")
        columns = [column[1] for column in cursor.fetchall()]

        if "difficulty" in columns:
            print("[OK] Column 'difficulty' already exists. No migration needed.")
            return

        print("[INFO] Adding 'difficulty' column...")
        cursor.execute("ALTER TABLE questions ADD COLUMN difficulty VARCHAR")
        conn.commit()
        print("[SUCCESS] Added 'difficulty' column to questions table.")
    except Exception as e:
        print(f"[ERROR] Failed to add difficulty column: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    add_difficulty_column()

