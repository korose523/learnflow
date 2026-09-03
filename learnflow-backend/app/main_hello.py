"""LearnFlow 最简版 —— 纯 Python 标准库 HTTP 服务器
用于测试 CloudBase 部署管道是否工作

用法: python app/main_hello.py
环境变量: PORT (默认 8000)
"""
import os
import json
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse


class HealthHandler(BaseHTTPRequestHandler):
    """极简 HTTP 处理器"""

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/health":
            self._json_response(200, {
                "status": "healthy",
                "version": "1.0.0-hello",
                "environment": os.getenv("ENVIRONMENT", "production"),
                "message": "LearnFlow pipeline OK!"
            })
        elif path == "/":
            self._json_response(200, {
                "app": "LearnFlow",
                "version": "1.0.0-hello",
                "docs": "N/A (minimal version)"
            })
        else:
            self._json_response(404, {"error": "not found"})

    def _json_response(self, status, data):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def log_message(self, format, *args):
        """打印到 stdout（CloudBase 会收集）"""
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {args[0]}")


if __name__ == "__main__":
    port = int(os.getenv("PORT", "80"))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] LearnFlow Hello Server running on 0.0.0.0:{port}")
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Health check: http://0.0.0.0:{port}/health")
    server.serve_forever()
