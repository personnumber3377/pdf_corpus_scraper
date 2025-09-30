# github_ps_scrape.py
import os, time, pathlib, requests

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")  # create one and export it
OUT = pathlib.Path("ps_corpus"); OUT.mkdir(parents=True, exist_ok=True)

SESSION = requests.Session()
SESSION.headers.update({
    "Accept": "application/vnd.github+json",
    "User-Agent": "ps-corpus-scraper/1.0",
})
if GITHUB_TOKEN:
    SESSION.headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    SESSION.headers["X-GitHub-Api-Version"] = "2022-11-28"

def search_code(query: str, page: int = 1, per_page: int = 100):
    r = SESSION.get(
        "https://api.github.com/search/code",
        params={"q": query, "page": page, "per_page": per_page},
        timeout=30,
    )
    r.raise_for_status()  # <- your 401 was here; token fixes it
    return r.json()

def raw_url_from_item(item):
    repo = item["repository"]
    owner = repo["owner"]["login"]
    name = repo["name"]
    branch = repo.get("default_branch", "main")
    path = item["path"]
    return f"https://raw.githubusercontent.com/{owner}/{name}/{branch}/{path}"

def save_item(item):
    raw = raw_url_from_item(item)
    r = SESSION.get(raw, timeout=30)
    r.raise_for_status()
    # mirror into OUT/owner/repo/path
    repo = item["repository"]
    dst = OUT / repo["owner"]["login"] / repo["name"] / item["path"]
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(r.content)
    print("saved", dst)
    return dst

def scrape_ps(max_pages=10):
    # widen as you like: 'extension:ps OR extension:eps language:PostScript size:>0'
    query = 'extension:ps NOT annex size:<50000'
    page = 1
    while page <= max_pages:
        try:
            data = search_code(query, page=page)
        except requests.HTTPError as e:
            # handle rate limit (403) or auth (401) nicely
            if e.response is not None and e.response.status_code in (401, 403):
                print("Auth/rate issue:", e.response.text)
                reset = e.response.headers.get("X-RateLimit-Reset")
                if reset and GITHUB_TOKEN:
                    wait = max(0, int(reset) - int(time.time()) + 1)
                    print(f"Rate limited; sleeping {wait}s")
                    time.sleep(wait)
                    continue
                raise
            raise

        items = data.get("items", [])
        if not items:
            break
        for it in items:
            try:
                save_item(it)
            except Exception as e:
                print("skip", it.get("html_url"), e)
        page += 1
        # polite pacing to avoid secondary rate limits
        time.sleep(1.0)

if __name__ == "__main__":
    scrape_ps(max_pages=10)
