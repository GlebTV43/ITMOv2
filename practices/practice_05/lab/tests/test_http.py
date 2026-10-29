"""Public HTTP contract against a real loopback server, no third-party helpers."""

from html.parser import HTMLParser
from http.client import HTTPConnection
from pathlib import Path
import sys
from threading import Thread
import unittest
from urllib.parse import urlencode

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from web import create_server


class Page(HTMLParser):
    """Read the rendered forms and names as a browser would."""

    def __init__(self, body):
        super().__init__()
        self.forms = []
        self.names = []
        self.text = []
        self._name = False
        self.feed(body)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "form":
            self.forms.append({"action": attrs["action"], "fields": {}})
        if tag == "input" and attrs.get("name") and self.forms:
            self.forms[-1]["fields"][attrs["name"]] = attrs.get("value", "")
        if tag == "span" and attrs.get("class") == "subscriber-name":
            self._name = True

    def handle_endtag(self, tag):
        if tag == "span":
            self._name = False

    def handle_data(self, data):
        self.text.append(data)
        if self._name:
            self.names.append(data)


class TestHTTPContract(unittest.TestCase):
    def setUp(self):
        self.server = create_server(port=0)
        self.thread = Thread(
            target=self.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True
        )
        self.thread.start()
        self.addCleanup(self.stop_server)

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)

    def request(self, method="GET", path="/", body=None, headers=None):
        connection = HTTPConnection(*self.server.server_address, timeout=4)
        try:
            connection.request(method, path, body=body, headers=headers or {})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read().decode("utf-8")
        finally:
            connection.close()

    def post(self, name, path="/subscribe"):
        return self.request("POST", path, urlencode({"name": name}).encode(),
                            {"Content-Type": "application/x-www-form-urlencoded"})

    def page(self):
        status, headers, body = self.request()
        self.assertEqual(status, 200)
        self.assertIn("charset=utf-8", headers["Content-Type"])
        return Page(body)

    def test_empty_page_has_labelled_form_and_empty_state(self):
        _, _, body = self.request()
        self.assertIn("Пока нет подписчиков", body)
        self.assertIn('for="name"', body)
        self.assertIn('id="name"', body)
        self.assertEqual(self.page().forms[0]["action"], "/subscribe")

    def test_subscribe_normalises_unicode_and_redirects(self):
        status, headers, _ = self.post("  Анна  ")
        self.assertEqual(status, 303)
        self.assertEqual(headers["Location"], "/?result=added")
        self.assertEqual(self.page().names, ["Анна"])
        self.assertIn("Подписчик добавлен", self.request(path=headers["Location"])[2])

    def test_duplicate_does_not_add_another_record(self):
        self.post("Анна")
        status, headers, _ = self.post("  Анна  ")
        self.assertEqual(status, 303)
        self.assertEqual(headers["Location"], "/?result=duplicate")
        self.assertEqual(self.page().names, ["Анна"])
        self.assertIn("Уже подписан", self.request(path=headers["Location"])[2])

    def test_names_are_sorted(self):
        for name in ["Charlie", "Alice", "Bob"]:
            self.post(name)
        self.assertEqual(self.page().names, ["Alice", "Bob", "Charlie"])

    def test_form_roundtrip_subscribe_and_unsubscribe(self):
        form = self.page().forms[0]
        form["fields"]["name"] = "  Анна  "
        status, headers, _ = self.request(
            "POST", form["action"], urlencode(form["fields"]).encode(),
            {"Content-Type": "application/x-www-form-urlencoded"}
        )
        self.assertEqual(status, 303)
        self.assertIn("Анна", self.request(path=headers["Location"])[2])
        removal = self.page().forms[1]
        status, headers, _ = self.request(
            "POST", removal["action"], urlencode(removal["fields"]).encode(),
            {"Content-Type": "application/x-www-form-urlencoded"}
        )
        self.assertEqual(status, 303)
        self.assertEqual(self.page().names, [])
        self.assertIn("Подписчик удалён", self.request(path=headers["Location"])[2])

    def test_unsubscribe_only_removes_selected_name(self):
        self.post("Alice")
        self.post("Bob")
        status, headers, _ = self.post(" Alice ", "/unsubscribe")
        self.assertEqual(status, 303)
        self.assertEqual(headers["Location"], "/?result=removed")
        self.assertEqual(self.page().names, ["Bob"])

    def test_absent_unsubscribe_is_normal_idempotent_result(self):
        self.post("Bob")
        status, headers, _ = self.post("Alice", "/unsubscribe")
        self.assertEqual(status, 303)
        self.assertEqual(headers["Location"], "/?result=missing")
        self.assertEqual(self.page().names, ["Bob"])
        self.assertIn("Подписчик не найден", self.request(path=headers["Location"])[2])

    def test_eighty_unicode_characters_are_accepted(self):
        self.assertEqual(self.post("я" * 80)[0], 303)
        self.assertEqual(self.page().names, ["я" * 80])

    def test_padded_eighty_character_name_is_accepted(self):
        self.assertEqual(self.post("  " + "я" * 80 + "  ")[0], 303)
        self.assertEqual(self.page().names, ["я" * 80])

    def test_ui_does_not_truncate_name_before_server_normalisation(self):
        body = self.request()[2]
        self.assertNotIn("maxlength", body)
        self.assertNotIn("<script", body)

    def test_invalid_names_preserve_state_and_input_on_both_actions(self):
        self.post("Bob")
        for action in ["/subscribe", "/unsubscribe"]:
            for name in ["", "   ", "я" * 81]:
                with self.subTest(action=action, name=name):
                    status, _, body = self.post(name, action)
                    self.assertEqual(status, 400)
                    self.assertIn('role="alert"', body)
                    self.assertEqual(Page(body).forms[0]["fields"]["name"], name)
                    self.assertEqual(self.page().names, ["Bob"])

    def test_eighty_character_name_can_be_unsubscribed(self):
        self.post("я" * 80)
        self.assertEqual(self.post("я" * 80, "/unsubscribe")[0], 303)
        self.assertEqual(self.page().names, [])

    def test_user_markup_is_text_in_names_and_hidden_fields(self):
        name = '\"><script>alert("x")</script>&'
        self.post(name)
        body = self.request()[2]
        self.assertNotIn("<script", body)
        self.assertIn("&lt;script&gt;", body)
        page = Page(body)
        self.assertEqual(page.names, [name])
        self.assertEqual(page.forms[1]["fields"]["name"], name)

    def test_invalid_input_is_escaped_when_redisplayed(self):
        name = '<img src=x onerror="alert(1)">' + "x" * 81
        status, _, body = self.post(name)
        self.assertEqual(status, 400)
        self.assertNotIn("<img", body)
        self.assertEqual(Page(body).forms[0]["fields"]["name"], name)

    def test_malformed_form_is_rejected_before_mutation(self):
        self.post("Bob")
        for body in [b"", b"other=Alice", b"name=A&name=B", b"name=A&extra=B",
                     b"name", b"name=%FF", b"name=%XZ", b"name=\xff"]:
            with self.subTest(body=body):
                status, _, response = self.request(
                    "POST", "/subscribe", body,
                    {"Content-Type": "application/x-www-form-urlencoded"}
                )
                self.assertEqual(status, 400)
                self.assertEqual(Page(response).forms[0]["fields"]["name"], "")
                self.assertEqual(self.page().names, ["Bob"])

    def test_oversized_body_returns_413_without_mutation(self):
        self.post("Bob")
        status, _, _ = self.request(
            "POST", "/subscribe", b"name=" + b"a" * 4092,
            {"Content-Type": "application/x-www-form-urlencoded"}
        )
        self.assertEqual(status, 413)
        self.assertEqual(self.page().names, ["Bob"])

    def test_exact_body_limit_is_parsed_then_domain_validated(self):
        body = b"name=" + b" " * 4090 + b"A"
        self.assertEqual(len(body), 4096)
        self.assertEqual(self.request("POST", "/subscribe", body,
                         {"Content-Type": "application/x-www-form-urlencoded"})[0], 303)
        self.assertEqual(self.page().names, ["A"])

    def test_unsupported_content_type_returns_415(self):
        status, _, _ = self.request("POST", "/subscribe", b'name=Alice',
                                    {"Content-Type": "application/json"})
        self.assertEqual(status, 415)
        self.assertEqual(self.page().names, [])

    def test_explicit_utf8_form_charset_is_supported(self):
        status, _, _ = self.request(
            "POST", "/subscribe", urlencode({"name": "Анна"}).encode(),
            {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
        )
        self.assertEqual(status, 303)
        self.assertEqual(self.page().names, ["Анна"])

    def test_unsupported_charset_returns_415(self):
        self.assertEqual(self.request("POST", "/subscribe", b"name=A",
                         {"Content-Type": "application/x-www-form-urlencoded; charset=latin1"})[0], 415)

    def test_invalid_content_length_is_rejected(self):
        for length in ["-1", "wrong", "+6"]:
            with self.subTest(length=length):
                self.assertEqual(self.request("POST", "/subscribe", b"name=A", {
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Content-Length": length
                })[0], 400)
        self.assertEqual(self.page().names, [])

    def test_unknown_paths_return_404(self):
        self.assertEqual(self.request(path="/unknown")[0], 404)
        self.assertEqual(self.post("A", "/unknown")[0], 404)
        self.assertEqual(self.page().names, [])

    def test_unknown_result_is_not_reflected_into_html(self):
        body = self.request(path="/?result=%3Cscript%3Eunknown%3C/script%3E")[2]
        self.assertNotIn("unknown", body)
        self.assertNotIn("<script", body)

    def test_refresh_after_redirect_does_not_change_state(self):
        _, headers, _ = self.post("Анна")
        self.request(path=headers["Location"])
        self.request(path=headers["Location"])
        self.assertEqual(self.page().names, ["Анна"])

    def test_new_server_has_independent_empty_registry(self):
        self.post("Анна")
        with create_server(port=0) as other:
            self.assertEqual(other.registry.names(), [])
        self.assertEqual(self.page().names, ["Анна"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
