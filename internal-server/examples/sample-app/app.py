"""Tiny HTTP server used to demo the local Docker Compose deploy flow."""

import os
from http.server import BaseHTTPRequestHandler, HTTPServer


GREETING = os.environ.get("GREETING", "Hello from the DevOps agent!")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 - stdlib signature
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(GREETING.encode("utf-8") + b"\n")


def main() -> None:
    port = int(os.environ.get("PORT", "8000"))
    server = HTTPServer(("0.0.0.0", port), Handler)
    print(f"sample-app listening on 0.0.0.0:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
