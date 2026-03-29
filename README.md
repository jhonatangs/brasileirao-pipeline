# 🏟️ Brasileirão 2026: Data Lakehouse & AI Analítico

Este projeto é um ecossistema de dados ponta a ponta que transforma informações brutas do Campeonato Brasileiro 2026 em inteligência analítica. O sistema combina um **Data Lakehouse local** com um **Agente de IA (NL2SQL)** dotado de memória de longo prazo para responder consultas complexas via linguagem natural.

## 🚀 Arquitetura do Sistema

O pipeline segue a filosofia de **Medallion Architecture** (Bronze, Silver e Gold), garantindo dados limpos, tipados e prontos para consumo. A orquestração paralela e a camada de IA garantem um fluxo contínuo e inteligente:

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#e1f5fe', 'edgeLabelBackground':'#ffffff', 'tertiaryColor': '#fff'}}}%%
graph TD
    %% Fontes de Dados
    subgraph "Sources (Web)"
        UOL[UOL Esporte Placar]
        TM[Transfermarkt (Future)]
    end

    %% Camada de Ingestão (Orquestrada pelo Airflow)
    subgraph "Ingestion & Bronze (Parquet)"
        AF[Apache Airflow Dag]
        SCR1[Scraper Classificação]
        SCR2[Scraper Partidas]
        
        AF -->|Orquestra| SCR1
        AF -->|Orquestra| SCR2
        
        UOL -->|Extract| SCR1
        UOL -->|Extract| SCR2
        
        RAW1[brasileirao_2026.parquet]
        RAW2[partidas_brasileirao_2026.parquet]
        
        SCR1 -->|Write| RAW1
        SCR2 -->|Write| RAW2
    end

    %% Camada de Transformação (dbt + DuckDB)
    subgraph "Transformation & Gold (Lakehouse)"
        DBT[dbt build]
        DKDB[(data/lakehouse.duckdb)]
        
        AF -->|Trigger| DBT
        
        RAW1 -->|Read| DBT
        RAW2 -->|Read| DBT
        
        STG1[stg_brasileirao]
        STG2[stg_matches]
        FCT1[fct_classificacao]
        DIM1[dim_matches]
        
        DBT -->|Creates| STG1
        DBT -->|Creates| STG2
        STG1 -->|Transforms| FCT1
        STG2 -->|Transforms| DIM1
        
        FCT1 -->|Persists| DKDB
        DIM1 -->|Persists| DKDB
    end

    %% Camada de Consumo e IA
    subgraph "AI Agent & Memory"
        AGENT[AI Agent (gpt-4o-mini)]
        MEM[Mem0 Layer]
        QDR[(data/qdrant_memory)]
        
        USER[Usuário] -->|Pergunta NL| AGENT
        
        AGENT <-->|Contexto| MEM
        MEM <-->|Persists| QDR
        
        TOOL1[Tool: run_query]
        TOOL2[Tool: search_web (Future)]
        
        AGENT -->|Usa| TOOL1
        AGENT -->|Usa| TOOL2
        
        TOOL1 <-->|Execute SQL| DKDB
    end

    %% Estilização
    style AF fill:#f96,stroke:#333,stroke-width:2px,color:white
    style DBT fill:#ff6f00,stroke:#333,stroke-width:2px,color:white
    style DKDB fill:#0277bd,stroke:#333,stroke-width:2px,color:white
    style AGENT fill:#7e57c2,stroke:#333,stroke-width:2px,color:white
    style MEM fill:#26a69a,stroke:#333,stroke-width:2px,color:white
    style QDR fill:#00695c,stroke:#333,stroke-width:2px,color:white
```

### Detalhamento das Camadas

1.  **Ingestão (Bronze):** Scrapers customizados em Python (`curl_cffi` + `Regex`) extraem classificação e resultados de partidas do portal UOL Esporte, persistindo em arquivos **Parquet** de forma idempotente.
2.  **Orquestração:** **Apache Airflow** (via Astro CLI) gerencia o fluxo em paralelo, garantindo que o processamento só inicie após a extração bem-sucedida de todas as fontes.
3.  **Transformação (Silver/Gold):** O **dbt (data build tool)** com adapter **DuckDB** realiza a limpeza, casting de tipos e criação de métricas de negócio (aproveitamento, saldo de gols, médias consolidadas).
4.  **Armazenamento:** **DuckDB** atua como motor de Lakehouse local, oferecendo performance analítica de alto nível com zero infraestrutura.
5.  **Camada de IA:** Um agente baseado em **GPT-4o-mini** utiliza *Function Calling* para traduzir perguntas em queries SQL precisas, consultando o Lakehouse em tempo real.
6.  **Memória Persistente:** Integração com **Mem0** e **Qdrant** (Vector Database) para permitir que o agente aprenda e recorde preferências do usuário (como o time do coração) entre diferentes sessões.

## 🧠 Diferenciais Técnicos

-   **Diagrama de Arquitetura Mermaid:** Visualização clara do fluxo do dado, desde a fonte até o consumo pela LLM.
-   **Consolidação Esportiva via SQL:** O agente utiliza lógica avançada de `UNION ALL` e `CTEs` para consolidar estatísticas de mandantes e visitantes, evitando duplicidade e erros comuns em dados de partidas.
-   **Resiliência e Persistência:** Implementação de encerramento seguro de conexões (*graceful shutdown*) para garantir a integridade das memórias vetoriais no disco.
-   **Local-First & Portável:** Todo o estado da aplicação (Dados no DuckDB e Memória no Qdrant) reside na pasta `data/`, permitindo backup e portabilidade total do projeto.
-   **Prompt Engineering:** System prompts rigorosos com regras de fidelidade absoluta aos dados, impedindo alucinações numéricas e garantindo respostas baseadas em fatos.

## 🛠️ Stack Tecnológica

-   **Linguagem:** Python 3.12 (Gerenciado com `uv`)
-   **Orquestração:** Apache Airflow
-   **Transformação:** dbt-core
-   **Bancos de Dados:** DuckDB (Relacional/Analítico) & Qdrant (Vetorial)
-   **IA/LLM:** OpenAI API & Mem0 (Memory Layer)
-   **Scraping:** curl_cffi (Impersonate Chrome)

## 📈 Estrutura de Pastas

```text
├── agent/               # Lógica do Agente de IA, Memória e Tools
├── dags/                # Orquestração das extrações (Airflow)
├── data/                # Lakehouse (DuckDB) e Memória Vetorial (Qdrant)
├── dbt_brasileirao/     # Modelos dbt (Staging e Marts)
├── include/             # Scrapers e scripts de suporte
└── main.py              # Interface de chat via terminal
```

## ⚙️ Como Executar

1.  **Instale as dependências:**
    ```bash
    uv sync
    ```
2.  **Configure as variáveis de ambiente:**
    Crie um arquivo `.env` com sua `OPENAI_API_KEY` e `USER_ID`.
3.  **Inicie o Pipeline:**
    ```bash
    astro dev start
    ```
4.  **Inicie o Agente Analítico:**
    ```bash
    uv run python main.py
    ```

---