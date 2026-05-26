"""Serveur web local : API JSON + service des fichiers statiques.

Repose uniquement sur la bibliotheque standard (http.server). Lancer via
``python -m backlink_assistant``.
"""

from __future__ import annotations

import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import catalog, db, listing
from .analyze import AnalyzeError, analyze_url

WEB_DIR = Path(__file__).parent / "web"
STATIC_TYPES = {".html": "text/html", ".js": "text/javascript", ".css": "text/css"}


class ApiError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def _opportunities(conn, site: dict) -> list[dict]:
    keywords = catalog.normalize_keywords(site.get("keywords", ""))
    matches = catalog.match_directories(keywords, country=site.get("country", "FR"))
    statuses = db.submissions_by_slug(conn, site["id"])
    for m in matches:
        sub = statuses.get(m["slug"])
        m["status"] = sub["status"] if sub else "todo"
        m["submitted_at"] = sub["submitted_at"] if sub else ""
        m["submission_notes"] = sub["notes"] if sub else ""
    return matches


class Handler(BaseHTTPRequestHandler):
    db_path = db.DEFAULT_DB
    server_version = "BacklinkAssistant/0.1"

    # -- helpers -----------------------------------------------------------
    def _json(self, status: int, payload) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0) or 0)
        if not length:
            return {}
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            raise ApiError(400, f"Corps JSON invalide : {exc}")
        if not isinstance(data, dict):
            raise ApiError(400, "Le corps de la requete doit etre un objet JSON.")
        return data

    def _serve_static(self, path: str) -> None:
        name = "index.html" if path == "/" else path.lstrip("/")
        target = (WEB_DIR / name).resolve()
        if WEB_DIR.resolve() not in target.parents or not target.is_file():
            self._json(404, {"error": "Fichier introuvable."})
            return
        ctype = STATIC_TYPES.get(target.suffix, "application/octet-stream")
        data = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", f"{ctype}; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):  # quieter logs
        return

    # -- dispatch ----------------------------------------------------------
    def do_GET(self):
        parsed = urlparse(self.path)
        path, query = parsed.path, parse_qs(parsed.query)
        try:
            if not path.startswith("/api/"):
                return self._serve_static(path)
            with db.connect(self.db_path) as conn:
                db.init_db(conn)
                self._route_get(conn, path, query)
        except ApiError as exc:
            self._json(exc.status, {"error": exc.message})
        except Exception as exc:  # pragma: no cover
            self._json(500, {"error": str(exc)})

    def do_POST(self):
        self._with_body("POST")

    def do_PUT(self):
        self._with_body("PUT")

    def do_DELETE(self):
        parsed = urlparse(self.path)
        try:
            with db.connect(self.db_path) as conn:
                db.init_db(conn)
                self._route_delete(conn, parsed.path)
        except ApiError as exc:
            self._json(exc.status, {"error": exc.message})
        except Exception as exc:  # pragma: no cover
            self._json(500, {"error": str(exc)})

    def _with_body(self, method: str):
        parsed = urlparse(self.path)
        try:
            body = self._read_body()
            with db.connect(self.db_path) as conn:
                db.init_db(conn)
                if method == "POST":
                    self._route_post(conn, parsed.path, body)
                else:
                    self._route_put(conn, parsed.path, body)
        except ApiError as exc:
            self._json(exc.status, {"error": exc.message})
        except ValueError as exc:
            self._json(400, {"error": str(exc)})
        except Exception as exc:  # pragma: no cover
            self._json(500, {"error": str(exc)})

    # -- routes ------------------------------------------------------------
    def _site_or_404(self, conn, site_id: int) -> dict:
        site = db.get_site(conn, site_id)
        if not site:
            raise ApiError(404, f"Site #{site_id} introuvable.")
        return site

    def _route_get(self, conn, path: str, query: dict):
        if path == "/api/catalog":
            return self._json(200, {"directories": catalog.DIRECTORIES})
        if path == "/api/sites":
            return self._json(200, {"sites": db.list_sites(conn)})
        if m := re.fullmatch(r"/api/sites/(\d+)", path):
            return self._json(200, self._site_or_404(conn, int(m[1])))
        if m := re.fullmatch(r"/api/sites/(\d+)/opportunities", path):
            site = self._site_or_404(conn, int(m[1]))
            return self._json(200, {"opportunities": _opportunities(conn, site)})
        if m := re.fullmatch(r"/api/sites/(\d+)/submissions", path):
            self._site_or_404(conn, int(m[1]))
            return self._json(200, {"submissions": db.list_submissions(conn, int(m[1]))})
        if m := re.fullmatch(r"/api/sites/(\d+)/today", path):
            site = self._site_or_404(conn, int(m[1]))
            pending = [o for o in _opportunities(conn, site) if o["status"] == "todo"]
            return self._json(200, {"suggestion": pending[0] if pending else None})
        if m := re.fullmatch(r"/api/sites/(\d+)/listing", path):
            site = self._site_or_404(conn, int(m[1]))
            slug = (query.get("slug") or [""])[0]
            directory = catalog.get_directory(slug)
            if not directory:
                raise ApiError(404, f"Annuaire inconnu : {slug!r}.")
            return self._json(200, listing.generate_listing(site, directory))
        raise ApiError(404, "Route inconnue.")

    def _route_post(self, conn, path: str, body: dict):
        if path == "/api/sites":
            site_id = db.add_site(conn, **body)
            return self._json(201, db.get_site(conn, site_id))
        if path == "/api/analyze":
            url = (body.get("url") or "").strip()
            if not url:
                raise ApiError(400, "URL manquante.")
            try:
                return self._json(200, analyze_url(url))
            except AnalyzeError as exc:
                raise ApiError(502, str(exc))
        if path == "/api/submissions":
            site_id = int(body.get("site_id", 0))
            slug = (body.get("directory_slug") or "").strip()
            self._site_or_404(conn, site_id)
            if not catalog.get_directory(slug):
                raise ApiError(404, f"Annuaire inconnu : {slug!r}.")
            result = db.set_submission(
                conn, site_id, slug,
                status=body.get("status", "todo"),
                notes=body.get("notes"),
            )
            return self._json(200, result)
        raise ApiError(404, "Route inconnue.")

    def _route_put(self, conn, path: str, body: dict):
        if m := re.fullmatch(r"/api/sites/(\d+)", path):
            site_id = int(m[1])
            self._site_or_404(conn, site_id)
            db.update_site(conn, site_id, **body)
            return self._json(200, db.get_site(conn, site_id))
        raise ApiError(404, "Route inconnue.")

    def _route_delete(self, conn, path: str):
        if m := re.fullmatch(r"/api/sites/(\d+)", path):
            site_id = int(m[1])
            if not db.delete_site(conn, site_id):
                raise ApiError(404, f"Site #{site_id} introuvable.")
            return self._json(200, {"deleted": site_id})
        raise ApiError(404, "Route inconnue.")


def run(host: str = "127.0.0.1", port: int = 8000, db_path: str = db.DEFAULT_DB) -> None:
    Handler.db_path = db_path
    with db.connect(db_path) as conn:
        db.init_db(conn)
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"Assistant de backlinks en ligne : http://{host}:{port}")
    print(f"Base de donnees : {db_path}")
    print("Ctrl+C pour arreter.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nArret.")
    finally:
        httpd.server_close()
