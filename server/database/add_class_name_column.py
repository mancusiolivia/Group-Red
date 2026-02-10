"""
Script to add class_name column to students table
"""
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from server.core.database import get_db_session
import sqlite3

def add_class_name_column():
    """Add class_name column to students table"""
    print("=" * 60)
    print("Adding class_name column to students table...")
    print("=" * 60)
    
    # Get database path
    from server.core.database import DATABASE_PATH
    
    # Connect directly to SQLite to add column
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(students)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'class_name' in columns:
            print("Column 'class_name' already exists in students table.")
            conn.close()
            return
        
        # Add the column
        cursor.execute("ALTER TABLE students ADD COLUMN class_name VARCHAR")
        conn.commit()
        print("Successfully added 'class_name' column to students table.")
        
    except Exception as e:
        print(f"Error adding column: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    add_class_name_column()
