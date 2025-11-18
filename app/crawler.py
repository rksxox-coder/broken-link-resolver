"""
Improved crawler for URL Alternative Finder (MVP+)

Features:
- checks URL via HEAD (fast) then GET (fallback)
- soft-404 detection via heuristics and content checks
- parse sitemap.xml for candidates
- extract internal links from HTML pages (limited depth & pages)
- parent-path heuristics
- polite throttling per-domain
- returns ranked candidate list (url + reason + score_estimate)
- lightweight: avoids heavy crawling and respects basic polite limits

Note: This is still an offline/simple crawler designed for free hosting.
For very large domains or deep crawling, add persistent queues and proxies.
"""

import time
import re
import requests
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup

# Config
HTTP_TIMEOUT = 6
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; LinkRecoverBot/1.0; +https://example.com)"
}
DOMAIN_THROTTLE_SECONDS = 0.5  # polite throttle per domain
MAX_CRAWL_PAGES = 10           # max pages to fetch per domain when searching alternatives
MAX_CANDIDATES = 12
SITEMAP_PATHS = ["/sitemap.xml", "/sitemap_index.xml"]
ROBOTS_TXT = "/robots.txt"

# domain -> last request timestamp
_domain_last_req = {}

# helper: throttle per domain
def _throttle(domain: str):
    now = time.time()
    last = _domain_last_req.get(domain, 0)
    wait = DOMAIN_THROTTLE_SECONDS - (now - last)
    if wait > 0:
        time.sleep(wait)
    _domain_last_req[domain] = time.time()

# normalize input URL
def normalize_url(url: str) -> str:
    if not url:
        return ""
    url = url.strip()
    if not re.match(r"^https?://", url, re.I):
        url = "http://" + url
    return url

# fast working check: HEAD then GET
def is_working(url: str) -> bool:
    try:
        parsed = urlparse(url)
        _throttle(parsed.netloc)
        # HEAD first (faster, doesn't download body)
        try:
            r = requests.head(url, headers=HEADERS, timeout=HTTP_TIMEOUT, allow_redirects=True)
            status = r.status_code
            if status and (200 <= status < 400):
                # do soft-404 content check for 200
                if status == 200:
                    # attempt a lightweight GET to confirm not a soft-404 (small GET)
                    _throttle(parsed.netloc)
                    g = requests.get(url, headers=HEADERS, timeout=HTTP_TIMEOUT, stream=True)
                    text = ""
                    try:
                        # read only a small chunk
                        text = g.text[:4000]
                    except Exception:
                        text = ""
                    if _is_soft_404(text):
                        return False
                return True
            elif status in (403, 401):
                # treat auth/forbidden as not "working" for our purposes, flag for manual review
                return False
        except requests.RequestException:
            # fallback to GET if HEAD fails
            _throttle(parsed.netloc)
            g = requests.get(url, headers=HEADERS, timeout=HTTP_TIMEOUT, allow_redirects=True)
            if g.status_code and (200 <= g.status_code < 400):
                if g.status_code == 200 and _is_soft_404(g.text):
                    return False
                return True
    except Exception:
        pass
    return False

# soft-404 detection
def _is_soft_404(html: str) -> bool:
    if not html:
        return False
    low = html.lower()
    indicators = [
        "page not found", "404 not found", "the page you requested could not be found",
        "does not exist", "not found on this server", "we could not find",
        "no results found", "sorry, we couldn't find", "requested url was not found"
    ]
    for sig in indicators:
        if sig in low:
            return True
    # very short or extremely repetitive content often indicates placeholder / soft-404
    text = re.sub(r"\s+", " ", BeautifulSoup(html, "html.parser").get_text()).strip()
    if len(text) < 60:
        return True
    return False

# fetch sitemap.xml and parse <loc> entries (simple)
def fetch_sitemap(domain: str) -> list:
    urls = []
    for path in SITEMAP_PATHS:
        sitemap_url = f"https://{domain.rstrip('/')}{path}"
        try:
            _throttle(domain)
            r = requests.get(sitemap_url, headers=HEADERS, timeout=HTTP_TIMEOUT)
            if r.status_code == 200 and r.text:
                matches = re.findall(r"<loc>(.*?)</loc>", r.text, flags=re.I | re.S)
                for m in matches:
                    m = m.strip()
                    if m:
                        urls.append(m)
                # if we found entries, return (prefer https sitemap)
                if urls:
                    return urls
        except Exception:
            pass
        # try http version as fallback
        try:
            sitemap_url = f"http://{domain.rstrip('/')}{path}"
            _throttle(domain)
            r = requests.get(sitemap_url, headers=HEADERS, timeout=HTTP_TIMEOUT)
            if r.status_code == 200 and r.text:
                matches = re.findall(r"<loc>(.*?)</loc>", r.text, flags=re.I | re.S)
                for m in matches:
                    m = m.strip()
                    if m:
                        urls.append(m)
                if urls:
                    return urls
        except Exception:
            pass
    return urls

# basic robots.txt check (very lightweight) -> returns False if disallowed for all
def is_allowed_by_robots(domain: str, path: str) -> bool:
    # this is a very small, permissive parser: if robots.txt contains "Disallow: /" for all agents, block
    try:
        robots_url = f"https://{domain.rstrip('/')}{ROBOTS_TXT}"
        _throttle(domain)
        r = requests.get(robots_url, headers=HEADERS, timeout=HTTP_TIMEOUT)
        if r.status_code == 200 and "disallow: /" in r.text.lower():
            # cautious: if disallow: / present, we avoid crawling
            return False
    except Exception:
        pass
    return True

# extract internal links from an HTML page (limit to same domain)
def extract_internal_links(base_url: str, html: str, domain: str) -> list:
    out = []
    if not html:
        return out
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a", href=True):
        href = a.get("href").strip()
        # ignore mailto, tel, javascript
        if href.startswith("mailto:") or href.startswith("tel:") or href.startswith("javascript:"):
            continue
        # make absolute
        try:
            abs_url = urljoin(base_url, href)
        except Exception:
            continue
        p = urlparse(abs_url)
        if not p.netloc:
            continue
        # same domain only
        if p.netloc == domain:
            out.append(abs_url.split('#')[0])  # remove fragment
    # dedupe preserving order
    deduped = []
    seen = set()
    for u in out:
        if u not in seen:
            seen.add(u)
            deduped.append(u)
    return deduped

# crawl a small number of pages on the domain to gather candidate URLs
def crawl_domain_for_candidates(start_url: str, max_pages: int = MAX_CRAWL_PAGES) -> list:
    """
    BFS-like crawl starting from start_url, limited to max_pages.
    Returns a list of internal URLs discovered (including start_url if valid).
    """
    parsed = urlparse(start_url)
    domain = parsed.netloc
    if not is_allowed_by_robots(domain, parsed.path):
        return []

    discovered = []
    queue = [start_url]
    visited = set()
    pages = 0

    while queue and pages < max_pages:
        url = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)
        try:
            _throttle(domain)
            r = requests.get(url, headers=HEADERS, timeout=HTTP_TIMEOUT)
            pages += 1
            if r.status_code == 200 and r.text and not _is_soft_404(r.text):
                discovered.append(url)
                links = extract_internal_links(url, r.text, domain)
                for l in links:
                    if l not in visited and l not in queue and len(queue) < max_pages * 3:
                        queue.append(l)
        except Exception:
            continue

    # return discovered (unique)
    return discovered

# parent-path heuristics
def parent_paths(url: str, max_levels: int = 3) -> list:
    parsed = urlparse(url)
    path = parsed.path
    parts = [p for p in path.split("/") if p]
    candidates = []
    for i in range(1, min(len(parts), max_levels) + 1):
        new_parts = parts[:-i]
        if not new_parts:
            new_path = "/"
        else:
            new_path = "/" + "/".join(new_parts) + "/"
        candidate = f"{parsed.scheme}://{parsed.netloc}{new_path}"
        candidates.append(candidate)
    return candidates

# simple heuristic scorer for candidates (title/snippet checks will be performed if page fetched)
def score_candidate(base_tokens: list, candidate_url: str, page_text: str = "") -> int:
    score = 0
    u_low = candidate_url.lower()
    for t in base_tokens:
        if t in u_low:
            score += 20
        if page_text and t in page_text.lower():
            score += 15
    # prefer directory-like pages
    if candidate_url.endswith("/"):
        score += 5
    # cap
    return min(100, score)

# main function: find_alternatives
def find_alternatives(original_url: str, max_candidates: int = MAX_CANDIDATES) -> list:
    """
    Return a list of candidate dicts:
    { 'url': ..., 'source': 'sitemap|crawl|parent|direct', 'score': int, 'reason': str }
    """
    orig = normalize_url(original_url)
    if not orig:
        return []

    parsed = urlparse(orig)
    domain = parsed.netloc

    candidates = []
    seen = set()

    # 1) if original works, return it immediately as top candidate
    try:
        if is_working(orig):
            candidates.append({'url': orig, 'source': 'original', 'score': 100, 'reason': 'original works'})
            return candidates
    except Exception:
        pass

    # base tokens for scoring: from path and query
    base_tokens = []
    path_parts = [p for p in parsed.path.split('/') if p]
    for p in path_parts[-3:]:
        for tok in re.split(r"[-_\\s]+", p):
            if tok and len(tok) > 1:
                base_tokens.append(tok.lower())
    # include host tokens
    host_parts = [x for x in re.split(r"[.-]+", domain) if x and len(x) > 1]
    base_tokens += host_parts[:2]
    base_tokens = list(dict.fromkeys(base_tokens))  # dedupe preserve order

    # 2) sitemap
    try:
        sm = fetch_sitemap(domain)
        for u in sm:
            if u not in seen:
                seen.add(u)
                # lightweight score using url only
                sc = score_candidate(base_tokens, u, "")
                candidates.append({'url': u, 'source': 'sitemap', 'score': sc, 'reason': 'from sitemap'})
                if len(candidates) >= max_candidates:
                    break
    except Exception:
        pass

    # 3) parent paths
    for u in parent_paths(orig, max_levels=3):
        if u not in seen:
            seen.add(u)
            sc = score_candidate(base_tokens, u, "")
            candidates.append({'url': u, 'source': 'parent', 'score': sc, 'reason': 'parent path heuristic'})

    # 4) crawl few internal pages near the original URL (BFS up to MAX_CRAWL_PAGES)
    try:
        crawled = crawl_domain_for_candidates(orig, max_pages=MAX_CRAWL_PAGES)
        for u in crawled:
            if u not in seen:
                # fetch small content to refine score
                page_text = ""
                try:
                    _throttle(domain)
                    r = requests.get(u, headers=HEADERS, timeout=HTTP_TIMEOUT)
                    if r.status_code == 200 and r.text and not _is_soft_404(r.text):
                        page_text = re.sub(r"\s+", " ", BeautifulSoup(r.text, "html.parser").get_text())[:2000]
                except Exception:
                    pass
                sc = score_candidate(base_tokens, u, page_text)
                candidates.append({'url': u, 'source': 'crawl', 'score': sc, 'reason': 'nearby internal page'})
                seen.add(u)
                if len(candidates) >= max_candidates:
                    break
    except Exception:
        pass

    # 5) fallback heuristics (simple slug variants)
    slug = path_parts[-1] if path_parts else ""
    if slug:
        heuristics = [f"{slug}-latest", f"{slug}-new", f"{slug}-updated", f"{slug}-1"]
        for h in heuristics:
            u = f"{parsed.scheme}://{domain}/{h}"
            if u not in seen:
                seen.add(u)
                sc = score_candidate(base_tokens, u, "")
                candidates.append({'url': u, 'source': 'heuristic', 'score': sc, 'reason': 'slug heuristic'})

    # dedupe and sort candidates by score desc
    candidates_sorted = sorted(candidates, key=lambda x: x.get('score', 0), reverse=True)

    # trim to max_candidates and return
    return candidates_sorted[:max_candidates]
