{{ config(materialized='view') }}

with raw_data as (
    select *
    from read_parquet('{{ env_var("PROJECT_DATA_DIR", "../data") }}/raw/jogos_futuros_brasileirao_2026.parquet')
),

casted as (
    select
        cast(id_partida      as bigint)      as id_partida,
        cast(rodada          as integer)     as rodada,
        cast(data_hora       as timestamptz) as data_hora,
        cast(time_mandante   as varchar)     as time_mandante,
        cast(time_visitante  as varchar)     as time_visitante,
        cast(status          as varchar)     as status
    from raw_data
)

select * from casted
