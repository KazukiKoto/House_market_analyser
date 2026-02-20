import sqlite3
import os
import sys

# Create the database file in data directory if in container, otherwise current dir
if os.path.exists('/app/data'):
    db_path = "/app/data/properties.db"
else:
    db_path = "properties.db"

try:
    if os.path.exists(db_path):
        print(f"[INFO] Database already exists at {db_path}")
        sys.exit(0)
    
    print(f"[INFO] Creating database at {db_path}...")
    
    # Ensure directory exists
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA synchronous=NORMAL")
    cur.execute("PRAGMA busy_timeout=30000")
    
    # Create the properties table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS properties (
        id TEXT PRIMARY KEY,
        url TEXT UNIQUE,
        name TEXT,
        title TEXT,
        price INTEGER,
        property_type TEXT,
        beds INTEGER,
        sqft INTEGER,
        address TEXT,
        agent_name TEXT,
        images TEXT,
        summary TEXT,
        first_seen TEXT,
        last_seen TEXT,
        off_market_at TEXT,
        on_market INTEGER DEFAULT 1,
        updated_at TEXT
    )
    """)
    
    # Create agent blacklist table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS agent_blacklist (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agent_name TEXT NOT NULL,
        address TEXT NOT NULL,
        occurrence_count INTEGER DEFAULT 1,
        first_seen TEXT,
        last_seen TEXT,
        UNIQUE(agent_name, address)
    )
    """)
    
    # Create index
    cur.execute("CREATE INDEX IF NOT EXISTS idx_title_address ON properties(LOWER(title), LOWER(address))")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_agent_address ON agent_blacklist(agent_name, address)")
    
    conn.commit()
    conn.close()
    print(f"[SUCCESS] Database created successfully at {db_path}")
    sys.exit(0)
    
except Exception as e:
    print(f"[ERROR] Failed to create database: {e}", file=sys.stderr)
    sys.exit(1)
