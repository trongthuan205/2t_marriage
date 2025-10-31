# save as fetch_html_css.py
import os, re, sys, pathlib, hashlib
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

def safe_name(url: str) -> str:
    p = urlparse(url)
    base = (p.path.rsplit('/', 1)[-1] or "index").split('?')[0]
    if not base.endswith('.css'):
        base += ".css"
    # ensure uniqueness with a short hash
    h = hashlib.sha1(url.encode()).hexdigest()[:8]
    return f"{h}-{base}"

def fetch(url: str, outdir: str = "output"):
    os.makedirs(outdir, exist_ok=True)
    assets_dir = os.path.join(outdir, "assets")
    os.makedirs(assets_dir, exist_ok=True)

    # 1) Get HTML
    headers = {"User-Agent": "Mozilla/5.0 (compatible; URL-to-HTML-CSS/1.0)"}
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    html = r.text

    soup = BeautifulSoup(html, "html.parser")

    # 2) Find external stylesheets
    for link in soup.find_all("link", rel=lambda v: v and "stylesheet" in v.lower()):
        href = link.get("href")
        if not href:
            continue
        abs_url = urljoin(url, href)
        try:
            css_resp = requests.get(abs_url, headers=headers, timeout=30)
            css_resp.raise_for_status()
        except Exception as e:
            print(f"[warn] could not download {abs_url}: {e}")
            continue

        fname = safe_name(abs_url)
        local_path = os.path.join(assets_dir, fname)
        with open(local_path, "wb") as f:
            f.write(css_resp.content)

        # rewrite href -> local path
        link["href"] = f"assets/{fname}"

    # 3) Optional: strip query strings from other asset links in HTML (keeps HTML cleaner)
    # (Not required for CSS-only extraction; comment out if you don’t want this)
    for tag in soup.find_all(src=True):
        tag["src"] = urljoin(url, tag["src"])

    # 4) Save rewritten HTML
    out_html = os.path.join(outdir, "page.html")
    with open(out_html, "w", encoding="utf-8") as f:
        f.write(str(soup))

    print(f"Saved HTML -> {out_html}")
    print(f"Saved CSS  -> {assets_dir}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fetch_html_css.py <URL> [output_dir]")
        sys.exit(1)
    url = sys.argv[1]
    outdir = sys.argv[2] if len(sys.argv) > 2 else "output"
    fetch(url, outdir)
