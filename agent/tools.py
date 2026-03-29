import duckdb
import os
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.path.join("data", "lakehouse.duckdb")


def run_query(sql_query: str) -> str:
    """
    Executes a SQL query on the DuckDB lakehouse and returns the result as a string.

    Args:
        sql_query: The SQL query to execute.

    Returns:
        A string representation of the query results.
    """
    try:
        con = duckdb.connect(DB_PATH, read_only=True)
        result = con.execute(sql_query).fetchdf()
        con.close()

        if result.empty:
            return "A consulta não retornou nenhum resultado."

        return result.to_string(index=False)
    except Exception as e:
        return f"Erro ao executar a query: {e}"
