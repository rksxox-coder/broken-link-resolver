# Broken Link Resolver

**Broken Link Resolver** checks URLs (single or bulk) and suggests the closest working alternative when pages are moved or removed.  
Built with Python + Flask. Frontend uses Tailwind CDN for a clean, responsive UI. Deployed on Render.

---

## Features
- Single URL check (via web UI or `/api/find?url=...`)
- Bulk CSV / TXT / XLSX upload (via web UI or `/api/bulk`)
- Smart alternative detection:
  - try simple variants (https / www / trailing slash)
  - parent-path fallback
  - homepage crawl + fuzzy matching
  - canonical / meta-refresh detection
- Downloadable CSV export of results
- Lightweight, zero-database architecture (stateless)

---

## Endpoints

- `GET /` — UI homepage  
- `POST /check` — checks a single URL (form)  
- `POST /upload` — upload CSV/TXT/XLSX (form)  
- `GET /api/find?url=<url>` — JSON API for single URL  
- `POST /api/bulk` — JSON or file-based bulk processing (file upload)  
- `POST /download` — download processed results as CSV (form)  
- `GET /healthz` — health check (200 OK)

---

## Run locally (optional)
If you can run Python locally:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
