import requests
from bs4 import BeautifulSoup

def check_url_status(url):
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
        }

        response = requests.get(url, headers=headers, timeout=8)

        return {
            "status_code": response.status_code,
            "final_url": response.url,
            "is_working": response.status_code in [200, 301, 302],
            "error": None
        }

    except Exception as e:
        return {
            "status_code": None,
            "final_url": url,
            "is_working": False,
            "error": str(e)
        }

def process_single_url(url):
    """
    Main function used by both frontend + API.
    Checks if URL works, returns alternative if broken.
    """
    try:
        info = check_url_status(url)

        if info["is_working"]:
            return {
                "input": url,
                "working": True,
                "final_url": info["final_url"]
            }

        # URL is broken → try finding replacement
        alternative = find_alternative(url)

        return {
            "input": url,
            "working": False,
            "alternative": alternative,
            "error": info["error"]
        }

    except Exception as e:
        return {
            "input": url,
            "working": False,
            "error": str(e)
        }

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from difflib import SequenceMatcher

def similarity(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def find_alternative(url, timeout=6):
    """
    Try to find best alternative working link for a missing/dead URL.
    Uses title similarity, slug matching, anchor text, and structure heuristics.
    """
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"

    # Extract slug (last part of URL)
    slug = parsed.path.rstrip('/').split('/')[-1]

    candidates = []

    try:
        # Step 1: Crawl the homepage
        r = requests.get(base, timeout=timeout)
        if r.status_code != 200:
            return None  # website itself unreachable

        soup = BeautifulSoup(r.text, "html.parser")

        for link in soup.find_all("a", href=True):
            href = link["href"]
            abs_url = urljoin(base, href)

            # Skip external or irrelevant links
            if base not in abs_url:
                continue
            if abs_url == url:
                continue

            # Collect info for ranking
            anchor_text = link.get_text(strip=True)
            score = 0

            # 1. URL similarity check
            score += similarity(url, abs_url) * 3

            # 2. Slug similarity
            if slug:
                score += similarity(slug, abs_url) * 4

            # 3. Anchor text relevance
            if anchor_text:
                score += similarity(slug, anchor_text) * 2

            candidates.append((score, abs_url))

    except Exception:
        return None

    if not candidates:
        return None

    # Step 2: Sort by score
    candidates.sort(reverse=True, key=lambda x: x[0])

    # Step 3: Validate top 5 for actual 200 status pages
    for score, link in candidates[:5]:
        try:
            check = requests.get(link, timeout=timeout)
            if check.status_code == 200:
                return link
        except:
            continue

    return None

