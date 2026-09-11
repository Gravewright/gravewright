"""Only accept forwarding headers from explicitly trusted proxy networks."""
from ipaddress import ip_address, ip_network
from django.conf import settings


def client_ip(request):
    peer = request.META.get('REMOTE_ADDR', '')
    networks = [ip_network(value, strict=False) for value in settings.TRUSTED_PROXIES]
    def trusted(value):
        address = ip_address(value)
        return any(address in network for network in networks)
    try:
        if not trusted(peer):
            return peer
        chain = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')
        for value in reversed(chain):
            value = value.strip()
            if not value:
                return peer
            if not trusted(value):
                return str(ip_address(value))
        return str(ip_address(chain[0].strip()))
    except ValueError:
        return peer
