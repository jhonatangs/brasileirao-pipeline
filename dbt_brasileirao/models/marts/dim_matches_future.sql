{{ config(materialized='table') }}

with future_matches as (
    select * from {{ ref('stg_matches_brasileirao_future') }}
),

finished_matches as (
    select id_partida from {{ ref('stg_matches_brasileirao') }}
),

final as (
    select
        f.*
    from future_matches f
    left join finished_matches m on f.id_partida = m.id_partida
    where m.id_partida is null
)

select * from final
