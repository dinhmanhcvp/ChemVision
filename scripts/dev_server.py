"""Máy chủ thử cục bộ giống Vercel: phục vụ public/ và chuyển /api/<tên> vào đúng hàm trong api/.

Chạy: python scripts/dev_server.py [cổng]   (đọc GEMINI_API_KEY, ACCESS_CODE từ môi trường hoặc chem_vision/.env)
"""
import importlib
import json
import mimetypes
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
PUBLIC = os.path.join(ROOT, "public")
ROUTES = {"meta", "analyze", "hint", "report", "equation", "classroom"}


def load_env():
    path = os.path.join(ROOT, "chem_vision", ".env")
    if os.path.exists(path):
        for line in open(path, encoding="utf-8-sig"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                if v.strip() and k.strip() not in os.environ:
                    os.environ[k.strip()] = v.strip().strip("\"'")


def security_headers() -> dict:
    cfg = json.load(open(os.path.join(ROOT, "vercel.json"), encoding="utf-8"))
    return {h["key"]: h["value"] for rule in cfg.get("headers", []) for h in rule["headers"]}


class Dev(BaseHTTPRequestHandler):
    def _api(self, route):
        mod = importlib.import_module(f"api.{route}")
        getattr(mod.handler, "do_" + self.command)(self)

    def _e2e(self):
        """Chỉ khi đặt E2E=1: phục vụ kịch bản kiểm thử giao diện để nạp vào trang (xem scripts/e2e_browser.js)."""
        data = open(os.path.join(ROOT, "scripts", "e2e_browser.js"), "rb").read()
        self.send_response(200)
        self.send_header("Content-Type", "text/javascript; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _static(self):
        if self.path.split("?")[0] == "/__e2e.js" and os.environ.get("E2E") == "1":
            return self._e2e()
        rel = self.path.split("?")[0].lstrip("/") or "index.html"
        full = os.path.normpath(os.path.join(PUBLIC, rel))
        if not full.startswith(PUBLIC + os.sep) or not os.path.isfile(full):
            self.send_error(404)
            return
        data = open(full, "rb").read()
        self.send_response(200)
        self.send_header("Content-Type", (mimetypes.guess_type(full)[0] or "application/octet-stream") + ("; charset=utf-8" if full.endswith((".html", ".js", ".css")) else ""))
        self.send_header("Content-Length", str(len(data)))
        for k, v in security_headers().items():      # cùng các header như khi chạy trên Vercel
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def _dispatch(self):
        path = self.path.split("?")[0]
        if path.startswith("/api/"):
            route = path[5:]
            if route in ROUTES:
                return self._api(route)
            return self.send_error(404)
        self._static()

    do_GET = do_POST = _dispatch

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    load_env()
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
    print(f"http://localhost:{port}  (GEMINI_API_KEY: {'có' if os.environ.get('GEMINI_API_KEY') else 'chưa'}, "
          f"ACCESS_CODE: {'có' if os.environ.get('ACCESS_CODE') else 'chưa'})")
    ThreadingHTTPServer(("127.0.0.1", port), Dev).serve_forever()
