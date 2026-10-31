"""Hàm serverless Vercel: /api/meta (GET). Toàn bộ xử lý nằm ở chem_vision/web.py."""
import os
import sys
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from chem_vision.web import serve  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        serve(self, "meta")

    def do_POST(self):
        serve(self, "meta")           # trả 405 đúng định dạng JSON

    def log_message(self, *args):   # không ghi nội dung yêu cầu vào nhật ký
        pass
