# Brasileirão Pipeline - Spec

## 1. Objetivo

Construir um pipeline de dados ponta a ponta que extrai classificação, resultados de partidas e agendas do Brasileirão (via UOL Esporte), além de dados de elenco e valores de mercado (via Transfermarkt). Os dados são transformados em um Data Lakehouse local e disponibilizados para consultas analíticas via um Agente de IA (Natural Language to SQL) com capacidade de busca web e memória de longo prazo.

## 2. Stack de Tecnologias

- **Orquestração**: Apache Airflow via Astro CLI
- **Extração**: Python via `curl_cffi`, `BeautifulSoup` e `re` (Regex)
- **Processamento/Transformação**: dbt (com DuckDB adapter)
- **Armazenamento**: DuckDB (Data Lakehouse local em `data/lakehouse.duckdb`)
- **Gerenciamento de Pacotes**: uv (Python 3.12)
- **IA/NLQ**: gpt-4o-mini via API com ferramentas (Functions/MCPs) para consultar o DuckDB
- **Pesquisa Web (Agentic)**: Tavily API (Leitura profunda de páginas para dados em tempo real)
- **Memória de Longo Prazo**: Mem0 (Retenção de contexto do usuário entre sessões)

## 3. Requisitos Funcionais

- O pipeline deve extrair dados do UOL Esporte (Placar) e Transfermarkt.
- O pipeline deve persistir a camada raw/bronze em arquivos Parquet isolados:
  - `data/raw/brasileirao_2026.parquet` (classificação)
  - `data/raw/partidas_brasileirao_2026.parquet` (partidas realizadas)
  - `data/raw/jogos_futuros_brasileirao_2026.parquet` (agenda de partidas)
  - `data/raw/transfermarkt_brasileirao_2026.parquet` (elencos e valores)
- O pipeline deve rodar em dois modos: carga histórica (Backfill) sob demanda e carga incremental (Daily) buscando as atualizações mais recentes.
- O Agente de IA deve ser capaz de distinguir quando usar o banco de dados local (via SQL) para dados tabulares e quando usar a internet (via Tavily) para notícias ou clima.

## 4. Regras e Decisões Arquiteturais

- **Estratégia de Ingestão:** DAGs separadas para Backfill e Incremental. Operações de Full Refresh garantem exclusividade de status das partidas.
- **Método de Extração (UOL):** A extração captura objetos JSON injetados diretamente nas tags `<script>` do HTML da página UOL. Expressões Regulares (`re`) são usadas para localizar e extrair os blocos de dados.
- **Método de Extração (Transfermarkt):** Arquitetura Crawler + Scraper em 2 passos, utilizando *delays* randômicos (3 a 5 segundos) entre requisições para evitar bloqueio.
- **Anti-Scraping:** O `curl_cffi` com `impersonate="chrome120"` substitui frameworks pesados, simulando fingerprints reais de navegador e passando por verificações de Cloudflare. Cookies de *consentimento* são injetados no header para burlar telas de privacidade.
- **Estrutura de Dados:** Tipagem estrita e tratamento numérico pesado na camada de Staging do dbt (ex: conversão de strings de euros formatadas para `BIGINT`).
- **Fan-in no dbt:** O `dbt_build` só é executado após **todas** as tasks de extração concluírem com sucesso.

## 5. Arquitetura de Extração (Scrapers)

### 5.1 `scrape_brasileirao_standings()`
- Extrai a classificação a partir do objeto `tableItems` (JSON no HTML).
- **Saída:** `data/raw/brasileirao_2026.parquet`

### 5.2 `scrape_brasileirao_matches()`
- Extrai resultados de partidas **encerradas** (`status == "match-ended"`).
- **Saída:** `data/raw/partidas_brasileirao_2026.parquet`

### 5.3 `scrape_brasileirao_jogos_futuros()`
- Reaproveita a lógica do scraper de partidas, mas filtra jogos **não encerrados** (`status != "match-ended"`).
- **Saída:** `data/raw/jogos_futuros_brasileirao_2026.parquet`

### 5.4 `scrape_transfermarkt_players()`
- Iteração na URL `/BRA1` para capturar os 20 links de times e, em seguida, navegação individual nas visões detalhadas (`/plus/1`) extraindo dados físicos e financeiros dos jogadores.
- **Saída:** `data/raw/transfermarkt_brasileirao_2026.parquet`

**Schema Bronze (Transfermarkt):**
| Coluna            | Tipo   |
|-------------------|--------|
| time_nome         | string |
| Nome              | string |
| Posição           | string |
| Idade             | string |
| Altura            | string |
| Pé                | string |
| Valor de Mercado  | string |

## 6. Orquestração (DAG)

**Arquivo:** `dags/extract_brasileirao.py`  
**Schedule:** `@daily` | **Catchup:** `False` | **Tags:** `ingestion`, `brasileirao`, `bronze`, `transfermarkt`

### Grafo de Dependências

```text
extract_standings_task ────────┐
extract_matches_task ──────────┼──► dbt_build
extract_future_matches_task ───┤
extract_transfermarket_task ───┘
```

As quatro extrações rodam **em paralelo** via TaskFlow API (`@task`). O `dbt_build` (via `BashOperator`) atua como consolidador final.

## 7. Camada de Transformação (dbt)

### 7.1 Staging

| Modelo                           | Materialização | Descrição / Tratamento                                                                 |
|----------------------------------|----------------|----------------------------------------------------------------------------------------|
| `stg_brasileirao`                | view           | Cast simples de inteiros.                                                              |
| `stg_matches_brasileirao`        | view           | Cast com `timestamptz` para datas.                                                     |
| `stg_matches_brasileirao_future` | view           | Permite placares nulos, focando apenas na agenda futura.                               |
| `stg_transfermarkt_players`      | view           | Normalização de *snake_case*, limpeza da string de `Altura` e regex pesado em `Valor de Mercado` para converter "€ X.XX mi" para `BIGINT` em euros (`valor_mercado_eur`). |

### 7.2 Marts

| Modelo                      | Materialização | Descrição e Lógica Principal                                                |
|-----------------------------|----------------|-----------------------------------------------------------------------------|
| `fct_classificacao`         | table          | Classificação com cálculo de `aproveitamento_pct`.                          |
| `dim_matches`               | table          | Jogos realizados. Contém formatação amigável de placar e cálculo de gols totais. |
| `dim_matches_future`        | table          | Agenda de jogos futuros. Modelagem defensiva para evitar duplicidade temporal com a tabela de jogos finalizados. |
| `dim_players_transfermarkt` | table          | Tabela consolidada contendo informações físicas e valuation em `BIGINT` (euros) de todos os jogadores da liga. |