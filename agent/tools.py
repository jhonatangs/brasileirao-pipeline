import duckdb
import os
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()

_tavily = TavilyClient(api_key=os.getenv("TVLY_API_KEY"))

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


def search_web(query: str) -> str:
    """
    Searches the web using DuckDuckGo and returns a summary of the results.

    Use this tool for up-to-date information such as recent news, player
    injuries, weather conditions, or any context not available in the
    historical DuckDB database.

    Args:
        query: The search query string.

    Returns:
        A string with a summary of the top web search results.
    """
    try:
        response = _tavily.search(query)
        results = response.get("results", [])
        if not results:
            return "Nenhum resultado encontrado na web."
        return "\n\n".join(
            f"[{r.get('title', 'Sem título')}]\n{r.get('content', '')}"
            for r in results
        )
    except Exception as e:
        return f"Erro ao buscar na web: {e}"
