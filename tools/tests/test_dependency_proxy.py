"""Prevent hostname suffixes, alternate ports and private destinations bypassing policy."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location(
    "dependency_proxy", Path(__file__).parents[1] / "ci/dependency-proxy.py"
)
proxy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(proxy)


class TargetPolicyTests(unittest.TestCase):
    def test_only_exact_package_hosts_on_tls_port(self):
        for host in ("pypi.org", "files.pythonhosted.org", "registry.npmjs.org"):
            self.assertEqual(proxy.target(host + ":443"), host)
            self.assertEqual(proxy.target(host.upper() + ":443"), host)

    def test_rejects_other_hosts_ports_and_ambiguous_authorities(self):
        for value in (
            "pypi.org:80", "pypi.org:8443", "example.com:443", "pypi.org.evil.test:443",
            "evilpypi.org:443", "pypi.org@127.0.0.1:443", "127.0.0.1:443",
            "169.254.169.254:443", "[::1]:443", "pypi.org.:443", "pypi.org:443/path",
            "https://pypi.org:443", "pypi.org:443\r\nX: y", "pypi.org", "",
        ):
            self.assertIsNone(proxy.target(value), value)


class ConnectionPolicyTests(unittest.TestCase):
    def handler(self, authority):
        handler = object.__new__(proxy.Proxy)
        handler.path = authority
        handler.send_error = Mock()
        return handler

    def test_forbidden_authority_never_resolves_or_connects(self):
        handler = self.handler("example.com:443")
        with patch.object(proxy.socket, "getaddrinfo") as resolve, patch.object(proxy.socket, "socket") as connect:
            handler.do_CONNECT()
        handler.send_error.assert_called_once_with(403, "Dependency host not allowed")
        resolve.assert_not_called()
        connect.assert_not_called()

    def test_allowed_hostname_cannot_resolve_to_private_endpoint(self):
        for address in ("127.0.0.1", "10.0.0.1", "169.254.169.254", "192.168.1.1", "::1", "fd00::1"):
            with self.subTest(address=address):
                handler = self.handler("pypi.org:443")
                answer = [(proxy.socket.AF_INET, proxy.socket.SOCK_STREAM, 0, "", (address, 443))]
                with patch.object(proxy.socket, "getaddrinfo", return_value=answer), patch.object(proxy.socket, "socket") as connect:
                    handler.do_CONNECT()
                handler.send_error.assert_called_once_with(502, "No public dependency endpoint")
                connect.assert_not_called()


class BindingTests(unittest.TestCase):
    def test_invalid_binding_never_constructs_server(self):
        import contextlib
        import io
        for args in ([], *(["--bind-address", value] for value in (
            "0.0.0.0", "127.0.0.1", "8.8.8.8", "224.0.0.1", "::1",
            "169.254.1.2", "dependency-proxy", "10.0.0.1 10.0.0.2", "", "garbage"))):
            with self.subTest(args=args), patch.object(proxy, "Server") as server:
                with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                    proxy.main(args)
                server.assert_not_called()

    def test_explicit_internal_address_is_the_only_listener(self):
        with patch.object(proxy, "Server") as server:
            proxy.main(["--bind-address", "172.29.4.2"])
        server.assert_called_once_with(("172.29.4.2", 3128), proxy.Proxy)
        server.return_value.__enter__.return_value.serve_forever.assert_called_once()


class RelayTests(unittest.TestCase):
    def exercise(self, events, *, recv_delay=0, send_delay=0, send_error=False):
        # Events are readiness times and direction; the production function owns
        # every timeout/deadline calculation, byte transfer and termination.
        self.now = 0.0
        self.transfers = []
        self.timeouts = []
        events = list(events)
        owner = self

        class Endpoint:
            def __init__(self, name):
                self.name = name
            def settimeout(self, duration):
                owner.timeouts.append((owner.now, duration))
            def recv(self, size):
                owner.now += recv_delay
                return b"" if self.name == "eof" else self.name.encode()
            def sendall(self, data):
                if send_error:
                    raise OSError("fake send failure")
                owner.now += send_delay
                owner.transfers.append((owner.now, self.name, data))

        client, upstream = Endpoint("client"), Endpoint("upstream")
        def select(readers, writers, errors, timeout):
            self.assertGreater(timeout, 0)
            self.assertLessEqual(timeout, 1)
            self.assertLess(self.now, 901, "production relay exceeded hard limit")
            if events and events[0][0] <= self.now + timeout:
                self.now, direction = events.pop(0)
                if direction == "both":
                    return [client, upstream], [], []
                if direction == "eof":
                    client.name = "eof"
                return [upstream if direction == "upstream" else client], [], []
            self.now += timeout
            return [], [], []
        with patch.object(proxy.time, "monotonic", side_effect=lambda: self.now), patch.object(proxy.select, "select", side_effect=select):
            proxy.relay(client, upstream)

    def test_successful_bidirectional_bytes_renew_idle_past_old_cutoff(self):
        self.exercise([(90, "client"), (180, "upstream"), (270, "client")])
        self.assertEqual([row[0] for row in self.transfers], [90, 180, 270])
        self.assertEqual(self.now, 390)
        self.assertEqual(self.transfers[1][1:], ("client", b"upstream"))

    def test_idle_connection_stops_at_120(self):
        self.exercise([])
        self.assertEqual(self.now, 120)
        self.assertEqual(self.transfers, [])

    def test_trickle_cannot_extend_hard_maximum(self):
        self.exercise([(time, "client") for time in range(90, 1000, 90)])
        self.assertEqual(self.now, 900)
        self.assertEqual(len(self.transfers), 9)

    def test_eof_exits_without_renewal(self):
        self.exercise([(5, "eof")])
        self.assertEqual(self.now, 5)
        self.assertEqual(self.transfers, [])

    def test_send_failure_propagates_to_handler_cleanup(self):
        with self.assertRaises(OSError):
            self.exercise([(5, "client")], send_error=True)
        self.assertEqual(self.transfers, [])

    def test_ready_at_deadline_does_not_forward(self):
        self.exercise([(120, "client")])
        self.assertEqual(self.transfers, [])

    def test_recv_cannot_use_expired_send_budget(self):
        self.exercise([(119, "client")], recv_delay=1)
        self.assertEqual(self.now, 120)
        self.assertEqual(self.transfers, [])
        self.assertEqual(self.timeouts, [(119, 1)])

    def test_second_ready_direction_cannot_cross_maximum(self):
        self.exercise([(t, "client") for t in range(90, 900, 90)] + [(899, "both")], send_delay=1)
        self.assertEqual(self.now, 900)
        self.assertEqual(self.transfers[-1], (900, "upstream", b"client"))
        self.assertEqual(self.timeouts[-1], (899, 1))

    def test_connect_handler_calls_real_relay_and_closes_on_send_failure(self):
        handler = object.__new__(proxy.Proxy)
        handler.path = "pypi.org:443"
        handler.send_response = Mock()
        handler.end_headers = Mock()
        handler.wfile = Mock()
        handler.connection = Mock()
        handler.connection.recv.return_value = b"hello"
        upstream = Mock()
        upstream.sendall.side_effect = OSError("failed")
        answer = [(proxy.socket.AF_INET, proxy.socket.SOCK_STREAM, 0, "", ("1.1.1.1", 443))]
        with patch.object(proxy.socket, "getaddrinfo", return_value=answer), patch.object(proxy.socket, "socket", return_value=upstream), patch.object(proxy.select, "select", return_value=([handler.connection], [], [])):
            handler.do_CONNECT()
        upstream.sendall.assert_called_once_with(b"hello")
        upstream.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
