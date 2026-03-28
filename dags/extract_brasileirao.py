from datetime import datetime
from airflow.decorators import dag, task

@dag(
    schedule="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["ingestion", "brasileirao", "bronze"]
)
def extract_brasileirao():

    @task
    def extract_standings():
        from include.scrapers.br_scraper import scrape_brasileirao_standings
        scrape_brasileirao_standings()

    extract_standings()

extract_brasileirao()
