"""
Utility functions for URL Alternative Finder

This version uses the improved crawler (find_alternatives)
and formats results for the Flask views to display.
"""

from .crawler import find_alternatives


def process_single_url(url: str) -> dict:
    """
    Takes a single URL and returns:
    - original_url
    - top_alternative (best candidate or None)
    - candidates (list with url, score, source, reason)
    - status: 'working', 'alternative-found', 'not-found', 'error'
    """

    try:
        candidates = find_alternatives(url)
        response = {
            "original_url": url,
            "top_alternative": None,
            "candidates": candidates,
            "status": ""
        }

        if not candidates:
            response["status"] = "not-found"
            return response

        # Top candidate is the one with highest score (already sorted)
        top = candidates[0]
        response["top_alternative"] = top["url"]

        # If top candidate is the same as original URL, it means original works
        if top["source"] == "original":
            response["status"] = "working"
        else:
            response["status"] = "alternative-found"

        return response

    except Exception as e:
        return {
            "original_url": url,
            "top_alternative": None,
            "candidates": [],
            "status": "error",
            "error": str(e)
        }


def process_multiple_urls(url_list: list) -> list:
    """
    Process a list of URLs and return structured results for each.
    """

    results = []
    for url in url_list:
        if url.strip():
            results.append(process_single_url(url.strip()))
    return results
