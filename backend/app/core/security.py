from urllib.parse import urlparse
import ipaddress
from typing import Tuple

BLOCKED_DOMAINS = {
    "localhost", "127.0.0.1", "0.0.0.0", "internal", "local", "intranet", "corp"
}

def is_safe_url(url: str) -> Tuple[bool, str]:
    if not url:
        return False, "URL is empty"
    
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False, f"Unsupported scheme: {parsed.scheme}"
    
    hostname = parsed.hostname
    if not hostname:
        return False, "Invalid hostname in URL"
        
    hostname_lower = hostname.lower()
    if hostname_lower in BLOCKED_DOMAINS or hostname_lower.endswith(".local") or hostname_lower.endswith(".internal"):
        return False, "Access to private or local network is blocked"
        
    try:
        ip = ipaddress.ip_address(hostname_lower)
        if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local:
            return False, "Access to private IP addresses is blocked (SSRF prevention)"
    except ValueError:
        pass

    return True, ""
