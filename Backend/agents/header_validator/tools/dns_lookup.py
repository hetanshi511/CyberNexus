import aiodns
import socket
import ipaddress
import logging

logger = logging.getLogger("header_validator.dns_lookup")

def is_private_ip(ip: str) -> bool:
    try:
        return ipaddress.ip_address(ip).is_private
    except ValueError:
        return False

async def resolve_domain(domain: str) -> str:
    """
    Asynchronously resolves a domain name to its primary IP address.
    Raises ValueError if a private/internal IP is detected (SSRF protection).
    """
    try:
        resolver = aiodns.DNSResolver()
        result = await resolver.gethostbyname(domain, socket.AF_INET)
        ip_address = result.addresses[0] if result.addresses else "Unknown"
        
        if is_private_ip(ip_address):
            raise ValueError(f"SSRF Protection blocked resolution of private IP: {ip_address}")
            
        return ip_address
    except ValueError as e:
        logger.warning(str(e))
        raise e
    except Exception as e:
        logger.error(f"Failed to resolve domain {domain}: {e}")
        return "Unknown"
