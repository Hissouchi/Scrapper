from datetime import datetime, timedelta
import requests
from utils.scrape_logic import run_scraper

def main():
    since = datetime.now().date() - timedelta(days=7)

    annonces = run_scraper(since)

    for annonce in annonces:
        try:
            res = requests.post("http://127.0.0.1:8000/api/announcements/", json=annonce)
            print(f"✔ {res.status_code} | {res.json()}")
        except Exception as e:
            print(f"❌ Échec d'insertion: {e}")

if __name__ == "__main__":
    main()
