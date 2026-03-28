{{ config(materialized='view') }}

with raw_data as (
    select *
    from read_parquet('{{ env_var('PROJECT_DATA_DIR', '../data') }}/raw/brasileirao_2026.parquet')
),

casted as (
    select
        cast(time as varchar) as time,
        cast(jogos as integer) as jogos,
        cast(vitorias as integer) as vitorias,
        cast(empates as integer) as empates,
        cast(derrotas as integer) as derrotas,
        cast(pontos as integer) as pontos
    from raw_data
)

select * from casted
