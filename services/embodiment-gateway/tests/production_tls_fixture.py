"""Ephemeral certificates and loopback routing for real provider TLS clients."""

import socket
import ssl
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID


@dataclass(frozen=True, slots=True)
class TlsContexts:
    server: ssl.SSLContext
    client: ssl.SSLContext


def contexts(tmp_path: Path) -> TlsContexts:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "fixture.invalid")])
    now = datetime.now(UTC)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=1))
        .add_extension(
            x509.SubjectAlternativeName(
                [
                    x509.DNSName(host)
                    for host in (
                        "api.hyperliquid.xyz",
                        "eventsub.wss.twitch.tv",
                        "id.twitch.tv",
                        "api.twitch.tv",
                    )
                ]
            ),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )
    cert_file, key_file = tmp_path / "cert.pem", tmp_path / "key.pem"
    _ = cert_file.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    _ = key_file.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    key_file.chmod(0o600)
    server = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server.load_cert_chain(cert_file, key_file)
    client = ssl.create_default_context(cafile=str(cert_file))
    return TlsContexts(server, client)


def route_loopback(monkeypatch: pytest.MonkeyPatch, port: int) -> None:
    original = socket.create_connection

    def connect(
        address: tuple[str, int],
        timeout: float | None = None,
        source_address: tuple[str, int] | None = None,
    ) -> socket.socket:
        if address[0] not in {
            "api.hyperliquid.xyz",
            "eventsub.wss.twitch.tv",
            "id.twitch.tv",
            "api.twitch.tv",
        }:
            msg = "unapproved test peer"
            raise AssertionError(msg)
        return original(("127.0.0.1", port), timeout, source_address)

    monkeypatch.setattr(socket, "create_connection", connect)
