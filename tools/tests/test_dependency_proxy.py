"""Prevent hostname suffixes, alternate ports and private destinations bypassing policy."""
import importlib.util
from pathlib import Path
import unittest

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


if __name__ == "__main__":
    unittest.main()
