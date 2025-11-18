import aiohttp
import asyncio
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from difflib import SequenceMatcher
import re

# ============================================================================
# 0. CONFIG
# ============================================================================
DEFAULT_TIMEOUT = 12
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


# ============================================================================
# 1. BASIC CHECK FUNCTIONS
# ============================================================================

async def check_status(url):
    """
    Returns HTTP status code or None if unreachable.
    """
    try:
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.get(url, timeout=DEFAULT_TIMEOUT, allow_redirects=True) as resp:
                return resp.status
    except Exception:
        return None


async def fetch_html(url):
    """
    Fetch raw HTML for scraping.
    Returns string or None.
    """
    try:
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.get(url, timeout=DEFAULT_TIMEOUT) as response:
                if response.status < 400:
                    return await response.text()
                return None
    except Exception:
        return None


async def fetch_head(url):
    """
    Sends HEAD request to detect faster dead links.
    """
    try:
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.head(url, timeout=DEFAULT_TIMEOUT, allow_redirects=True) as response:
                return response.status
    except:
        return None


# ============================================================================
# 2. SMART HTML PARSING ENGINE
# ============================================================================

def extract_internal_links(base_url, soup):
    """
    Extracts internal links belonging to same domain.
    Returns list of URLs.
    """
    base_domain = urlparse(base_url).netloc
    links = []

    for tag in soup.find_all("a", href=True):
        href = tag["href"]
        full_link = urljoin(base_url, href)

        if urlparse(full_link).netloc == base_domain:
            if full_link not in links:
                links.append(full_link)

    return links


def get_meta_refresh(soup, base_url):
    meta = soup.find("meta", attrs={"http-equiv": "refresh"})
    if not meta:
        return None

    content = meta.get("content", "")
    match = re.search(r'URL=(.+)', content, re.IGNORECASE)
    if match:
        return urljoin(base_url, match.group(1).strip())

    return None


def get_canonical(soup, base_url):
    canonical = soup.find("link", rel="canonical")
    if canonical and canonical.get("href"):
        return urljoin(base_url, canonical["href"].strip())
    return None


def detect_moved_text(soup, base_url):
    moved_patterns = [
        r"this page has moved",
        r"moved here",
        r"click here",
        r"new page",
        r"updated page",
        r"this page is now available",
    ]

    for pattern in moved_patterns:
        text = soup.find(string=re.compile(pattern, re.IGNORECASE))
        if text:
            parent_a = text.parent.find("a")
            if parent_a and parent_a.get("href"):
                return urljoin(base_url, parent_a["href"])
    return None


# ============================================================================
# 3. FUZZY LOGIC MATCHING FOR BEST ALTERNATIVE
# ============================================================================

def score_similarity(original_url, target_url):
    """
    Computes fuzzy similarity score between URLs.
    Also adds bonuses for keywords indicating new/updated content.
    """
    similarity = SequenceMatcher(None, original_url, target_url).ratio()

    keywords = [
        "latest", "update", "new", "2024", "2025", "news",
        "blog", "article", "post", "archive"
    ]

    keyword_bonus = sum(0.05 for kw in keywords if kw in target_url.lower())
    return similarity + keyword_bonus


def pick_best_match(original, candidates):
    if not candidates:
        return None

    scored = sorted(
        candidates,
        key=lambda c: score_similarity(original, c),
        reverse=True
    )

    best = scored[0]
    similarity = SequenceMatcher(None, original, best).ratio()

    # Only accept if similarity is reasonably close (0.25+)
    if similarity > 0.25:
        return best

    return None


# ============================================================================
# 4. MAIN ALTERNATIVE FINDER
# ============================================================================

async def find_alternative(url):
    """
    Extracts best alternative URL using:
    - Meta refresh
    - Canonical
    - "This page moved" text
    - Internal link scanning + fuzzy match
    """

    html = await fetch_html(url)
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")

    # (A) meta refresh
    meta_refresh = get_meta_refresh(soup, url)
    if meta_refresh:
        return meta_refresh

    # (B) canonical
    canonical = get_canonical(soup, url)
    if canonical:
        return canonical

    # (C) moved text
    moved = detect_moved_text(soup, url)
    if moved:
        return moved

    # (D) internal link mining → score → best candidate
    internal_links = extract_internal_links(url, soup)
    return pick_best_match(url, internal_links)


# ============================================================================
# 5. PROCESS A SINGLE URL (MAIN FUNCTION)
# ============================================================================

async def process_single_url(url):
    """
    Returns:
    {
        "url": original,
        "status": HTTP status or None,
        "alternative": working alternative or None,
        "final": final working URL (alt if original fails)
    }
    """

    # Quick HEAD check
    head_status = await fetch_head(url)

    if head_status and head_status < 400:
        return {
            "url": url,
            "status": head_status,
            "alternative": None,
            "final": url
        }

    # GET re-check
    get_status = await check_status(url)

    if get_status and get_status < 400:
        return {
            "url": url,
            "status": get_status,
            "alternative": None,
            "final": url
        }

    # If URL is dead → find alternative
    alt = await find_alternative(url)
    final_status = await check_status(alt) if alt else None

    return {
        "url": url,
        "status": get_status or head_status,
        "alternative": alt,
        "final": alt if final_status and final_status < 400 else None
    }


# ============================================================================
# 6. PROCESS MULTIPLE URLs (BULK SUPPORT)
# ============================================================================

async def process_bulk(urls):
    """
    Process multiple URLs concurrently using asyncio.gather.
    """
    tasks = [asyncio.create_task(process_single_url(u)) for u in urls]
    return await asyncio.gather(*tasks)
