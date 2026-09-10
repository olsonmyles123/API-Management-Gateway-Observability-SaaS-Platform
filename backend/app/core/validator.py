import ipaddress
import socket
import logging
from urllib.parse import urlparse
from app.config import settings

logger = logging.getLogger("gateway.validator")

# High-risk internal ports that should never be proxied or called by webhooks
BLOCKED_PORTS = {
    22,    # SSH
    25,    # SMTP
    111,   # Portmapper
    6379,  # Redis default
    6380,  # Redis TLS
    9000,  # ClickHouse native
    9009,  # ClickHouse interserver
    11211, # Memcached
    27017, # MongoDB
    5432,  # PostgreSQL
    3306,  # MySQL
}

# Cloud metadata IP range (AWS, GCP, Azure, DigitalOcean, OpenStack)
METADATA_NETWORK = ipaddress.ip_network("169.254.0.0/16")
IPV6_LINK_LOCAL = ipaddress.ip_network("fe80::/10")


def validate_safe_url(url: str, allow_localhost: bool = True) -> str:
    """
    Validates that a URL is safe from SSRF (Server-Side Request Forgery).

    Checks:
    - Scheme must be http or https
    - Hostname must be present and valid
    - Disallows link-local and cloud metadata addresses (169.254.169.254)
    - Disallows dangerous infrastructure service ports (e.g. 6379, 5432)
    - In production, rejects RFC-1918 private subnets and localhost
    """
    if not url or not isinstance(url, str):
        raise ValueError("URL must be a non-empty string.")

    url = url.strip()
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Invalid URL scheme '{parsed.scheme}'. Only 'http' and 'https' are allowed.")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL must contain a valid hostname.")

    # Check dangerous ports
    port = parsed.port
    if port and port in BLOCKED_PORTS:
        raise ValueError(f"Port {port} is restricted for security reasons.")

    # Resolve IP address to detect internal / link-local / metadata targeting
    try:
        # Check if hostname is directly an IP address
        try:
            ip = ipaddress.ip_address(hostname)
        except ValueError:
            # Resolve DNS
            addr_info = socket.getaddrinfo(hostname, None)
            if not addr_info:
                raise ValueError(f"Could not resolve hostname: {hostname}")
            ip_str = addr_info[0][4][0]
            ip = ipaddress.ip_address(ip_str)

        # 1. Always reject Cloud Metadata service (169.254.169.254)
        if ip in METADATA_NETWORK or ip in IPV6_LINK_LOCAL:
            raise ValueError("Targeting cloud metadata or link-local addresses is strictly prohibited.")

        # 2. Check loopback & private networks
        is_prod = (settings.ENVIRONMENT == "production")
        if is_prod or not allow_localhost:
            if ip.is_loopback:
                raise ValueError("Targeting localhost/loopback addresses is not permitted in this environment.")
            if ip.is_private:
                raise ValueError("Targeting internal private network addresses (RFC 1918) is prohibited.")

        # 3. Reject multicast / reserved (excluding loopback addresses)
        if ip.is_multicast or (ip.is_reserved and not ip.is_loopback):
            raise ValueError("Targeting multicast or reserved network addresses is prohibited.")

    except socket.gaierror as e:
        logger.warning(f"DNS resolution failed for '{hostname}': {e}")
        # Allow unresolved domain in test/dev if valid syntax, but not in prod
        if settings.ENVIRONMENT == "production":
            raise ValueError(f"Cannot resolve host '{hostname}'.")

    return url
