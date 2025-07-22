from datetime import datetime, timedelta

from utils.scrape_logic import run_scraper

def main():
    since = datetime.now().date() - timedelta(days=7)
    run_scraper(since)


if __name__ == "__main__":
    main()
