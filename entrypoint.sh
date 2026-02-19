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
        
        # Automatically populate database with initial data if AUTO_POPULATE is enabled
        if [ "${AUTO_POPULATE:-true}" = "true" ]; then
            echo "[INFO] AUTO_POPULATE is enabled. Running scraper to populate database..."
            echo "[INFO] This may take a few minutes..."
            cd /app
            python scraper.py --non-interactive --location worcester --db "$DB_PATH" 2>&1 | grep -E '^\[|^Progress|properties' || true
            scraper_status=${PIPESTATUS[0]}
            
            if [ "${scraper_status}" -eq 0 ]; then
                echo "[SUCCESS] Database populated with initial data"
                SIZE=$(du -h "$DB_PATH" | cut -f1)
                echo "[INFO] Database size after population: $SIZE"
            else
                echo "[WARNING] Scraper failed, but continuing with empty database"
            fi
        else
            echo "[INFO] AUTO_POPULATE is disabled. Database created but empty."
            echo "[INFO] Run 'make scraper' to populate it manually."
        fi
    else
        echo "[ERROR] Failed to create database"
        exit 1
    fi
else
    echo "[OK] Database found at $DB_PATH"
    # Show database size
    SIZE=$(du -h "$DB_PATH" | cut -f1)
    echo "[INFO] Database size: $SIZE"
    
    # Run migration to update schema if needed
    echo "[INFO] Checking for database schema updates..."
    python /app/migrate_db.py "$DB_PATH"
    if [ $? -eq 0 ]; then
        echo "[SUCCESS] Database schema is up to date"
    else
        echo "[WARNING] Database migration had issues, but continuing..."
    fi
fi

echo "[INFO] Starting application..."
echo "========================================="

# Start the periodic scraper scheduler in the background if ENABLE_SCHEDULER is true
if [ "${ENABLE_SCHEDULER:-true}" = "true" ]; then
    echo "[INFO] Starting periodic scraper scheduler (every 1 hour)..."
    python /app/scheduler.py &
    SCHEDULER_PID=$!
    echo "[INFO] Scheduler started with PID: $SCHEDULER_PID"
    
    # Create a trap to stop scheduler on shutdown
    trap "echo '[INFO] Stopping scheduler...'; kill $SCHEDULER_PID 2>/dev/null || true; wait $SCHEDULER_PID 2>/dev/null || true" EXIT TERM INT
else
    echo "[INFO] Periodic scheduler is disabled (ENABLE_SCHEDULER=false)"
fi

echo "[INFO] Starting main application..."
echo "========================================="

# Start the application
exec "$@"
