"""Local HTTP adapter for the unchanged practice_04 Registry."""

import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import re
import socket
from urllib.parse import parse_qsl, parse_qs, urlsplit

from view import render_page

REGISTRY_PATH = Path(__file__).resolve().parents[2] / "practice_04" / "lab" / "registry.py"
_spec = spec_from_file_location("practice04_registry", REGISTRY_PATH)
_module = module_from_spec(_spec)
_spec.loader.exec_module(_module)
Registry = _module.Registry

MAX_BODY = 4096
MESSAGES = {
    "added": "Подписчик добавлен",
    "duplicate": "Уже подписан",
    "removed": "Подписчик удалён",
    "missing": "Подписчик не найден",
}


class FormError(Exception):
    """Rejected transport input; Registry has not been called."""

    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


class RegistryServer(HTTPServer):
    """One server owns one independent in-memory registry, handled sequentially."""

    def __init__(self, port):
        self.registry = Registry()
        super().__init__(("127.0.0.1", port), RegistryHandler)


class RegistryHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        """Keep subscriber names out of request logs; demo prints its own summary."""

    def send_page(self, status=200, *, message="", error="", name=""):
        body = render_page(self.server.registry.names(), message, error, name).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        target = urlsplit(self.path)
        if target.path != "/":
            self.send_page(404, error="Страница не найдена")
            return
        try:
            result = parse_qs(target.query, max_num_fields=16).get("result", [""])[0]
        except ValueError:
            result = ""
        self.send_page(message=MESSAGES.get(result, ""))

    def read_name(self):
        lengths = self.headers.get_all("Content-Length", [])
        if (len(lengths) != 1 or not lengths[0].isascii()
                or not lengths[0].isdecimal() or self.headers.get("Transfer-Encoding")):
            raise FormError(400, "Некорректная длина запроса")
        # Compare as strings before int() to also handle excessively long headers.
        length_text = lengths[0].lstrip("0") or "0"
        if len(length_text) > 4 or int(length_text) > MAX_BODY:
            raise FormError(413, "Запрос превышает 4096 байт")
        length = int(length_text)
        if (len(self.headers.get_all("Content-Type", [])) != 1
                or self.headers.get_content_type() != "application/x-www-form-urlencoded"
                or self.headers.get_content_charset("utf-8") != "utf-8"):
            raise FormError(415, "Нужна форма в кодировке UTF-8")
        self.connection.settimeout(3)
        try:
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise ValueError("incomplete body")
            text = raw.decode("utf-8", errors="strict")
            if re.search(r"%(?![0-9a-fA-F]{2})", text):
                raise ValueError("invalid percent encoding")
            fields = parse_qsl(text, keep_blank_values=True, strict_parsing=True,
                               encoding="utf-8", errors="strict", max_num_fields=2)
            if len(fields) != 1 or fields[0][0] != "name":
                raise ValueError("expected exactly one name")
        except (ValueError, TimeoutError) as exc:
            raise FormError(400, "Некорректная форма: передайте одно поле имени") from exc
        return fields[0][1]

    def do_POST(self):
        action = urlsplit(self.path).path
        if action not in ("/subscribe", "/unsubscribe"):
            self.send_page(404, error="Страница не найдена")
            self.finish_rejected_request()
            return
        try:
            name = self.read_name()
        except FormError as exc:
            self.send_page(exc.status, error=str(exc))
            self.finish_rejected_request()
            return
        operation = (self.server.registry.subscribe if action == "/subscribe"
                     else self.server.registry.unsubscribe)
        try:
            changed = operation(name)
        except ValueError:
            error = ("Введите непустое имя" if not name.strip()
                     else "Имя не должно превышать 80 символов")
            self.send_page(400, error=error, name=name)
            return
        if action == "/subscribe":
            result = "added" if changed else "duplicate"
        else:
            result = "removed" if changed else "missing"
        self.send_response(303)
        self.send_header("Location", f"/?result={result}")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def finish_rejected_request(self):
        """Deliver an early error before closing a socket with unread form bytes.

        Windows may reset a connection closed with unread input. Half-close the
        response first, then discard only a bounded amount of already arriving
        data. Rejected bodies are never parsed or passed to Registry.
        """
        self.close_connection = True
        self.wfile.flush()
        try:
            self.connection.shutdown(socket.SHUT_WR)
            self.connection.settimeout(0.05)
            remaining = 65536
            while remaining:
                chunk = self.connection.recv(min(8192, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
        except OSError:
            pass  # A peer that has already closed needs no further draining.


def create_server(port=8765):
    """Create a loopback-only server. Use port=0 for an OS-selected test port."""
    return RegistryServer(port)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    with create_server(args.port) as server:
        print(f"Registry: http://127.0.0.1:{server.server_port}/", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")


if __name__ == "__main__":
    main()
