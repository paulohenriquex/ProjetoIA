import http.server
import socketserver
import urllib.error
import urllib.request
from pathlib import Path

PORT = 6500
BACKEND = "http://127.0.0.1:8080"
DIR = Path(__file__).resolve().parent / "dist"


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIR), **kwargs)

    def _proxy(self):
        url = f"{BACKEND}{self.path}"
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else None

        req = urllib.request.Request(url, data=body, method=self.command)
        for key, val in self.headers.items():
            if key.lower() not in ("host", "content-length"):
                req.add_header(key, val)

        try:
            with urllib.request.urlopen(req, timeout=600) as resp:
                self.send_response(resp.status)
                for key, val in resp.headers.items():
                    if key.lower() not in ("transfer-encoding", "connection"):
                        self.send_header(key, val)
                self.end_headers()
                self.wfile.write(resp.read())
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            self.end_headers()
            self.wfile.write(e.read())
        except Exception:
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"detail":"Backend offline na porta 8080"}')

    def do_GET(self):
        if self.path.startswith("/api/"):
            self._proxy()
            return

        file_path = DIR / self.path.lstrip("/").split("?")[0]
        if not file_path.is_file():
            self.path = "/index.html"
        super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/"):
            self._proxy()
        else:
            self.send_error(404)

    def end_headers(self):
        if not self.path.startswith("/api/"):
            self.send_header("Cache-Control", "no-store")
        super().end_headers()


if __name__ == "__main__":
    if not DIR.is_dir():
        raise SystemExit(
            "Pasta dist/ não encontrada. Execute 'npm run build' na pasta frontend antes de iniciar."
        )
    with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
        print(f"Frontend rodando em http://localhost:{PORT}")
        print(f"Proxy API -> {BACKEND}")
        httpd.serve_forever()
