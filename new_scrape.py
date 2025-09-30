import os
import requests
from urllib.parse import quote
import random
import subprocess
import tempfile
import shutil

# ==== CONFIG ====
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")  # set your token in env
# SEARCH_QUERY = 'extension:ps OR extension:eps size:<200000'  # tweak for size limits
SEARCH_QUERY = 'A extension:pdf size:<2000000'  # tweak for size limits
OUTPUT_DIR = "pdf_corpus"
MAX_PAGES = 2000  # number of search pages to fetch (100 files per page)
# ===============

if not GITHUB_TOKEN:
    raise RuntimeError("Please set GITHUB_TOKEN environment variable with a GitHub personal access token")

os.makedirs(OUTPUT_DIR, exist_ok=True)
EXISTING = os.listdir(OUTPUT_DIR)
session = requests.Session()
session.headers.update({
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
})

def is_git_lfs(content: bytes) -> bool:
    """Detect Git LFS pointer files."""
    text = content.decode("utf-8", errors="ignore")
    return text.startswith("version https://git-lfs.github.com/spec/v1")

'''
def fetch_lfs_file(item, output_path):
    repo_url = item["repository"]["html_url"]
    file_path = item["path"]
    print(f"    [*] Fetching LFS file from {repo_url} ({file_path})")

    tmpdir = tempfile.mkdtemp()
    try:
        # Clone repo shallowly, blobs off
        subprocess.check_call([
            "git", "clone", "--depth", "1", "--filter=blob:none",
            repo_url, tmpdir
        ])
        # Pull the specific LFS file
        subprocess.check_call(["git", "lfs", "pull", "-I", file_path], cwd=tmpdir)

        # Copy file to output_path
        src_path = os.path.join(tmpdir, file_path)
        if os.path.exists(src_path):
            shutil.copy(src_path, output_path)
            print(f"    [✓] Saved LFS file to {output_path}")
        else:
            print("    [!] LFS file not found after pull")
    except Exception as e:
        print(f"    [!] Failed to fetch LFS file: {e}")
    finally:
        shutil.rmtree(tmpdir)
'''

def fetch_lfs_file(item, output_path):
    repo_url = item["repository"]["html_url"]
    repo_name = item["repository"]["full_name"].replace("/", "_")
    print(f"    [*] Fetching ALL PDFs from {repo_url}")

    tmpdir = tempfile.mkdtemp()
    try:
        # Clone repo shallowly, blobs off
        subprocess.check_call([
            "git", "clone", "--depth", "1", "--filter=blob:none",
            repo_url, tmpdir
        ])

        # Fetch ALL .pdf files tracked by LFS
        subprocess.check_call(["git", "lfs", "pull", "-I", "*.pdf"], cwd=tmpdir)

        # Now walk the repo tree and copy every real PDF
        for root, _, files in os.walk(tmpdir):
            for f in files:
                if f.lower().endswith(".pdf"):
                    src_path = os.path.join(root, f)
                    # Skip if it’s still a .fetch placeholder
                    if src_path.endswith(".pdf.fetch"):
                        continue
                    # Build output filename with repo prefix
                    rel_path = os.path.relpath(src_path, tmpdir)
                    safe_name = repo_name + "__" + rel_path.replace(os.sep, "_")
                    dst_path = os.path.join(OUTPUT_DIR, safe_name)
                    try:
                        shutil.copy(src_path, dst_path)
                        print(f"    [✓] Saved {dst_path}")
                    except Exception as e:
                        print(f"    [!] Failed to copy {src_path}: {e}")

    except Exception as e:
        print(f"    [!] Failed to fetch PDFs from {repo_url}: {e}")
    finally:
        shutil.rmtree(tmpdir)

def is_git_annex(content: bytes) -> bool:
    """Detect git-annex pointer files."""
    first_line = content.split(b"\n", 1)[0]
    return b".git/annex" in first_line or b"SHA256E-" in first_line

'''
def download_file(item):
    raw_url = item["html_url"].replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
    print(f"[+] Downloading {raw_url}")
    filename = raw_url[raw_url.rfind("/")+1:] # Get the thing
    print(filename)
    if any(filename in s for s in EXISTING):
        print(f"[✓] Already have {filename} !!!")
        return
    r = session.get(raw_url)
    try:
        r.raise_for_status()
    except:
        return
    data = r.content

    if is_git_annex(data):
        print("    [-] Skipped git-annex pointer file.")
        return

    filename = f"{item['repository']['full_name'].replace('/', '_')}__{item['name']}"
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(data)
    print(f"    [✓] Saved {filepath} ({len(data)} bytes)")
'''

def download_file(item):
    raw_url = item["html_url"].replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
    print(f"[+] Downloading {raw_url}")
    filename = f"{item['repository']['full_name'].replace('/', '_')}__{item['name']}"
    filepath = os.path.join(OUTPUT_DIR, filename)
    if any(filename in s for s in EXISTING):
        print(f"[✓] Already have {filename}")
        return
    r = session.get(raw_url)
    try:
        r.raise_for_status()
    except:
        return
    data = r.content

    if is_git_annex(data):
        print("    [-] Skipped git-annex pointer file.")
        return

    if is_git_lfs(data):
        fetch_lfs_file(item, filepath)
        return

    with open(filepath, "wb") as f:
        f.write(data)
    print(f"    [✓] Saved {filepath} ({len(data)} bytes)")

for page in range(0, 1000):
    actual_page = random.randrange(1, MAX_PAGES)
    search_url = f"https://api.github.com/search/code?q={quote(SEARCH_QUERY)}&page={page}&per_page=100"
    print(f"[PAGE {page}] {search_url}")
    r = session.get(search_url)
    r.raise_for_status()
    items = r.json().get("items", [])
    if not items:
        break

    for item in items:
        try:
            download_file(item)
        except Exception as e:
            print(f"    [!] Error: {e}")
