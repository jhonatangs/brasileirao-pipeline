# Brasileirão Pipeline - Spec

## 1. Objetivo

Construir um pipeline de dados ponta a ponta que extrai estatísticas avançadas e classificação do Brasileirão da fonte UOL Esporte (Placar), transforma os dados em um Data Lakehouse local e permite consultas analíticas via um Agente de IA (Natural Language to SQL).

## 2. Stack de Tecnologias

- **Orquestração**: Apache Airflow via Astro CLI
- **Extração**: Python via `curl_cffi` e `re` (Regex)
- **Processamento/Transformação**: dbt
- **Armazenamento**: DuckDB (Data Lakehouse)
- **Gerenciamento de Pacotes**: uv (Python 3.12)
- **IA/NLQ**: gpt-4o-mini via API com ferramentas (Functions/MCPs) para consultar o DuckDB

## 3. Requisitos Funcionais
- O pipeline deve extrair os dados de classificação e estatísticas do Brasileirão através do UOL Esporte (Placar).
- O pipeline deve persistir a camada raw/bronze através do arquivo de saída `data/raw/brasileirao_2026.parquet`.
- O pipeline deve rodar em dois modos: carga histórica (Backfill) rodando sob demanda, e carga incremental (Daily) buscando as atualizações mais recentes.

## 4. Regras e Decisões Arquiteturais
- **Estratégia de Ingestão:** DAGs separadas para Backfill e Incremental.
- **Método de Extração:** A extração deve capturar o objeto JSON `tableItems` injetado diretamente na tag `<script>` do HTML da página. O uso de Expressões Regulares (`re`) é recomendado, sendo esta a forma mais robusta para evitar quebras no script devido a mudanças visuais e de interface no site.
- **Anti-Scraping:** O método de scraping abandona frameworks pesados como o Playwright e playwright-stealth, adotando o `curl_cffi` para simular requisições seguras por meio de fingerprints do navegador e lidar com as medidas de bloqueio eficientemente.
- **Esquema Bronze (Contrato de Dados):** As seguintes colunas devem estar presentes no DataFrame final, tipadas corretamente, antes de salvar o parquet:
  - `time` (string)
  - `jogos` (int)
  - `vitorias` (int)
  - `empates` (int)
  - `derrotas` (int)
  - `pontos` (int)
- **Estrutura de Dados:** Uso de tipagem estrita no dbt (Staging, Intermediate, Mart) para garantir que o Agente de IA receba um schema limpo e bem documentado.