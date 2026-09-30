"""Public-address-only transport, including DNS and redirect checks."""
import asyncio
import ipaddress
import socket
import time
from urllib.parse import urlsplit, urljoin
import httpx
from app.core.config import settings
from .url_discovery import normalize_url, same_site


async def public_addresses(url):
    p = urlsplit(normalize_url(url))
    records = await asyncio.get_running_loop().getaddrinfo(p.hostname, p.port or (443 if p.scheme == "https" else 80), type=socket.SOCK_STREAM)
    addresses = sorted({r[4][0] for r in records})
    if not addresses or any(not ipaddress.ip_address(ip).is_global for ip in addresses):
        raise ValueError("Private, reserved or local addresses are prohibited")
    return addresses


class SafeTransport:
    def __init__(self):
        self.last = {}
        self.delay = max(settings.REQUEST_DELAY, .1)

    async def get(self, url, boundary=None, redirect_check=None):
        for _ in range(6):
            url = normalize_url(url)
            if boundary and not same_site(url, boundary):
                raise ValueError("Redirect left the crawl domain")
            p = urlsplit(url)
            addresses = await public_addresses(url)
            # Pin the connection to the checked IP; preserve HTTP host and TLS SNI.
            ip = addresses[0]
            host = f"[{ip}]" if ":" in ip else ip
            request_url = httpx.URL(url).copy_with(host=host.strip("[]"))
            response = None
            for attempt in range(settings.MAX_RETRIES + 1):
                wait = self.delay - (time.monotonic() - self.last.get(p.hostname, 0))
                if wait > 0: await asyncio.sleep(wait)
                self.last[p.hostname] = time.monotonic()
                try:
                    async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT, trust_env=False) as client:
                        async with client.stream("GET", request_url, headers={"Host": p.netloc, "User-Agent": settings.CRAWLER_USER_AGENT},
                                                 extensions={"sni_hostname": p.hostname.encode()}) as r:
                            chunks = bytearray()
                            async for chunk in r.aiter_bytes():
                                chunks.extend(chunk)
                                if len(chunks) > settings.MAX_RESPONSE_BYTES:
                                    raise ValueError("Response exceeds byte limit")
                            headers = {k:v for k,v in r.headers.items() if k.lower() not in {"content-encoding", "content-length", "transfer-encoding"}}
                            response = httpx.Response(r.status_code, headers=headers, content=bytes(chunks), request=httpx.Request("GET", url))
                    if response.status_code not in (429, 500, 502, 503, 504): break
                except httpx.TransportError:
                    if attempt == settings.MAX_RETRIES: raise
                await asyncio.sleep(min(2 ** attempt, 8))
            if response is None: raise ValueError("No HTTP response")
            if response.is_redirect:
                url = urljoin(url, response.headers.get("location", ""))
                if redirect_check and not await redirect_check(url):
                    raise ValueError("Redirect disallowed by robots.txt")
                continue
            return response
        raise ValueError("Too many redirects")
