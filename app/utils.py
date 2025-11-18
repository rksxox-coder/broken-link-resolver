import requests
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from difflib import SequenceMatcher
import csv
import io
import pandas as pd

headers = {
    "User-Agent": "Mozilla/5.0"
}


# -----------------------------------------------------
# BASIC UTILITIES
# -----------------------------------------------------

def is_valid_url(url: str) -> bool:
    """Check if URL is well-formed."""
    try:
        parsed = urlparse(url)
        return bool(parsed.scheme) and bool(parsed.netloc)
    except:
        return False


def check_url_status(url: str) -> dict:
    """Return status code, final URL, and redirection info."""
    try:
        r = requests.get(url, timeout=6, allow_redirects=True, headers=headers)

        return {
            "input_url": url,
            "final_url": r.url,
            "status_code": r.status_code,
            "ok": (200 <= r.status_code < 400)
        }
    except Exception as e:
        return {
            "input_url": url,
            "final_url": None,
            "status_code": None,
            "ok": False
        }


# -----------------------------------------------------
# URL NORMALIZATION & VARIANTS
# -----------------------------------------------------

def normalize_url(url):
    """Fix www, https, remove query junk."""
    parsed = urlparse(url)

    scheme = "https"

    netloc = parsed.netloc
    if not netloc.startswith("www."):
        netloc = "www." + netloc

    clean_query = ""

    normalized = f"{scheme}://{netloc}{parsed.path}"
    return normalized


def try_simple_variants(url):
    """Generate multiple possible corrected versions of the input URL."""
    variants = set()
    parsed = urlparse(url)

    # Normalized
    variants.add(normalize_url(url))

    # Add/remove trailing slash
    if url.endswith("/"):
        variants.add(url.rstrip("/"))
    else:
        variants.add(url + "/")

    # Try http & https
    variants.add("http://" + parsed.netloc + parsed.path)
    variants.add("https://" + parsed.netloc + parsed.path)

    return list(variants)


def url_works(url):
    """Returns True if URL returns HTTP 200."""
    try:
        r = requests.get(url, timeout=5, allow_redirects=True, headers=headers)
        return r.status_code == 200
    except:
        return False


# -----------------------------------------------------
# PARENT PATH RECOVERY
# -----------------------------------------------------

def try_parent_paths(url):
    """Recover URL by decreasing the path depth."""
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")

    candidates = []

    # Example:
    # /blog/article/2020 → /blog/article → /blog → /
    while "/" in path:
        path = path[:path.rfind("/")]
        if not path:
            break
        candidate = f"https://{parsed.netloc}{path}/"
        candidates.append(candidate)

    # Try only domain
    candidates.append(f"https://{parsed.netloc}/")

    return candidates


# -----------------------------------------------------
# HOMEPAGE CRAWLING + FUZZY MATCHING
# -----------------------------------------------------

def crawl_homepage(url):
    """Fetch homepage links for fuzzy alternative detection."""
    parsed = urlparse(url)
    homepage = f"https://{parsed.netloc}/"

    try:
        r = requests.get(homepage, timeout=7, headers=headers)
        soup = BeautifulSoup(r.text, "html.parser")
        links = []

        for a in soup.find_all("a", href=True):
            link = urljoin(homepage, a["href"])
            links.append(link)

        return links
    except:
        return []


def fuzzy_best_match(broken_url, candidates):
    """Find best matching link from homepage."""
    broken_name = urlparse(broken_url).path.split("/")[-1]

    best = None
    best_score = 0

    for c in candidates:
        name = urlparse(c).path.split("/")[-1]
        score = SequenceMatcher(None, broken_name, name).ratio()

        if score > best_score:
            best = c
            best_score = score

    # Threshold to avoid random matches
    if best_score > 0.45:
        return best
    return None


# -----------------------------------------------------
# MAIN FUNCTION: FIND ALTERNATIVE LINK
# -----------------------------------------------------

def find_alternative(url):
    """
    Try to find a valid alternative for a dead/redirected URL.
    Steps:
    1. Simple variants (https, www, trailing slash)
    2. Parent path recovery
    3. Homepage crawl + fuzzy matching
    """

    # STEP 1: Try simple variants
    for u in try_simple_variants(url):
        if url_works(u):
            return u

    # STEP 2: Parent path fallback
    for u in try_parent_paths(url):
        if url_works(u):
            return u

    # STEP 3: Homepage crawl & fuzzy match
    homepage_links = crawl_homepage(url)
    if homepage_links:
        match = fuzzy_best_match(url, homepage_links)
        if match and url_works(match):
            return match

    # STOP HERE (as requested)
    return None


# -----------------------------------------------------
# PROCESS A SINGLE URL (used by your API)
# -----------------------------------------------------

def process_single_url(url: str):
    """
    Combined function used by your API:
    - check if URL works
    - if not, try to find alternative
    """
    if not is_valid_url(url):
        return {
            "url": url,
            "valid": False,
            "status": None,
            "final_url": None,
            "alternative": None
        }

    status = check_url_status(url)

    if status["ok"]:
        return {
            "url": url,
            "valid": True,
            "status": status["status_code"],
            "final_url": status["final_url"],
            "alternative": None
        }

    # URL broken → find alternative
    alternative = find_alternative(url)

    return {
        "url": url,
        "valid": False,
        "status": status["status_code"],
        "final_url": status["final_url"],
        "alternative": alternative
    }


def extract_urls_from_file(file):
    """Reads URLs from CSV or XLSX and returns a list."""
    filename = file.filename.lower()

    urls = []

    try:
        if filename.endswith(".csv"):
            stream = io.StringIO(file.stream.read().decode("utf-8"))
            reader = csv.reader(stream)
            for row in reader:
                if row:
                    urls.append(row[0].strip())

        elif filename.endswith(".xlsx"):
            df = pd.read_excel(file)
            first_col = df.columns[0]
            urls = df[first_col].dropna().astype(str).tolist()

    except Exception as e:
        print("File read error:", e)

    return urls


def process_bulk_file(file):
    """Processes CSV or XLSX and returns results list."""
    urls = extract_urls_from_file(file)
    results = []

    for url in urls:
        try:
            result = process_single_url(url)
            results.append(result)
        except Exception as e:
            results.append({
                "url": url,
                "valid": False,
                "status": None,
                "final_url": None,
                "alternative": None,
                "error": str(e)
            })

    return results
