{{ config(materialized='table') }}

with source as (
    select *
    from {{ ref('stg_brasileirao') }}
),

calc_aproveitamento as (
    select
        time,
        jogos,
        vitorias,
        empates,
        derrotas,
        pontos,
        case 
            when jogos = 0 then 0.0
            else round((pontos * 100.0) / (jogos * 3), 2)
        end as aproveitamento_pct
    from source
)

select *
from calc_aproveitamento
order by pontos desc
