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
