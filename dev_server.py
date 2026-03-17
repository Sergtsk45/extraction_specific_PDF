#!/usr/bin/env python3
"""
@file: dev_server.py
@description: Dev-сервер для локальной разработки Shell + прокси к микросервисам.
  Раздаёт статику из корня проекта, проксирует:
  • /api/spec-converter/* → localhost:5001/*
  • /api/invoice-extractor/* → localhost:5002/*
@dependencies: Python 3.10+ stdlib
@created: 2026-03-01
"""

import http.server
import os
import socketserver
import urllib.request
import urllib.error
import sys
from pathlib import Path

_ROOT = Path(__file__).parent

# Load root .env if present (python-dotenv optional dep — fall back to os.getenv)
try:
    from dotenv import load_dotenv
    load_dotenv(_ROOT / ".env")
except ImportError:
    pass

PORT = int(os.getenv("SHELL_PORT", "8080"))
SPEC_CONVERTER_PREFIX = "/api/spec-converter"
SPEC_CONVERTER_BACKEND = "http://127.0.0.1:" + os.getenv("SPEC_CONVERTER_PORT", "5001")
INVOICE_EXTRACTOR_PREFIX = "/api/invoice-extractor"
INVOICE_EXTRACTOR_BACKEND = "http://127.0.0.1:" + os.getenv("INVOICE_EXTRACTOR_PORT", "5002")
ROOT = _ROOT


class DevHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        if self.path.startswith(SPEC_CONVERTER_PREFIX):
            self._proxy_request("GET", SPEC_CONVERTER_PREFIX, SPEC_CONVERTER_BACKEND)
        elif self.path.startswith(INVOICE_EXTRACTOR_PREFIX):
            self._proxy_request("GET", INVOICE_EXTRACTOR_PREFIX, INVOICE_EXTRACTOR_BACKEND)
        else:
            self._serve_static()

    def do_POST(self):
        if self.path.startswith(SPEC_CONVERTER_PREFIX):
            self._proxy_request("POST", SPEC_CONVERTER_PREFIX, SPEC_CONVERTER_BACKEND)
        elif self.path.startswith(INVOICE_EXTRACTOR_PREFIX):
            self._proxy_request("POST", INVOICE_EXTRACTOR_PREFIX, INVOICE_EXTRACTOR_BACKEND)
        else:
            self.send_error(405, "Method Not Allowed")

    def _proxy_request(self, method: str, api_prefix: str, backend_url: str):
        backend_path = self.path[len(api_prefix) :] or "/"
        url = f"{backend_url}{backend_path}"
        try:
            if method == "GET":
                req = urllib.request.Request(url, method="GET")
            else:
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length) if content_length else None
                req = urllib.request.Request(url, data=body, method="POST")
                for h in ("Content-Type", "Content-Length"):
                    if self.headers.get(h):
                        req.add_header(h, self.headers[h])
            with urllib.request.urlopen(req, timeout=60) as resp:
                self.send_response(resp.status)
                for k, v in resp.headers.items():
                    if k.lower() not in ("transfer-encoding",):
                        self.send_header(k, v)
                self.end_headers()
                self.wfile.write(resp.read())
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            self.end_headers()
            try:
                self.wfile.write(e.read())
            except Exception:
                pass
        except Exception as e:
            print(f"[proxy] {e}", file=sys.stderr)
            self.send_error(502, f"Backend unreachable: {e}")

    def _serve_static(self):
        # / → редирект на /shell/index.html (чтобы относительные пути css/js работали)
        path = self.path
        if path in ("/", ""):
            self.send_response(302)
            self.send_header("Location", "/shell/index.html")
            self.end_headers()
            return
        self.path = path
        return super().do_GET()


def main():
    print(f"\n{'='*60}")
    print(f"  [DEV] DocPlatform Dev Server — только для разработки!")
    print(f"  Для production используйте Nginx: gateway/nginx.conf")
    print(f"{'='*60}")
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), DevHandler) as httpd:
        print(f"  Dev Server запущен: http://localhost:{PORT}")
        print(f"  Прокси:")
        print(f"    • {SPEC_CONVERTER_PREFIX} → {SPEC_CONVERTER_BACKEND}")
        print(f"    • {INVOICE_EXTRACTOR_PREFIX} → {INVOICE_EXTRACTOR_BACKEND}")
        print(f"  Убедитесь, что Flask-сервисы запущены:")
        print(f"    • spec-converter: cd services/spec-converterv2/backend && python app.py")
        print(f"    • invoice-extractor: cd services/invoice-extractor/backend && python app.py")
        print(f"{'='*60}\n")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
