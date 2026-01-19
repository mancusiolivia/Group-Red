"""
Database initialization script
Reads schema.sql and creates the database and all tables
Run: python server/database/init.py
"""
import os
import sys
import sqlite3

# Get paths
# init.py is in server/database/, so schema.sql is in the same directory
database_dir = os.path.dirname(os.path.abspath(__file__))
server_dir = os.path.dirname(database_dir)
project_root = os.path.dirname(server_dir)

schema_sql_path = os.path.join(database_dir, "schema.sql")
database_path = os.path.join(project_root, "data", "app.db")

def main():
    """Initialize the database by reading schema.sql and creating tables"""
    # Create data directory if it doesn't exist
    data_dir = os.path.join(project_root, "data")
    os.makedirs(data_dir, exist_ok=True)
    
    print("=" * 60)
    print("Initializing Essay Testing System Database")
    print("=" * 60)
    print(f"Reading schema from: {schema_sql_path}")
    print(f"Database will be created at: {database_path}")
    print("=" * 60)
    
    # Check if schema.sql exists
    if not os.path.exists(schema_sql_path):
        print(f"\n[ERROR] schema.sql not found at: {schema_sql_path}")
        sys.exit(1)
    
    try:
        # Read schema.sql
        with open(schema_sql_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        # Connect to SQLite database (creates file if it doesn't exist)
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        # Execute schema SQL (split by semicolons to handle multiple statements)
        # SQLite's executescript handles multiple statements better
        cursor.executescript(schema_sql)
        
        conn.commit()
        conn.close()
        
        print("\n[SUCCESS] Database initialized successfully!")
        print(f"[SUCCESS] Database file: {database_path}")
        print("\nYou can now connect to this database using DBeaver:")
        print("  1. Open DBeaver")
        print("  2. Click Database -> New Database Connection")
        print("  3. Choose SQLite")
        print("  4. Click Next")
        print("  5. For Database file, click Browse")
        print(f"  6. Select app.db (from data folder)")
        print("  7. Click Finish")
    except Exception as e:
        print(f"\n[ERROR] Error initializing database: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
