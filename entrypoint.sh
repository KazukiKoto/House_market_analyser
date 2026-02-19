#!/bin/bash
set -e

echo "========================================="
echo "  House Market Analyser - Starting Up"
echo "========================================="

# Set database path
DB_PATH="/app/data/properties.db"

# Check if database file exists
if [ ! -f "$DB_PATH" ]; then
    echo "[INFO] Database not found at $DB_PATH"
    echo "[INFO] Creating new database..."
    
    cd /app/data
    python /app/init_db.py
    
    if [ -f "$DB_PATH" ]; then
        echo "[SUCCESS] Database created successfully at $DB_PATH"
    else
        echo "[ERROR] Failed to create database"
        exit 1
    fi
else
    echo "[OK] Database found at $DB_PATH"
    # Show database size
    SIZE=$(du -h "$DB_PATH" | cut -f1)
    echo "[INFO] Database size: $SIZE"
fi

echo "[INFO] Starting application..."
echo "========================================="

# Start the application
exec "$@"
