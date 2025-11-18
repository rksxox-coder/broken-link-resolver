import csv
from .crawler import find_alternative_url

def process_single_url(url):
    return {
        "input": url,
        "alternative": find_alternative_url(url)
    }

def process_bulk_file(file):
    results = []
    if not file:
        return []

    lines = file.stream.read().decode("utf-8").splitlines()
    reader = csv.reader(lines)

    for row in reader:
        if row:
            url = row[0]
            results.append({
                "input": url,
                "alternative": find_alternative_url(url)
            })

    return results
