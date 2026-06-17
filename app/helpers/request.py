from __future__ import annotations

from ipaddress import ip_address
from ipaddress import ip_network

from litestar import Request

from app.config import config


def get_client_ip(request: Request) -> str:
    peer_ip = request.client.host if request.client else None

    if _is_trusted_proxy(peer_ip):
        forwarded_for = request.headers.get("x-forwarded-for")

        if forwarded_for:
            return forwarded_for.split(",", 1)[0].strip()

        real_ip = request.headers.get("x-real-ip")

        if real_ip:
            return real_ip.strip()

    if peer_ip:
        return peer_ip

    return "unknown"


def _is_trusted_proxy(peer_ip: str | None) -> bool:
    if not peer_ip or not config.trusted_proxies:
        return False

    try:
        peer = ip_address(peer_ip)
    except ValueError:
        return False

    for raw_proxy in config.trusted_proxies:
        try:
            if "/" in raw_proxy:
                if peer in ip_network(raw_proxy, strict=False):
                    return True
            elif peer == ip_address(raw_proxy):
                return True
        except ValueError:
            continue
    return False
