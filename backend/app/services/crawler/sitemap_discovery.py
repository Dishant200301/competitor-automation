from typing import List
from urllib.parse import urljoin
import xml.etree.ElementTree as ET
import httpx
from app.utils.logger import logger

async def discover_sitemap_urls(base_url: str, limit: int = 15) -> List[str]:
    urls = []
    candidates = [
        urljoin(base_url, "/sitemap.xml"),
        urljoin(base_url, "/sitemap_index.xml"),
    ]
    async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
        for sitemap_url in candidates:
            try:
                res = await client.get(sitemap_url)
                if res.status_code == 200 and ("xml" in res.headers.get("content-type", "") or res.text.strip().startswith("<?xml")):
                    root = ET.fromstring(res.content)
                    for elem in root.iter():
                        if elem.tag.endswith("loc") and elem.text:
                            loc = elem.text.strip()
                            if loc.startswith("http"):
                                urls.append(loc)
                                if len(urls) >= limit:
                                    return urls
            except Exception as e:
                logger.debug(f"Sitemap fetch failed for {sitemap_url}: {e}")
    return urls
