{{ config(materialized='view') }}

with raw_data as (
    select *
    from read_parquet('{{ env_var("PROJECT_DATA_DIR", "../data") }}/raw/partidas_brasileirao_2026.parquet')
),

casted as (
    select
        cast(id_partida       as bigint)                    as id_partida,
        cast(rodada           as integer)                   as rodada,
        cast(data_hora        as timestamptz)               as data_hora,
        cast(time_mandante    as varchar)                   as time_mandante,
        cast(time_visitante   as varchar)                   as time_visitante,
        cast(placar_mandante  as integer)                   as placar_mandante,
        cast(placar_visitante as integer)                   as placar_visitante
    from raw_data
)

select * from casted
