#!/usr/bin/env python3
"""
Database migration script to add new columns to existing properties database.
Safely adds agent_name column and creates agent_blacklist table if they don't exist.
"""

import sqlite3
import sys
import os

def get_db_path():
    """Get the database path from environment or use default."""
    if os.path.exists('/app/data'):
        return "/app/data/properties.db"
    return os.environ.get('DB_DEFAULT', 'properties.db')

def migrate_database(db_path):
    """Migrate database schema to latest version."""
    print(f"[MIGRATION] Checking database at: {db_path}")
    
    if not os.path.exists(db_path):
        print(f"[ERROR] Database not found at {db_path}")
        return False
    
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # Check if agent_name column exists
        cur.execute("PRAGMA table_info(properties)")
        columns = [col[1] for col in cur.fetchall()]
        
        if 'agent_name' not in columns:
            print("[MIGRATION] Adding agent_name column to properties table...")
            cur.execute("ALTER TABLE properties ADD COLUMN agent_name TEXT")
            conn.commit()
            print("[SUCCESS] Added agent_name column")
        else:
            print("[INFO] agent_name column already exists")
        
        # Check if agent_blacklist table exists
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='agent_blacklist'")
        if not cur.fetchone():
            print("[MIGRATION] Creating agent_blacklist table...")
            cur.execute("""
            CREATE TABLE agent_blacklist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT NOT NULL,
                address TEXT NOT NULL,
                occurrence_count INTEGER DEFAULT 1,
                first_seen TEXT,
                last_seen TEXT,
                UNIQUE(agent_name, address)
            )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_agent_address ON agent_blacklist(agent_name, address)")
            conn.commit()
            print("[SUCCESS] Created agent_blacklist table")
        else:
            print("[INFO] agent_blacklist table already exists")
        
        print("[SUCCESS] Database migration completed successfully")
        return True
        
    except Exception as e:
        print(f"[ERROR] Migration failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    db_path = sys.argv[1] if len(sys.argv) > 1 else get_db_path()
    success = migrate_database(db_path)
    sys.exit(0 if success else 1)
