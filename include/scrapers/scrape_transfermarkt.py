import pandas as pd
import time
import random
import os
from curl_cffi import requests
from bs4 import BeautifulSoup

def scrape_transfermarkt():
    """
    Scrapes all Série A clubs squads from Transfermarkt.
    Saves the data to data/raw/transfermarkt_brasileirao_2026.parquet.
    """
    base_url = "https://www.transfermarkt.com.br"
    league_url = f"{base_url}/campeonato-brasileiro-serie-a/startseite/wettbewerb/BRA1"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    cookies = {"consent-prop": "true"}
    
    # Initialize session with impersonation
    session = requests.Session(impersonate="chrome120")
    
    print(f"Step 1: Fetching league page to get club links: {league_url}")
    try:
        response = session.get(league_url, headers=headers, cookies=cookies)
        response.raise_for_status()
    except Exception as e:
        print(f"CRITICAL ERROR: Failed to fetch league page: {e}")
        return
    
    soup = BeautifulSoup(response.text, 'html.parser')
    # The table with class 'items' usually contains the club list
    table = soup.find('table', class_='items')
    if not table:
        print("ERROR: Could not find clubs table. Check if the class 'items' still exists.")
        return
    
    clubs = []
    # Club links are typically in the 'hauptlink' cells within the table
    links = table.find_all('td', class_='hauptlink')
    for link_td in links:
        a = link_td.find('a')
        if a and 'href' in a.attrs:
            club_name = a.text.strip()
            club_url = a['href']
            # Convert startseite link to detailed kader view
            # Link format usually: /club-name/startseite/verein/ID/saison_id/YEAR
            # Target format: /club-name/kader/verein/ID/saison_id/YEAR/plus/1
            squad_url = f"{base_url}{club_url.replace('/startseite/', '/kader/')}/plus/1"
            clubs.append({'name': club_name, 'url': squad_url})
    
    # Deduplicate club list (links may appear multiple times due to logos/names)
    seen_urls = set()
    unique_clubs = []
    for c in clubs:
        if c['url'] not in seen_urls:
            unique_clubs.append(c)
            seen_urls.add(c['url'])
    
    print(f"Found {len(unique_clubs)} clubs. Proceeding to scrape squads...")
    
    all_players = []
    
    for club in unique_clubs:
        club_name = club['name']
        squad_url = club['url']
        
        # Respectful delay
        delay = random.randint(3, 5)
        print(f"Waiting {delay}s before scraping {club_name}...")
        time.sleep(delay)
        
        try:
            resp = session.get(squad_url, headers=headers, cookies=cookies)
            resp.raise_for_status()
            
            s_soup = BeautifulSoup(resp.text, 'html.parser')
            s_table = s_soup.find('table', class_='items')
            if not s_table:
                print(f"WARNING: No squad table found for {club_name}")
                continue
            
            # The squad table body contains the players
            tbody = s_table.find('tbody')
            if not tbody:
                continue
                
            rows = tbody.find_all('tr', recursive=False)
            for row in rows:
                # Regular rows represent players; odd/even/selected classes
                cols = row.find_all('td', recursive=False)
                if len(cols) < 5: 
                    # Probably a sub-header (e.g., "Goleiros") or spacer
                    continue
                
                player_data = {'time_nome': club_name}
                
                # Column 1 (index 1) usually contains Name and Position in a sub-table
                # Using selectors for precision
                info_td = cols[1]
                name_a = info_td.select_one('table.inline-table tr td.hauptlink a')
                if not name_a:
                    # Fallback for name
                    name_a = info_td.find('a')
                
                player_data['Nome'] = name_a.text.strip() if name_a else "N/A"
                
                pos_td = info_td.select_one('table.inline-table tr:nth-of-type(2) td')
                player_data['Posição'] = pos_td.text.strip() if pos_td else "N/A"
                
                # Based on 'plus/1' layout:
                # 0: #
                # 1: Info (Name/Pos)
                # 2: Age (Nasc./Idade)
                # 3: Nat
                # 4: Height
                # 5: Foot
                # 6: Joined (No time desde)
                # 7: Previous Club (Anterior)
                # 8: Contract (Contrato)
                # 9: Market Value (Valor de Mercado)
                
                if len(cols) >= 10:
                    # Age is usually at index 2
                    player_data['Idade'] = cols[2].text.strip().split('(')[-1].replace(')', '') if '(' in cols[2].text else cols[2].text.strip()
                    
                    # Nat can be multiple flags at index 3
                    nats = cols[3].find_all('img')
                    player_data['Nacionalidade'] = ", ".join([img.get('title', '') for img in nats]) if nats else "N/A"
                    
                    player_data['Altura'] = cols[4].text.strip()
                    player_data['Pé'] = cols[5].text.strip()
                    player_data['No time desde'] = cols[6].text.strip()
                    
                    # Previous club at index 7
                    prev_club_img = cols[7].find('img')
                    if prev_club_img:
                        player_data['Anterior'] = prev_club_img.get('title', '').strip()
                    else:
                        player_data['Anterior'] = cols[7].text.strip()
                    
                    player_data['Contrato'] = cols[8].text.strip()
                    # Market value at index 9
                    player_data['Valor de Mercado'] = cols[9].text.strip()
                
                all_players.append(player_data)
                
        except Exception as e:
            print(f"ERROR: Failed to scrape {club_name}: {e}")
            continue

    if not all_players:
        print("ERROR: No player data extracted.")
        return

    # Finalize DataFrame
    df = pd.DataFrame(all_players)
    
    # Ensure directory exists
    os.makedirs('data/raw', exist_ok=True)
    output_path = 'data/raw/transfermarkt_brasileirao_2026.parquet'
    
    # Export to Parquet
    print(f"Exporting {len(df)} players to {output_path}...")
    df.to_parquet(output_path, index=False)
    print("Export completed successfully.")

if __name__ == "__main__":
    scrape_transfermarkt()
