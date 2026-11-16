"""Hàm serverless Vercel duy nhất: /api/<tên> được vercel.json viết lại thành /api/index?route=<tên>.
Toàn bộ xử lý nằm ở chem_vision/web.py."""
import os
import sys
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from chem_vision.web import ROUTES, serve  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def _go(self):
        route = (parse_qs(urlparse(self.path).query).get("route") or [""])[0]
        if route not in ROUTES:
            body = b'{"ok": false, "error": "Kh\xc3\xb4ng c\xc3\xb3 \xc4\x91\xe1\xbb\x8bch n\xc3\xa0y."}'
            self.send_response(404)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        serve(self, route)

    do_GET = do_POST = _go

    def log_message(self, *args):   # không ghi nội dung yêu cầu vào nhật ký
        pass
