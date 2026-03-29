# Brasileirão Pipeline - Spec

## 1. Objetivo

Construir um pipeline de dados ponta a ponta que extrai classificação e resultados de partidas do Brasileirão via UOL Esporte (Placar), transforma os dados em um Data Lakehouse local e permite consultas analíticas via um Agente de IA (Natural Language to SQL).

## 2. Stack de Tecnologias

- **Orquestração**: Apache Airflow via Astro CLI
- **Extração**: Python via `curl_cffi` e `re` (Regex)
- **Processamento/Transformação**: dbt (com DuckDB adapter)
- **Armazenamento**: DuckDB (Data Lakehouse local em `data/lakehouse.duckdb`)
- **Gerenciamento de Pacotes**: uv (Python 3.12)
- **IA/NLQ**: gpt-4o-mini via API com ferramentas (Functions/MCPs) para consultar o DuckDB

## 3. Requisitos Funcionais

- O pipeline deve extrair dados de **classificação** e **resultados de partidas** do Brasileirão através do UOL Esporte (Placar).
- O pipeline deve persistir a camada raw/bronze em arquivos Parquet:
  - `data/raw/brasileirao_2026.parquet` (classificação)
  - `data/raw/partidas_brasileirao_2026.parquet` (partidas)
- O pipeline deve rodar em dois modos: carga histórica (Backfill) sob demanda e carga incremental (Daily) buscando as atualizações mais recentes.

## 4. Regras e Decisões Arquiteturais

- **Estratégia de Ingestão:** DAGs separadas para Backfill e Incremental.
- **Método de Extração:** A extração captura objetos JSON injetados diretamente nas tags `<script>` do HTML da página UOL. Expressões Regulares (`re`) são usadas para localizar e extrair os blocos de dados, sendo a forma mais robusta contra mudanças visuais do site.
- **Anti-Scraping:** O `curl_cffi` com `impersonate="chrome110"` substitui frameworks pesados como Playwright e playwright-stealth, simulando fingerprints reais de navegador.
- **Estrutura de Dados:** Tipagem estrita nas camadas de Staging e Mart do dbt garante schema limpo e bem documentado para o Agente de IA.
- **Fan-in no dbt:** O `dbt_build` só é executado após **ambas** as tasks de extração concluírem com sucesso.

## 5. Arquitetura de Extração (Scrapers)

**Módulo:** `include/scrapers/br_scraper.py`  
Ambas as funções acessam a mesma URL do UOL Esporte com `curl_cffi` (`impersonate="chrome110"`).

### 5.1 `scrape_brasileirao_standings()`

- Extrai a classificação a partir do objeto `tableItems` embutido em uma tag `<script>`.
- Usa Regex para localizar o array e balanceamento de colchetes `[]` para extrair o JSON completo.
- **Saída:** `data/raw/brasileirao_2026.parquet`

**Schema Bronze:**

| Coluna   | Tipo   |
|----------|--------|
| time     | string |
| jogos    | int    |
| vitorias | int    |
| empates  | int    |
| derrotas | int    |
| pontos   | int    |

### 5.2 `scrape_brasileirao_matches()`

- Extrai resultados de partidas **encerradas** (`status = "match-ended"`) a partir dos objetos `football-match-{id}` e `football-team-{id}` embutidos no HTML.
- Usa Regex para iterar os objetos e balanceamento de chaves `{}` para extrair cada bloco JSON.
- Constrói um mapa `team_id → nome do time` para resolver os IDs de cada partida.
- **Saída:** `data/raw/partidas_brasileirao_2026.parquet`

**Schema Bronze:**

| Coluna          | Tipo                |
|-----------------|---------------------|
| id_partida      | Int64               |
| rodada          | Int64               |
| data_hora       | datetime64[ns, UTC] |
| time_mandante   | str                 |
| time_visitante  | str                 |
| placar_mandante | Int64               |
| placar_visitante| Int64               |

## 6. Orquestração (DAG)

**Arquivo:** `dags/extract_brasileirao.py`  
**Schedule:** `@daily` | **Catchup:** `False` | **Tags:** `ingestion`, `brasileirao`, `bronze`

### Grafo de Dependências

```
extract_standings_task ──┐
                          ├──► dbt_build
extract_matches_task   ──┘
```

As tasks `extract_standings` e `extract_matches` rodam **em paralelo** via TaskFlow API (`@task`). O `dbt_build` (via `BashOperator`) só é acionado após ambas concluírem (fan-in).

**Comando dbt:**
```bash
dbt build --project-dir /usr/local/airflow/dbt_brasileirao --profiles-dir /usr/local/airflow/dbt_brasileirao
```

## 7. Camada de Transformação (dbt)

### 7.1 Staging

| Modelo                    | Fonte                                        | Materialização |
|---------------------------|----------------------------------------------|----------------|
| `stg_brasileirao`         | `data/raw/brasileirao_2026.parquet`          | view           |
| `stg_matches_brasileirao` | `data/raw/partidas_brasileirao_2026.parquet` | view           |

**`stg_matches_brasileirao`** aplica tipagem explícita via `CAST`:

| Coluna          | Tipo DuckDB  |
|-----------------|--------------|
| id_partida      | bigint       |
| rodada          | integer      |
| data_hora       | timestamptz  |
| time_mandante   | varchar      |
| time_visitante  | varchar      |
| placar_mandante | integer      |
| placar_visitante| integer      |

### 7.2 Marts

| Modelo              | Fonte                     | Materialização | Descrição                                   |
|---------------------|---------------------------|----------------|---------------------------------------------|
| `fct_classificacao` | `stg_brasileirao`         | table          | Classificação com `aproveitamento_pct`      |
| `dim_matches`       | `stg_matches_brasileirao` | table          | Resultado, placar formatado e total de gols |

**`dim_matches`** — colunas calculadas:

| Coluna                  | Lógica                                                         |
|-------------------------|----------------------------------------------------------------|
| `resultado`             | `'mandante'`, `'visitante'` ou `'empate'` (CASE WHEN)         |
| `placar`                | `gols_mandante \|\| ' x ' \|\| gols_visitante` (varchar)      |
| `total_de_gols_partida` | `placar_mandante + placar_visitante`                           |