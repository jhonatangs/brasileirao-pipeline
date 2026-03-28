import os
import re
import json
import pandas as pd
from curl_cffi import requests
def scrape_brasileirao_standings():
    # Caminho do arquivo de saída
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    output_dir = os.path.join(project_root, "data", "raw")
    output_file = os.path.join(output_dir, "brasileirao_2026.parquet")
    
    os.makedirs(output_dir, exist_ok=True)
    
    url = "https://www.uol.com.br/esporte/futebol/campeonatos/brasileirao/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        "Referer": "https://www.google.com/"
    }
    
    try:
        response = requests.get(url, headers=headers, impersonate="chrome110")
    except Exception as e:
        print(f"Erro na requisição: {e}")
        return
        
    if response.status_code != 200:
        print(f"Erro ao acessar UOL. Status Code: {response.status_code}")
        return
        
    # Extração de Texto: procurar JSON pelo padrão que começa próximo aos dados da tabela
    match = re.search(r'"tableItems":\s*(\[)', response.text)
    if not match:
        print(f"Não foi encontrado o JSON de 'tableItems'. Resposta parcial:\n{response.text[:500]}")
        return
        
    start_idx = match.start(1)
    
    # Função auxiliar para encontrar o fechamento correto da string JSON
    def find_brackets(text, start):
        count = 0
        for i in range(start, len(text)):
            if text[i] == '[':
                count += 1
            elif text[i] == ']':
                count -= 1
            if count == 0:
                return text[start:i+1]
        return ""
        
    arr_str = find_brackets(response.text, start_idx)
    
    if not arr_str:
        print("Não foi possível extrair o array JSON de tableItems.")
        return
        
    try:
        # Processamento: Converta a string capturada em um dicionário Python (json.loads)
        # Vamos contornar o array em um dicionário para "navegar até chegar em tableItems"
        json_str = f'{{"tableItems": {arr_str}}}'
        data_dict = json.loads(json_str)
        
        # Navegue no dicionário até chegar em tableItems
        table_items = data_dict.get("tableItems", [])
    except json.JSONDecodeError as e:
        print(f"Erro ao parsear JSON: {e}")
        return
        
    parsed_data = []
    
    # Itere sobre os itens e extraia: name (time), pts (pontos), pl (jogos), w (vitorias), d (empates), l (derrotas)
    for item in table_items:
        parsed_data.append({
            "time": item.get("name"),
            "jogos": item.get("pl"),
            "vitorias": item.get("w"),
            "empates": item.get("d"),
            "derrotas": item.get("l"),
            "pontos": item.get("pts")
        })
        
    df = pd.DataFrame(parsed_data)
    
    # Pandas: Crie o DataFrame com as colunas padronizadas
    required_cols = ["time", "jogos", "vitorias", "empates", "derrotas", "pontos"]
    final_cols = [c for c in required_cols if c in df.columns]
    
    df = df[final_cols]
    
    try:
        df.to_parquet(output_file, index=False)
        print(f"Dados salvos com sucesso em {output_file}")
    except Exception as e:
        print(f"Erro ao salvar parquet: {e}")


def scrape_brasileirao_matches():
    """
    Extrai os jogos do Brasileirão 2026 da página UOL Esporte.
    Filtra apenas partidas encerradas (status=match-ended) e salva
    em data/raw/partidas_brasileirao_2026.parquet.

    Schema de saída:
        id_partida       (int)
        rodada           (int)
        data_hora        (datetime64[ns, UTC])
        time_mandante    (str)
        time_visitante   (str)
        placar_mandante  (int)
        placar_visitante (int)
    """
    # Caminho do arquivo de saída
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    output_dir = os.path.join(project_root, "data", "raw")
    output_file = os.path.join(output_dir, "partidas_brasileirao_2026.parquet")

    os.makedirs(output_dir, exist_ok=True)

    url = "https://www.uol.com.br/esporte/futebol/campeonatos/brasileirao/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        "Referer": "https://www.google.com/"
    }

    try:
        response = requests.get(url, headers=headers, impersonate="chrome110")
    except Exception as e:
        print(f"Erro na requisição: {e}")
        return

    if response.status_code != 200:
        print(f"Erro ao acessar UOL. Status Code: {response.status_code}")
        return

    text = response.text

    # Função auxiliar: encontra o fechamento correto de um objeto JSON via balanceamento de chaves
    def find_braces(text, start):
        count = 0
        for i in range(start, len(text)):
            if text[i] == '{':
                count += 1
            elif text[i] == '}':
                count -= 1
            if count == 0:
                return text[start:i + 1]
        return ""

    # Construir mapeamento: team_id (int) -> nome do time
    # Os dados de time estão dispersos no HTML como "football-team-{id}": {...}
    teams_map = {}
    for m in re.finditer(r'"football-team-\d+":\s*(\{)', text):
        obj_str = find_braces(text, m.start(1))
        if not obj_str:
            continue
        try:
            team_data = json.loads(obj_str)
            tid = team_data.get("id")
            name = team_data.get("name")
            if tid is not None and name:
                teams_map[tid] = name
        except json.JSONDecodeError:
            continue

    if not teams_map:
        print("Não foram encontrados dados de times (football-team-*).")
        return

    # Iterar sobre partidas, filtrando apenas as encerradas
    # Cada partida está no HTML como "football-match-{id}": {...}
    parsed_data = []
    for m in re.finditer(r'"football-match-\d+":\s*(\{)', text):
        obj_str = find_braces(text, m.start(1))
        if not obj_str:
            continue
        try:
            match_data = json.loads(obj_str)
        except json.JSONDecodeError:
            continue

        if match_data.get("status") != "match-ended":
            continue

        home_id = match_data.get("teams", {}).get("home")
        away_id = match_data.get("teams", {}).get("away")
        goals = match_data.get("score", {}).get("goals", {})

        parsed_data.append({
            "id_partida":       match_data.get("id"),
            "rodada":           match_data.get("round"),
            "data_hora":        match_data.get("isoDate"),
            "time_mandante":    teams_map.get(home_id, str(home_id)),
            "time_visitante":   teams_map.get(away_id, str(away_id)),
            "placar_mandante":  goals.get("home"),
            "placar_visitante": goals.get("away"),
        })


    if not parsed_data:
        print("Nenhuma partida encerrada encontrada.")
        return

    df = pd.DataFrame(parsed_data)

    # Tipagem explícita
    df["id_partida"]       = df["id_partida"].astype("Int64")
    df["rodada"]           = df["rodada"].astype("Int64")
    df["data_hora"]        = pd.to_datetime(df["data_hora"], utc=True)
    df["time_mandante"]    = df["time_mandante"].astype(str)
    df["time_visitante"]   = df["time_visitante"].astype(str)
    df["placar_mandante"]  = df["placar_mandante"].astype("Int64")
    df["placar_visitante"] = df["placar_visitante"].astype("Int64")

    df = df.sort_values(["rodada", "data_hora"]).reset_index(drop=True)

    try:
        df.to_parquet(output_file, index=False)
        print(f"Partidas salvas com sucesso em {output_file} ({len(df)} registros)")
    except Exception as e:
        print(f"Erro ao salvar parquet: {e}")


if __name__ == "__main__":
    scrape_brasileirao_standings()
    scrape_brasileirao_matches()
