"""Exercise HTTPS/WSS through the installed Daphne and a real TLS proxy.

Run ``uv run --locked python tests/e2e/https.py`` after installing Chromium with Playwright.
Certificates, accounts, database, media, and server settings are temporary. The
browser trusts only the generated certificate's public key; system trust stores
and the development database are untouched. Production settings are used with
an explicitly isolated, single-process in-memory channel layer and a test-only
static-file wrapper, so this check needs neither Redis nor a deployed web server.
"""

import base64
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import secrets
import select
import socket
from socketserver import BaseRequestHandler, ThreadingTCPServer
import ssl
import subprocess
import sys
import tempfile
import threading
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from dotenv import dotenv_values
from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[2]
PASSWORD = "https-browser-password-123"


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def certificate(directory):
    """Create a short-lived localhost certificate and its narrowly scoped trust."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Gravewright HTTPS test")])
    now = datetime.now(timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(hours=1))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
                x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
            ]),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )
    key_path = directory / "key.pem"
    cert_path = directory / "cert.pem"
    key_path.write_bytes(key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    ))
    key_path.chmod(0o600)
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    public_key = key.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    fingerprint = base64.b64encode(hashlib.sha256(public_key).digest()).decode("ascii")
    return key_path, cert_path, fingerprint


class ProxyHandler(BaseRequestHandler):
    """Terminate TLS, replace forwarded headers, and relay HTTP or WebSocket bytes."""

    def handle(self):
        try:
            with self.server.tls.wrap_socket(self.request, server_side=True) as client:
                client.settimeout(10)
                data = b""
                while b"\r\n\r\n" not in data:
                    chunk = client.recv(65536)
                    if not chunk:
                        return
                    data += chunk
                    if len(data) > 131072:
                        raise ValueError("Test proxy request headers exceeded limit")
                header, body = data.split(b"\r\n\r\n", 1)
                lines = header.split(b"\r\n")
                websocket = any(
                    line.lower() == b"upgrade: websocket" for line in lines[1:]
                )
                # Each ordinary HTTP request gets its own backend connection;
                # WebSocket connections remain open after their Upgrade response.
                forwarded = [lines[0]] + [
                    line for line in lines[1:]
                    if not line.lower().startswith((b"x-forwarded-", b"connection:"))
                ]
                forwarded += [
                    b"X-Forwarded-Proto: https",
                    b"Connection: Upgrade" if websocket else b"Connection: close",
                ]
                with socket.create_connection(("127.0.0.1", self.server.backend), timeout=10) as backend:
                    backend.sendall(b"\r\n".join(forwarded) + b"\r\n\r\n" + body)
                    peers = {client: backend, backend: client}
                    while not self.server.stopping.is_set():
                        readable, _, _ = select.select(list(peers), [], [], 0.5)
                        if client.pending() and client not in readable:
                            readable.append(client)
                        for source in readable:
                            chunk = source.recv(65536)
                            if not chunk:
                                return
                            peers[source].sendall(chunk)
        except (OSError, ssl.SSLError):
            # Browsers abandon speculative connections and close sockets on exit.
            pass


class TLSProxy(ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, port, backend, key_path, cert_path):
        self.backend = backend
        self.stopping = threading.Event()
        self.tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self.tls.load_cert_chain(cert_path, key_path)
        super().__init__(("127.0.0.1", port), ProxyHandler)


@contextmanager
def proxy(port, backend, key_path, cert_path):
    with TLSProxy(port, backend, key_path, cert_path) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield
        finally:
            server.stopping.set()
            server.shutdown()
            thread.join(timeout=5)


def wait_ready(server, base, trust, log_path):
    for _ in range(150):
        if server.poll() is not None:
            raise RuntimeError(f"Daphne exited; inspect {log_path}")
        try:
            with urlopen(base + "/api/auth/status", context=trust, timeout=1) as response:
                assert response.status == 200
                assert response.headers["Strict-Transport-Security"] == "max-age=31536000"
                return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError(f"Daphne did not become ready; inspect {log_path}")


def request_json(page, path, *, method="GET", data=None, token=None):
    """Use the browser's TLS and cookie handling, including real Origin/CSRF."""
    return page.evaluate(
        """async ({path, method, data, token}) => {
            const headers = {};
            if (data !== null) headers['Content-Type'] = 'application/json';
            if (token !== null) headers['X-CSRF-Token'] = token;
            const response = await fetch(path, {
                method, headers, body: data === null ? undefined : JSON.stringify(data)
            });
            const text = await response.text();
            return {status: response.status, body: text ? JSON.parse(text) : null};
        }""",
        {"path": path, "method": method, "data": data, "token": token},
    )


def handshake_status(port, path, origin, cookie, trust):
    """Send an authenticated real WSS handshake with a controlled Origin."""
    headers = [
        f"GET {path} HTTP/1.1",
        f"Host: 127.0.0.1:{port}",
        "Upgrade: websocket",
        "Connection: Upgrade",
        "Sec-WebSocket-Version: 13",
        "Sec-WebSocket-Key: " + base64.b64encode(os.urandom(16)).decode("ascii"),
        f"Cookie: {cookie}",
    ]
    if origin is not None:
        headers.append(f"Origin: {origin}")
    with socket.create_connection(("127.0.0.1", port), timeout=10) as raw:
        with trust.wrap_socket(raw, server_hostname="127.0.0.1") as connection:
            connection.sendall(("\r\n".join(headers) + "\r\n\r\n").encode("ascii"))
            response = b""
            while b"\r\n" not in response:
                chunk = connection.recv(4096)
                if not chunk:
                    raise AssertionError("WSS server closed before responding")
                response += chunk
            return int(response.split(b" ", 2)[1])


def browser_checks(pw, base, fingerprint, trust, *, proxied):
    with pw.chromium.launch(args=[
        "--ignore-certificate-errors-spki-list=" + fingerprint,
    ]) as browser:
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        context.add_init_script("""
            window.httpsFrames = [];
            window.httpsSockets = [];
            const Native = window.WebSocket;
            window.WebSocket = class extends Native {
                constructor(...args) {
                    super(...args);
                    window.httpsSockets.push(this);
                    this.addEventListener('message', event => {
                        window.httpsFrames.push(JSON.parse(event.data));
                    });
                }
            };
        """)
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        response = page.goto(base)
        assert response.headers["strict-transport-security"] == "max-age=31536000"
        page.locator("#owner-name").fill("HTTPS Owner")
        page.locator("#owner-email").fill("https-owner@example.test")
        page.locator("#owner-password").fill(PASSWORD)
        page.get_by_role("button", name="Create administrator", exact=True).click()
        expect(page.locator("#inside-shell")).to_be_visible()
        assert request_json(page, "/api/auth/session")["body"]["authenticated"]

        cookies = {cookie["name"]: cookie for cookie in context.cookies()}
        for name in ("__Host-gravewright-session", "__Host-gravewright-csrf"):
            assert cookies[name]["secure"] and cookies[name]["path"] == "/"
            assert cookies[name]["sameSite"] == "Strict"
        assert cookies["__Host-gravewright-session"]["httpOnly"]
        token = cookies["__Host-gravewright-csrf"]["value"]
        invalid = request_json(page, "/api/containers", method="POST", data={
            "name": "Invalid CSRF", "system": "gravewright-pdf-system",
        }, token="forged")
        assert invalid["status"] == 403, invalid
        created = request_json(page, "/api/containers", method="POST", data={
            "name": "HTTPS table", "system": "gravewright-pdf-system",
        }, token=token)
        assert created["status"] == 201, created
        campaign = created["body"]["id"]
        cookie = "; ".join(f"{name}={value['value']}" for name, value in cookies.items())
        malicious = Request(base + "/api/containers", method="POST", data=json.dumps({
            "name": "Foreign origin", "system": "gravewright-pdf-system",
        }).encode(), headers={
            "Cookie": cookie, "Content-Type": "application/json",
            "X-CSRF-Token": token, "Origin": "https://foreign.example.test",
        })
        try:
            with urlopen(malicious, context=trust, timeout=10) as response:
                raise AssertionError(f"Foreign HTTP Origin returned {response.status}")
        except HTTPError as error:
            assert error.code == 403, error.code

        port = int(base.rsplit(":", 1)[1])
        path = f"/ws/tables/{campaign}/"
        for origin in (None, "https://foreign.example.test", base.replace("https:", "http:"),
                       f"https://127.0.0.1:{port + 1 if port < 65535 else port - 1}"):
            assert handshake_status(port, path, origin, cookie, trust) == 403, origin

        page.goto(base + "/game/" + campaign)
        expect(page.locator(".game-menubar__presence")).to_have_attribute(
            "data-presence", "seated", timeout=15000
        )
        page.wait_for_function("httpsFrames.some(frame => frame.type === 'table.joined')")
        assert page.evaluate("httpsSockets.every(socket => socket.url.startsWith('wss://'))")
        page.get_by_role("button", name="Chat", exact=True).click()
        page.locator("#chat-form textarea").fill("Authenticated chat over HTTPS")
        page.get_by_role("button", name="Send", exact=True).click()
        expect(page.locator("#chat-log article")).to_have_count(1)
        expect(page.locator("#chat-log article")).to_contain_text("Authenticated chat over HTTPS")
        page.wait_for_function("httpsFrames.some(frame => frame.type === 'chat.message')")
        page.reload()
        expect(page.locator(".game-menubar__presence")).to_have_attribute(
            "data-presence", "seated", timeout=15000
        )
        assert request_json(page, "/api/auth/session")["body"]["authenticated"]
        assert not errors, errors

        if proxied:
            # The proxy replaces an attacker-supplied scheme instead of appending it.
            forged = Request(base + "/api/auth/status", headers={"X-Forwarded-Proto": "http"})
            with urlopen(forged, context=trust, timeout=10) as response:
                assert response.headers["Strict-Transport-Security"] == "max-age=31536000"


def scenario(pw, directory, key_path, cert_path, fingerprint, *, proxied):
    label = "tls-proxy" if proxied else "direct-tls"
    work = directory / label
    work.mkdir()
    public_port, backend_port = free_port(), free_port()
    while backend_port == public_port:
        backend_port = free_port()
    base = f"https://127.0.0.1:{public_port}"
    # Redis is replaced only in this generated test settings module. The import
    # still validates all normal DEBUG=false settings, including the secret key.
    (work / "https_settings.py").write_text(
        "from config.settings import *\n"
        "CHANNEL_LAYERS = {'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}}\n"
    )
    (work / "https_application.py").write_text(
        "from config.asgi import application as project_application\n"
        "from django.contrib.staticfiles.handlers import ASGIStaticFilesHandler\n"
        "application = ASGIStaticFilesHandler(project_application)\n"
    )
    # Project defaults override inherited operator settings, including optional
    # external integrations; scenario values then select isolated test resources.
    env = {
        **os.environ,
        **{name: value for name, value in dotenv_values(
            ROOT / ".env.example", interpolate=False
        ).items() if value is not None},
        "PYTHONPATH": os.pathsep.join((str(work), str(ROOT))),
        "PYTHONUNBUFFERED": "1",
        "DJANGO_SETTINGS_MODULE": "https_settings",
        "DJANGO_DEBUG": "false",
        "DJANGO_SECRET_KEY": secrets.token_urlsafe(48),
        "DJANGO_ALLOWED_HOSTS": "127.0.0.1",
        "DJANGO_SECURE_COOKIES": "true",
        "GRAVEWRIGHT_DATABASE": str(work / "db.sqlite3"),
        "GRAVEWRIGHT_MEDIA_ROOT": str(work / "media"),
        "GRAVEWRIGHT_PUBLIC_ORIGIN": base,
        "GRAVEWRIGHT_REDIS_URL": "redis://127.0.0.1:1/0",
        "TRUSTED_PROXIES": "127.0.0.1/32" if proxied else "",
    }
    subprocess.run([sys.executable, "manage.py", "migrate", "--noinput"],
                   cwd=ROOT, env=env, check=True, stdout=subprocess.DEVNULL)
    command = [sys.executable, "-m", "daphne"]
    if proxied:
        command += ["-b", "127.0.0.1", "-p", str(backend_port)]
    else:
        command += ["-e", (
            f"ssl:port={public_port}:interface=127.0.0.1:"
            f"privateKey={key_path}:certKey={cert_path}"
        )]
    command += ["https_application:application"]
    output = ROOT / "test-results" / "https"
    output.mkdir(parents=True, exist_ok=True)
    log_path = output / (label + ".log")
    trust = ssl.create_default_context(cafile=str(cert_path))
    with log_path.open("w") as log:
        server = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log, stderr=log)
        try:
            if proxied:
                with proxy(public_port, backend_port, key_path, cert_path):
                    wait_ready(server, base, trust, log_path)
                    browser_checks(pw, base, fingerprint, trust, proxied=True)
            else:
                wait_ready(server, base, trust, log_path)
                browser_checks(pw, base, fingerprint, trust, proxied=False)
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()
    print(f"{label}: HTTPS setup, secure cookies, HSTS, CSRF, WSS origins and chat passed.", flush=True)


def main():
    with tempfile.TemporaryDirectory(prefix="grave-https-") as temp:
        directory = Path(temp)
        key_path, cert_path, fingerprint = certificate(directory)
        with sync_playwright() as pw:
            for proxied in (False, True):
                scenario(pw, directory, key_path, cert_path, fingerprint, proxied=proxied)
    print("HTTPS/WSS checks passed; development data and certificate trust are unchanged.", flush=True)


if __name__ == "__main__":
    main()
