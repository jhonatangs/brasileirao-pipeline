{{ config(materialized='table') }}

with source as (
    select * from {{ ref('stg_matches_brasileirao') }}
),

enriched as (
    select
        id_partida,
        rodada,
        data_hora,
        time_mandante,
        time_visitante,
        placar_mandante                                             as gols_mandante,
        placar_visitante                                           as gols_visitante,

        -- Resultado da partida
        case
            when placar_mandante > placar_visitante then 'mandante'
            when placar_visitante > placar_mandante then 'visitante'
            else 'empate'
        end                                                        as resultado,

        -- Placar formatado
        cast(placar_mandante as varchar) || ' x ' ||
        cast(placar_visitante as varchar)                          as placar,

        -- Total de gols na partida
        placar_mandante + placar_visitante                         as total_de_gols_partida

    from source
)

select * from enriched
