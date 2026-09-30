from urllib.parse import urljoin
from lxml import etree
from .url_discovery import same_site, normalize_url


async def discover_sitemaps(start, transport, robots, limit=5000):
    policy = await robots.load(start)
    queue = list(policy.site_maps() or []) + [urljoin(start, "/sitemap.xml"), urljoin(start, "/sitemap_index.xml")]
    seen, urls, records = set(), [], []
    while queue and len(seen) < 20 and len(urls) < limit:
        url = queue.pop(0)
        if url in seen or not same_site(url, start): continue
        seen.add(url)
        if not await robots.can_fetch(url): continue
        try:
            r = await transport.get(url, boundary=start, redirect_check=robots.can_fetch)
            if r.status_code != 200: continue
            root = etree.fromstring(r.content, etree.XMLParser(resolve_entities=False, no_network=True))
            if etree.QName(root).localname not in {"sitemapindex", "urlset"}: continue
            locs = root.xpath('//*[local-name()="loc"]/text()')
            records.append({"url": url, "status": r.status_code, "entries": len(locs)})
            for loc in locs:
                try: loc = normalize_url(loc)
                except ValueError: continue
                if not same_site(loc, start): continue
                if etree.QName(root).localname == "sitemapindex": queue.append(loc)
                elif loc not in urls: urls.append(loc)
                if len(urls) >= limit: break
        except (ValueError, etree.XMLSyntaxError, OSError):
            continue
    return urls, records
