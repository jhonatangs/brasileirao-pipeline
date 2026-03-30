{{
    config(
        materialized='table'
    )
}}

WITH stg_players AS (
    SELECT * FROM {{ ref('stg_transfermarkt_players') }}
),

dim_players AS (
    SELECT
        -- Gerando um ID único para o jogador baseado no nome, time, posição e idade
        MD5(nome || '-' || time_nome || '-' || posicao || '-' || CAST(idade AS VARCHAR)) AS id_jogador,
        nome,
        time_nome,
        posicao,
        idade,
        nacionalidade,
        altura,
        pe,
        contrato,
        valor_mercado_eur,
        valor_mercado_bruto
    FROM stg_players
)

SELECT * FROM dim_players
