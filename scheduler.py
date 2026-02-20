#!/usr/bin/env python3
"""
Scheduler for periodic scraping of property listings.
Runs scraper every hour automatically in the background.
"""

import os
import sys
import time
import signal
import logging
from datetime import datetime
from scraper import run_scrape

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Configuration
SCRAPE_INTERVAL = 3600  # 1 hour in seconds
DB_PATH = os.environ.get('DB_PATH', '/app/data/properties.db')
LOCATION = os.environ.get('SCRAPE_LOCATION', 'worcester')
SITE = os.environ.get('SCRAPE_SITE', 'onthemarket')

# Global flag for graceful shutdown
shutdown_requested = False


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global shutdown_requested
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_requested = True


def run_periodic_scrape():
    """Run scraper periodically."""
    global shutdown_requested
    
    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    logger.info("========================================")
    logger.info("  Property Scraper Scheduler Started")
    logger.info("========================================")
    logger.info(f"Database: {DB_PATH}")
    logger.info(f"Location: {LOCATION}")
    logger.info(f"Interval: {SCRAPE_INTERVAL} seconds ({SCRAPE_INTERVAL/3600:.1f} hours)")
    logger.info("========================================")
    
    run_count = 0
    
    while not shutdown_requested:
        run_count += 1
        logger.info(f"\n{'='*60}")
        logger.info(f"Starting scrape run #{run_count}")
        logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"{'='*60}\n")
        
        try:
            # Run the scraper
            results = run_scrape(
                db_path=DB_PATH,
                site=SITE,
                location=LOCATION,
                pages=None,  # Auto-detect all pages
                min_price=None,
                max_price=None,
                min_beds=None,
                delay=1.0,
                max_workers=7
            )
            
            logger.info(f"\n{'='*60}")
            logger.info(f"Scrape run #{run_count} completed successfully")
            logger.info(f"Properties found: {len(results)}")
            logger.info(f"{'='*60}\n")
            
        except Exception as e:
            logger.error(f"Scrape run #{run_count} failed: {e}", exc_info=True)
        
        # Wait for next run (checking shutdown flag periodically)
        if not shutdown_requested:
            logger.info(f"Next scrape in {SCRAPE_INTERVAL} seconds ({SCRAPE_INTERVAL/3600:.1f} hours)")
            logger.info(f"Sleeping until {datetime.fromtimestamp(time.time() + SCRAPE_INTERVAL).strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Sleep in chunks to allow responsive shutdown
            sleep_remaining = SCRAPE_INTERVAL
            while sleep_remaining > 0 and not shutdown_requested:
                sleep_chunk = min(60, sleep_remaining)  # Check every minute
                time.sleep(sleep_chunk)
                sleep_remaining -= sleep_chunk
    
    logger.info("\n========================================")
    logger.info("  Scheduler shutdown complete")
    logger.info("========================================")


if __name__ == '__main__':
    try:
        run_periodic_scrape()
    except KeyboardInterrupt:
        logger.info("\nScheduler interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Scheduler crashed: {e}", exc_info=True)
        sys.exit(1)
