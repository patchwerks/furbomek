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


if __name__ == "__main__":
    unittest.main()
