
{{
    config(
        materialized='view'
    )
}}

WITH source_data AS (
    SELECT *
    FROM read_parquet('{{ env_var("PROJECT_DATA_DIR", "../data") }}/raw/transfermarkt_brasileirao_2026.parquet')
),

renamed_and_cleaned AS (
    SELECT
        time_nome,
        "Nome" AS nome,
        "Posição" AS posicao,
        CAST(NULLIF("Idade", '') AS INTEGER) AS idade,
        "Nacionalidade" AS nacionalidade,
        -- Altura: "1,85 m", "2.04m", "-" -> 1.85, 2.04, NULL
        CAST(
            NULLIF(
                REGEXP_REPLACE(REPLACE("Altura", ',', '.'), '[^0-9.]', '', 'g'),
                ''
            ) AS DECIMAL(3,2)
        ) AS altura,
        "Pé" AS pe,
        "Contrato" AS contrato,
        "Valor de Mercado" AS valor_mercado_bruto,
        -- Valor de Mercado: "€4.50m", "€500k", "€4,50 mi.", etc.
        CASE
            WHEN "Valor de Mercado" IS NULL OR "Valor de Mercado" IN ('-', '') THEN NULL
            ELSE (
                CAST(
                    REGEXP_REPLACE(
                        REGEXP_REPLACE(
                            REPLACE("Valor de Mercado", '€', ''),
                            '(?i)( mil| mi\.?| m| k)', '', 'g'
                        ),
                        ',', '.'
                    ) AS DECIMAL(18,2)
                ) * 
                CASE 
                    -- Millions: 'm' or 'mi', but not 'mil'
                    WHEN ("Valor de Mercado" ILIKE '%m%' OR "Valor de Mercado" ILIKE '%mi%') 
                         AND "Valor de Mercado" NOT ILIKE '%mil%' THEN 1000000 
                    -- Thousands: 'k' or 'mil'
                    WHEN "Valor de Mercado" ILIKE '%k%' OR "Valor de Mercado" ILIKE '%mil%' THEN 1000 
                    ELSE 1 
                END
            )::BIGINT
        END AS valor_mercado_eur
    FROM source_data
)

SELECT * FROM renamed_and_cleaned
