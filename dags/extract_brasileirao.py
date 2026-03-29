from datetime import datetime
from airflow.decorators import dag, task
from airflow.operators.bash import BashOperator

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

    extract_standings_task = extract_standings()

    @task
    def extract_matches():
        from include.scrapers.br_scraper import scrape_brasileirao_matches
        scrape_brasileirao_matches()

    extract_matches_task = extract_matches()

    @task
    def extract_future_matches():
        from include.scrapers.br_scraper import scrape_brasileirao_future_matches
        scrape_brasileirao_future_matches()

    extract_future_matches_task = extract_future_matches()

    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command="dbt build --project-dir /usr/local/airflow/dbt_brasileirao --profiles-dir /usr/local/airflow/dbt_brasileirao"
    )

    [extract_standings_task, extract_matches_task, extract_future_matches_task] >> dbt_build

extract_brasileirao()
