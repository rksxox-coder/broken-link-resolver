import requests

def find_alternative_url(url):
    """
    Step 1: Check if URL works.
    Step 2: If broken, check parent folder.
    """

    if is_working(url):
        return url

    # Try parent directory
    parts = url.rstrip("/").split("/")
    if len(parts) > 3:
        parent = "/".join(parts[:-1]) + "/"
        if is_working(parent):
            return parent

    return "No alternative found"

def is_working(url):
    try:
        r = requests.get(url, timeout=4)
        return r.status_code == 200
    except:
        return False
