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
