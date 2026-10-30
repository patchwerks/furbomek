"""Bounded HTTPS CONNECT proxy for credential-free dependency provisioning."""
import argparse
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


IDLE_TIMEOUT = 120
MAX_TUNNEL_SECONDS = 900
IO_TIMEOUT = 15


def bind_address(value):
    try:
        address = ipaddress.IPv4Address(value)
    except ipaddress.AddressValueError as error:
        raise argparse.ArgumentTypeError("A single numeric internal IPv4 address is required") from error
    if (not address.is_private or address.is_loopback or address.is_unspecified
            or address.is_multicast or address.is_link_local or address.is_reserved):
        raise argparse.ArgumentTypeError("A private non-loopback internal IPv4 address is required")
    return str(address)


def relay(client, upstream):
    started = last_activity = time.monotonic()
    while True:
        remaining = min(last_activity + IDLE_TIMEOUT, started + MAX_TUNNEL_SECONDS) - time.monotonic()
        if remaining <= 0:
            return
        readable, _, _ = select.select([client, upstream], [], [], min(1, remaining))
        for source in readable:
            remaining = min(last_activity + IDLE_TIMEOUT, started + MAX_TUNNEL_SECONDS) - time.monotonic()
            if remaining <= 0:
                return
            source.settimeout(min(IO_TIMEOUT, remaining))
            data = source.recv(65536)
            if not data:
                return
            destination = upstream if source is client else client
            remaining = min(last_activity + IDLE_TIMEOUT, started + MAX_TUNNEL_SECONDS) - time.monotonic()
            if remaining <= 0:
                return
            destination.settimeout(min(IO_TIMEOUT, remaining))
            destination.sendall(data)
            last_activity = time.monotonic()


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
            relay(self.connection, upstream)
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


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--bind-address", required=True, type=bind_address)
    args = parser.parse_args(argv)
    with Server((args.bind_address, 3128), Proxy) as server:
        server.serve_forever()


if __name__ == "__main__":
    main()
