# Security

[English](SECURITY.md) · [Português (Brasil)](SECURITY.pt-BR.md)

## Reporting

Report vulnerabilities privately through the hosting platform's private vulnerability reporting feature, if it is enabled for the repository. This source tree does not specify a security email address or guarantee that private reporting is enabled. If no private channel is available, open an issue requesting a private contact without including exploit details, credentials or affected users' data.

Include the affected version, reproduction steps using synthetic data, the affected permission boundary and expected impact. Redact cookies, tokens, `.env` values and private uploads. There is no published support window or response-time commitment in this repository.

## Relevant boundaries

Sessions authenticate browser requests; VTT owner, campaign GM/player membership, document permissions and streamer access are separate checks. A Django superuser is not automatically the VTT owner. State-changing HTTP calls require CSRF protection; the configured header is `X-CSRF-Token`. WebSocket handshakes require a matching origin and host, and commands revalidate the relevant authorization.

For HTTPS, configure the public origin and use a TLS endpoint. The WebSocket origin check enforces the configured scheme, domain and effective port, including when Daphne omits its WebSocket scheme. Forwarded schemes and client IPs are trusted only from socket peers in `TRUSTED_PROXIES`; keep Daphne's `--proxy-headers` disabled and overwrite forwarding headers at the proxy. Follow the [HTTPS deployment guide](docs/en/deployment.md) for the complete proxy setup.

Private files must continue through the application's guarded views. Never expose `MEDIA_ROOT`, SQLite databases or backup archives as public static directories. Treat installed modules as trusted application code: their JavaScript runs in the main page on the application's origin. Signatures and manifests establish package identity/integrity; they do not sandbox code or prove it harmless.

The [Windows runner](docs/en/windows-runner.md) binds only to `127.0.0.1` and uses a dedicated local profile with debug disabled, a persistent personal secret and one in-memory Channels process. Its local HTTP settings are not a deployment configuration for a LAN or public reverse proxy. Browser origin, host, session, CSRF and campaign checks still apply. Protect the runner's personal data directory and backups as carefully as server data.

The current content security policy permits `unsafe-eval` for Datastar expressions and inline styles. Keep untrusted rich content inside the journal/document validators rather than interpolating it as executable markup.

Review [configuration](docs/en/configuration.md), [modules](docs/en/modules.md) and [third-party notices](THIRD_PARTY_NOTICES.md) when changing these boundaries or upgrading dependencies.
