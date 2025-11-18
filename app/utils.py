import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import difflib

# ----------------------------------------------------
# User-Agent to avoid blocking by websites (BMW etc.)
# ----------------------------------------------------
HEADERS = {
    "User-Agent":
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}


# ----------------------------------------------------
# Safe GET with retry + timeout
# ----------------------------------------------------
def safe_get(url, timeout=12, retries=3):
    for attempt in range(retries):
        try:
            return requests.get(url, timeout=timeout, headers=HEADERS)
        except requests.exceptions.Timeout:
            if attempt == retries - 1:
                return None
            continue
        except Exception:
            return None
    return None


# ----------------------------------------------------
# Extract slug from a URL
# ex: https://site.com/a/b/c.html → c
# ----------------------------------------------------
def get_slug(url):
    path = urlparse(url).path
    if not path:
        return ""
    parts = [p for p in path.split("/") if p]
    if not parts:
        return ""
    slug = parts[-1].replace(".html", "").replace(".htm", "")
    return slug.lower()


# ----------------------------------------------------
# Find the best alternative link
# ----------------------------------------------------
def find_alternative(url):
    try:
        base = "{uri.scheme}://{uri.netloc}".format(uri=urlparse(url))

        # Fetch the homepage or directory page
        r = safe_get(base)
        if not r or r.status_code != 200:
            return None

        soup = BeautifulSoup(r.text, "html.parser")
        all_links = [a.get("href") for a in soup.find_all("a")]

        slug = get_slug(url)
        scored = []

        # Score links based on similarity
        for link in all_links:
            if not link:
                continue

            full = urljoin(base, link)
            if not full.startswith(base):
                continue  # ignore external links

            link_slug = get_slug(full)
            if not link_slug:
                continue

            # Slug similarity
            score = difflib.SequenceMatcher(None, slug, link_slug).ratio()
            if score > 0.30:  # lower threshold = more flexible
                scored.append((score, full))

        # Sort by best match
        scored.sort(reverse=True, key=lambda x: x[0])

        # Return best working link
        for _, link in scored:
            check = safe_get(link)
            if check and check.status_code == 200:
                return link

        return None

    except Exception as e:
        return None


# ----------------------------------------------------
# Process a single URL
# ----------------------------------------------------
def process_single_url(url):
    try:
        r = safe_get(url)

        # Case 1: URL works properly
        if r and r.status_code == 200:
            return {
                "input": url,
                "working": True,
                "status": r.status_code,
                "alternative": None,
                "error": None
            }

        # Case 2: URL broken – try finding alternative
        alt = find_alternative(url)

        return {
            "input": url,
            "working": False,
            "status": r.status_code if r else None,
            "alternative": alt,
            "error": None if r else "Request failed or timed out"
        }

    except Exception as e:
        return {
            "input": url,
            "working": False,
            "status": None,
            "alternative": None,
            "error": str(e)
        }


# ----------------------------------------------------
# Process bulk file (TXT with one URL per line)
# ----------------------------------------------------
def process_bulk_file(file):
    if not file:
        return []

    urls = file.read().decode().splitlines()
    results = []

    for url in urls:
        if url.strip():
            results.append(process_single_url(url.strip()))

    return results
