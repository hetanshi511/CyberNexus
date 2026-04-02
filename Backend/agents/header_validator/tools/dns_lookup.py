"""
dns_lookup.py — Async DNS resolution with SSRF protection.

Uses aiodns if available (Linux/Docker). Falls back to Python's built-in
socket module on platforms where aiodns cannot be installed (e.g. Windows).
"""
import socket
import ipaddress
import asyncio
import logging

logger = logging.getLogger("header_validator.dns_lookup")

# ── Try to import aiodns; if missing, mark unavailable ───────────────────────
try:
    import aiodns
    _AIODNS_AVAILABLE = True
except ImportError:
    _AIODNS_AVAILABLE = False
    logger.info(
        "aiodns is not installed — DNS resolution will use the socket fallback. "
        "This is expected on Windows. Install aiodns on Linux for better performance."
    )


def is_private_ip(ip: str) -> bool:
    try:
        return ipaddress.ip_address(ip).is_private
    except ValueError:
        return False


async def resolve_domain(domain: str) -> str:
    """
    Asynchronously resolves a domain name to its primary IP address.
    Raises ValueError if a private/internal IP is detected (SSRF protection).

    Uses aiodns when available; falls back to socket.gethostbyname() otherwise.
    """
    if _AIODNS_AVAILABLE:
        # ── aiodns path (Linux / Docker) ──────────────────────────────────────
        try:
            resolver = aiodns.DNSResolver()
            result = await resolver.gethostbyname(domain, socket.AF_INET)
            ip_address = result.addresses[0] if result.addresses else "Unknown"

            if is_private_ip(ip_address):
                raise ValueError(f"SSRF Protection blocked resolution of private IP: {ip_address}")

            return ip_address
        except ValueError:
            raise
        except Exception as e:
            logger.error("aiodns failed to resolve %s: %s", domain, e)
            return "Unknown"
    else:
        # ── socket fallback path (Windows / no aiodns) ────────────────────────
        try:
            loop = asyncio.get_event_loop()
            ip_address = await loop.run_in_executor(None, socket.gethostbyname, domain)

            if is_private_ip(ip_address):
                raise ValueError(f"SSRF Protection blocked resolution of private IP: {ip_address}")

            return ip_address
        except ValueError:
            raise
        except Exception as e:
            logger.error("socket DNS fallback failed to resolve %s: %s", domain, e)
            return "Unknown"
