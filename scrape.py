import requests
import os

QUERY = 'extension:ps'
OUTPUT_DIR = 'ps_corpus'
os.makedirs(OUTPUT_DIR, exist_ok=True)

def search_github(query, page=1):
    url = f'https://api.github.com/search/code?q={query}&page={page}&per_page=100'
    r = requests.get(url, headers={'Accept': 'application/vnd.github.v3.text-match+json'})
    r.raise_for_status()
    return r.json()

page = 1
while True:
    data = search_github(QUERY, page)
    items = data.get('items', [])
    if not items:
        break
    for item in items:
        raw_url = item['html_url'].replace('github.com', 'raw.githubusercontent.com').replace('/blob/', '/')
        try:
            resp = requests.get(raw_url)
            resp.raise_for_status()
            fname = os.path.join(OUTPUT_DIR, os.path.basename(item['path']))
            with open(fname, 'wb') as f:
                f.write(resp.content)
            print(f"Saved {fname}")
        except Exception as e:
            print(f"Failed {raw_url}: {e}")
    page += 1
