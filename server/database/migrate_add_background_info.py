"""
Migration script to add background_info column to questions table
Run this once to update existing databases
"""
import sys
import os
import sqlite3

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from server.core.config import DATABASE_PATH

def migrate():
    """Add background_info column to questions table if it doesn't exist"""
    print("=" * 60)
    print("Migration: Adding background_info column to questions table")
    print("=" * 60)
    print(f"Database: {DATABASE_PATH}")
    
    if not os.path.exists(DATABASE_PATH):
        print(f"\n[ERROR] Database file not found at: {DATABASE_PATH}")
        print("The database will be created automatically on first server startup.")
        return
    
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(questions)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'background_info' in columns:
            print("\n[OK] Column 'background_info' already exists. No migration needed.")
            conn.close()
            return
        
        # Add the column
        print("\n[INFO] Adding background_info column...")
        cursor.execute("ALTER TABLE questions ADD COLUMN background_info TEXT")
        conn.commit()
        
        print("[SUCCESS] Migration completed successfully!")
        print("The background_info column has been added to the questions table.")
        
        conn.close()
        
    except Exception as e:
        print(f"\n[ERROR] Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    migrate()
