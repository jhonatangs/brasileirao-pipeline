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

    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command="dbt build --project-dir /usr/local/airflow/dbt_brasileirao --profiles-dir /usr/local/airflow/dbt_brasileirao"
    )

    extract_standings_task >> dbt_build

extract_brasileirao()
