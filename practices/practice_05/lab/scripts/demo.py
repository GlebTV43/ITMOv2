"""Short repeatable HTTP demo; starts and stops its own empty server."""

from http.client import HTTPConnection
from pathlib import Path
import sys
from threading import Thread
from urllib.parse import urlencode

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from web import create_server


def main():
    server = create_server(port=0)
    worker = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    worker.start()
    output = []

    def request(method, path="/", name=None):
        connection = HTTPConnection(*server.server_address, timeout=4)
        body = None if name is None else urlencode({"name": name}).encode()
        headers = {} if body is None else {"Content-Type": "application/x-www-form-urlencoded"}
        try:
            connection.request(method, path, body, headers)
            response = connection.getresponse()
            return response.status, response.getheader("Location"), response.read().decode("utf-8")
        finally:
            connection.close()

    def step(label, actual, expected):
        if actual != expected:
            raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")
        output.append(f"PASS | {label}")

    try:
        step("GET /: пустой список", "Пока нет подписчиков" in request("GET")[2], True)
        step("Подписка '  Анна  ': 303 added", request("POST", "/subscribe", "  Анна  ")[:2],
             (303, "/?result=added"))
        step("В Registry хранится нормализованное имя", server.registry.names(), ["Анна"])
        step("Дубль: 303 duplicate", request("POST", "/subscribe", "Анна")[:2],
             (303, "/?result=duplicate"))
        step("Пустое имя: 400", request("POST", "/subscribe", "   ")[0], 400)
        step("81 Unicode-символ: 400", request("POST", "/subscribe", "я" * 81)[0], 400)
        step("После ошибок список сохранён", server.registry.names(), ["Анна"])
        step("80 Unicode-символов: 303", request("POST", "/subscribe", "я" * 80)[0], 303)
        step("Отписка граничного имени: 303", request("POST", "/unsubscribe", "я" * 80)[0], 303)
        step("Отписка Анны: 303 removed", request("POST", "/unsubscribe", "Анна")[:2],
             (303, "/?result=removed"))
        step("Повторная отписка: 303 missing", request("POST", "/unsubscribe", "Анна")[:2],
             (303, "/?result=missing"))
        step("Финальный список пуст", "Пока нет подписчиков" in request("GET")[2], True)
        output.append("Demo: PASS (12 checks)")
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=3)
    results = Path(__file__).resolve().parents[2] / "results"
    results.mkdir(exist_ok=True)
    (results / "demo.txt").write_text("\n".join(output) + "\n", encoding="utf-8")
    print("\n".join(output))


if __name__ == "__main__":
    main()
