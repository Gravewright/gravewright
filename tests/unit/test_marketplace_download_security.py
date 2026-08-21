from __future__ import annotations

import socket

import pytest

from app.engine.sdk import marketplace_service as remote


def addresses(value: str):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (value, 443))]


@pytest.mark.parametrize("value", [
    "file:///etc/passwd", "ftp://example.com/a", "http://example.com/a",
    "https://localhost/a", "https://127.0.0.1/a", "https://[::1]/a",
    "https://169.254.169.254/latest/meta-data", "https://10.0.0.1/a",
    "https://user:pass@example.com/a",
])
def test_remote_url_policy_is_https_and_rejects_internal_targets(value: str) -> None:
    assert not remote._safe_remote_url(value)


def test_dns_resolution_rejects_any_private_answer(monkeypatch) -> None:
    monkeypatch.setattr(socket, "getaddrinfo", lambda *_args, **_kwargs:
                        addresses("93.184.216.34") + addresses("10.0.0.4"))
    with pytest.raises(ValueError, match="MARKETPLACE_DNS_UNSAFE"):
        remote._resolved_public_addresses("packages.example", 443)


class Response:
    def __init__(self, *, status=200, data=b"ok", headers=None):
        self.status, self.data, self.headers, self.offset = status, data, headers or {}, 0
    def getheader(self, name): return self.headers.get(name)
    def read(self, size):
        value = self.data[self.offset:self.offset + size]
        self.offset += len(value)
        return value


class Connection:
    responses = []
    pins = []
    def __init__(self, host, address, port, timeout):
        self.__class__.pins.append((host, address, port, timeout))
    def request(self, *_args, **_kwargs): pass
    def getresponse(self): return self.__class__.responses.pop(0)
    def close(self): pass


def public_dns(host, *_args, **_kwargs):
    value = "127.0.0.1" if host == "127.0.0.1" else "93.184.216.34"
    return addresses(value)


def test_fetch_pins_validated_ip_and_bounds_real_bytes(monkeypatch) -> None:
    Connection.responses = [Response(data=b"12345", headers={"Content-Length": "5"})]
    Connection.pins = []
    monkeypatch.setattr(socket, "getaddrinfo", public_dns)
    monkeypatch.setattr(remote, "_PinnedHTTPSConnection", Connection)
    assert remote.fetch_bytes("https://packages.example/a", 5) == b"12345"
    assert Connection.pins[0][1] == "93.184.216.34"
    Connection.responses = [Response(data=b"123456")]
    with pytest.raises(ValueError, match="MARKETPLACE_RESPONSE_TOO_LARGE"):
        remote.fetch_bytes("https://packages.example/a", 5)


def test_redirect_to_internal_address_is_rejected_before_connection(monkeypatch) -> None:
    Connection.responses = [Response(status=302, headers={"Location": "https://127.0.0.1/private"})]
    Connection.pins = []
    monkeypatch.setattr(socket, "getaddrinfo", public_dns)
    monkeypatch.setattr(remote, "_PinnedHTTPSConnection", Connection)
    with pytest.raises(ValueError, match="MARKETPLACE_URL_UNSAFE|MARKETPLACE_DNS_UNSAFE"):
        remote.fetch_bytes("https://packages.example/a", 100)
    assert len(Connection.pins) == 1


def test_incomplete_content_length_fails_closed(monkeypatch) -> None:
    Connection.responses = [Response(data=b"short", headers={"Content-Length": "10"})]
    monkeypatch.setattr(socket, "getaddrinfo", public_dns)
    monkeypatch.setattr(remote, "_PinnedHTTPSConnection", Connection)
    with pytest.raises(ValueError, match="MARKETPLACE_RESPONSE_INCOMPLETE"):
        remote.fetch_bytes("https://packages.example/a", 100)
