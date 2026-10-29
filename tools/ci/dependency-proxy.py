"""Bounded HTTPS CONNECT proxy for credential-free dependency provisioning."""
import ipaddress
import select
import socket
import socketserver
import time
from http.server import BaseHTTPRequestHandler

HOSTS = frozenset({"pypi.org", "files.pythonhosted.org", "registry.npmjs.org"})


def target(value):
    host, separator, port = value.rpartition(":")
    if separator and port == "443" and host.lower() in HOSTS:
        return host.lower()
    return None


class Proxy(BaseHTTPRequestHandler):
    timeout = 15

    def do_CONNECT(self):
        host = target(self.path)
        if host is None:
            self.send_error(403, "Dependency host not allowed")
            return
        upstream = None
        try:
            addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
            for family, kind, protocol, _, address in addresses:
                if not ipaddress.ip_address(address[0]).is_global:
                    continue
                candidate = socket.socket(family, kind, protocol)
                candidate.settimeout(15)
                try:
                    candidate.connect(address)
                except OSError:
                    candidate.close()
                    continue
                upstream = candidate
                break
            if upstream is None:
                self.send_error(502, "No public dependency endpoint")
                return
            self.send_response(200, "Connection established")
            self.end_headers()
            self.wfile.flush()
            self.connection.settimeout(15)
            deadline = time.monotonic() + 120
            while time.monotonic() < deadline:
                readable, _, _ = select.select([self.connection, upstream], [], [], 1)
                for source in readable:
                    data = source.recv(65536)
                    if not data:
                        return
                    destination = upstream if source is self.connection else self.connection
                    destination.sendall(data)
        except OSError:
            return
        finally:
            if upstream is not None:
                upstream.close()

    def log_message(self, format, *args):
        # Avoid copying package paths, authorization headers or request payloads.
        pass


class Server(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True


if __name__ == "__main__":
    with Server(("0.0.0.0", 3128), Proxy) as server:
        server.serve_forever()
