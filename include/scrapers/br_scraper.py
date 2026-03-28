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

if __name__ == "__main__":
    scrape_brasileirao_standings()
