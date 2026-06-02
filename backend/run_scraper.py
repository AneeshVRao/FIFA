"""
run_scraper.py — Scraper CLI runner

Pre-fetches all statistical tables from Transfermarkt and populates the local cache.
Run with: python -m backend.run_scraper
"""

import logging
from backend.scraper import TM_URLS, get_scraped_stat

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    logger.info("Initializing Stats Scraping Engine...")
    logger.info("Total categories to scrape: %d", len(TM_URLS))
    
    success_count = 0
    for idx, category in enumerate(TM_URLS.keys(), start=1):
        logger.info("[%d/%d] Fetching category: %s", idx, len(TM_URLS), category)
        try:
            data = get_scraped_stat(category)
            if data:
                logger.info("Success! Cached %d records for %s", len(data), category)
                success_count += 1
            else:
                logger.warning("No records returned for %s", category)
        except Exception as e:
            logger.error("Failed to fetch %s: %s", category, e)
            
    logger.info("Scraping completed. Successfully populated %d/%d tables.", success_count, len(TM_URLS))

if __name__ == "__main__":
    main()
