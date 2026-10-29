"""Additional input, role, audit and resource-bound checks after hardening."""

from http.client import HTTPConnection
import json
import socket
import unittest

from attacks import running_shop
from service import Shop, MAX_REVIEWS, MAX_SESSIONS, SESSION_TTL


class ProtocolTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scope = running_shop()
        cls.client = cls.scope.__enter__()
        cls.auth = cls.client.login("alice")

    @classmethod
    def tearDownClass(cls):
        cls.scope.__exit__(None, None, None)

    def test_duplicate_json_fields_are_rejected(self):
        self.assertEqual(self.client.call("POST", "/login", raw=b'{"username":"alice","username":"bob"}')[0], 400)

    def test_nonfinite_json_is_rejected(self):
        self.assertEqual(self.client.call("POST", "/orders", raw=b'{"product":"chair","price":NaN}', auth=self.auth)[0], 400)

    def test_wrong_content_type_is_rejected(self):
        self.assertEqual(self.client.call("POST", "/login", raw=b"{}", headers={"Content-Type": "text/plain"})[0], 415)

    def test_duplicate_query_values_are_rejected(self):
        self.assertEqual(self.client.call("GET", "/profile?id=1&id=2", auth=self.auth)[0], 400)

    def test_invalid_utf8_json_is_rejected(self):
        self.assertEqual(self.client.call("POST", "/login", raw=b'{"username":"\xff"}')[0], 400)

    def test_excessive_json_nesting_returns_400(self):
        self.assertEqual(self.client.call("POST", "/login", raw=b"[" * 1100 + b"0" + b"]" * 1100)[0], 400)

    def test_incomplete_headers_have_read_deadline(self):
        with socket.create_connection(("127.0.0.1", self.client.port), timeout=5) as connection:
            connection.sendall(b"GET /health HTTP/1.1\r\nHost: 127.0.0.1\r\n")
            self.assertEqual(connection.recv(1), b"")

    def test_oversized_body_is_rejected(self):
        self.assertEqual(self.client.call("POST", "/reviews", raw=b" " * 65537, auth=self.auth)[0], 413)

    def test_duplicate_content_length_is_rejected(self):
        connection = HTTPConnection("127.0.0.1", self.client.port, timeout=5)
        try:
            connection.putrequest("POST", "/login")
            connection.putheader("Content-Type", "application/json")
            connection.putheader("Content-Length", "2")
            connection.putheader("Content-Length", "2")
            connection.endheaders(b"{}")
            response = connection.getresponse()
            response.read()
            self.assertEqual(response.status, 400)
        finally:
            connection.close()

    def test_staff_role_header_is_not_needed(self):
        staff = self.client.login("staff")
        self.assertEqual(self.client.call("GET", "/admin/export", auth=staff)[0], 200)

    def test_refuse_is_supported_without_changing_receipt(self):
        self.assertEqual(self.client.call("POST", "/assistant/execute",
                         {"decision": {"tool": "refuse", "arguments": {"reason": "unsafe"}}}, self.auth)[0], 200)
        self.assertIn("TEST_ALICE", self.client.call("GET", "/files", auth=self.auth)[1]["content"])

    def test_security_headers_are_present(self):
        connection = HTTPConnection("127.0.0.1", self.client.port, timeout=5)
        try:
            connection.request("GET", "/reviews/view", headers=self.auth)
            response = connection.getresponse()
            response.read()
            self.assertIn("default-src 'none'", response.getheader("Content-Security-Policy"))
            self.assertEqual(response.getheader("X-Content-Type-Options"), "nosniff")
        finally:
            connection.close()


class StatePolicyTest(unittest.TestCase):
    def setUp(self):
        self.shop = Shop()
        self.addCleanup(self.shop.close)
        _, result = self.shop.dispatch("POST", "/login", {"username": "alice", "password": "learn-alice"}, {})
        self.token = result["token"]
        self.auth = {"X-Token": self.token}

    def call(self, method, path, body=None, auth=None):
        return self.shop.dispatch(method, path, body or {}, self.auth if auth is None else auth)

    def test_expired_session_is_rejected(self):
        # Advance a server-owned fixture timestamp without sleeping 30 minutes.
        self.shop.sessions[self.token]["created"] -= SESSION_TTL + 1
        self.assertEqual(self.call("GET", "/orders")[0], 401)

    def test_audit_has_no_credentials_or_bodies(self):
        self.call("GET", "/profile?id=1")
        text = json.dumps(list(self.shop.logs))
        self.assertNotIn(self.token, text)
        self.assertNotIn("learn-alice", text)
        self.assertNotIn("?id=", text)
        self.assertEqual(set(self.shop.logs[-1]), {"method", "path", "status", "actor"})

    def test_audit_has_bounded_retention(self):
        for _ in range(110):
            self.call("GET", "/health")
        self.assertEqual(len(self.shop.logs), 100)

    def test_review_count_is_bounded(self):
        for _ in range(MAX_REVIEWS):
            self.assertEqual(self.call("POST", "/reviews", {"product": "chair", "text": "ok"})[0], 201)
        self.assertEqual(self.call("POST", "/reviews", {"product": "chair", "text": "excess"})[0], 429)

    def test_login_failures_are_throttled(self):
        for _ in range(10):
            self.assertEqual(self.call("POST", "/login", {"username": "alice", "password": "wrong"}, {})[0], 401)
        self.assertEqual(self.call("POST", "/login", {"username": "alice", "password": "wrong"}, {})[0], 429)

    def test_session_count_is_bounded(self):
        for _ in range(MAX_SESSIONS - 1):
            self.assertEqual(self.call("POST", "/login", {"username": "alice", "password": "learn-alice"}, {})[0], 200)
        self.assertEqual(self.call("POST", "/login", {"username": "alice", "password": "learn-alice"}, {})[0], 429)

    def test_order_count_is_bounded(self):
        for _ in range(498):
            self.assertEqual(self.call("POST", "/orders", {"product": "chair"})[0], 201)
        self.assertEqual(self.call("POST", "/orders", {"product": "chair"})[0], 429)

    def test_unknown_json_shapes_return_400(self):
        for body in [{}, {"decision": []}, {"decision": {"tool": "read_file", "arguments": []}},
                     {"decision": {"tool": "read_file", "arguments": {"path": None}}}]:
            with self.subTest(body=body):
                self.assertEqual(self.call("POST", "/assistant/execute", body)[0], 400)

    def test_staff_cannot_use_destructive_ai_tools(self):
        _, result = self.call("POST", "/login", {"username": "staff", "password": "learn-staff"}, {})
        status, _ = self.call("POST", "/assistant/execute",
                              {"decision": {"tool": "delete_tree", "arguments": {"path": "."}}},
                              {"X-Token": result["token"]})
        self.assertEqual(status, 403)
        self.assertIn("TEST_ALICE", self.call("GET", "/files")[1]["content"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
