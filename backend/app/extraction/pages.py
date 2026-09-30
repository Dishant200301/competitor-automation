import hashlib
from datetime import datetime, timezone
from urllib.parse import urljoin, urlsplit
from bs4 import BeautifulSoup
import extruct
from app.crawler.novacrawl_adapter import extract_metadata
from app.crawler.url_discovery import normalize_url, same_site


def now(): return datetime.now(timezone.utc).isoformat()


def nodes(value):
    if isinstance(value, list):
        for item in value: yield from nodes(item)
    elif isinstance(value, dict):
        if "@type" in value: yield value
        for v in value.values():
            if isinstance(v, (dict, list)): yield from nodes(v)


def extract_page(html, url, status=200):
    metadata = extract_metadata(html, url)
    soup = BeautifulSoup(html, "lxml")
    links = []
    seen = set()
    for a in soup.select("a[href]"):
        if a["href"].startswith(("#", "mailto:", "tel:", "javascript:")): continue
        try: href = normalize_url(a["href"], url)
        except ValueError: continue
        if href in seen: continue
        seen.add(href)
        links.append({"url": href, "text": a.get_text(" ", strip=True), "navigation": bool(a.find_parent("nav"))})
    schema = list(nodes(metadata["json_ld"]))
    try:
        extracted = extruct.extract(html, base_url=url, syntaxes=["json-ld", "microdata"], uniform=True)
        schema = list(nodes(extracted.get("json-ld", []))) or schema
        schema.extend(nodes(extracted.get("microdata", [])))
    except (ValueError, TypeError): pass
    commerce = [x for x in ("add to cart", "add to bag", "woocommerce", "shopify") if x in html.lower()]
    product_meta = {tag.get('property') or tag.get('name'):tag.get('content') for tag in soup.select('meta[content]')
                    if (tag.get('property') or tag.get('name') or '').startswith(('product:', 'og:price', 'og:type'))}
    for element in soup(["script", "style", "noscript", "svg", "iframe"]): element.decompose()
    text = " ".join(soup.get_text(" ", strip=True).split())
    path = urlsplit(url).path.lower()
    page_type = "HOME" if path == "/" else "PAGE"
    for token, kind in [("/products/", "PRODUCT"), ("/product/", "PRODUCT"), ("/collections/", "COLLECTION"), ("/category/", "COLLECTION"), ("/services/", "SERVICE"), ("/pricing", "PRICING"), ("/blog", "BLOG")]:
        if token in path: page_type = kind; break
    return {"url": url, "final_url": url, "http_status": status, "title": metadata["title"],
            "meta_description": metadata["meta_description"], "h1": metadata["h1_list"],
            "h2": metadata["h2"], "h3": metadata["h3"], "main_text": text,
            "canonical_url": urljoin(url, metadata["canonical_url"]) if metadata["canonical_url"] else None,
            "language": metadata["lang"] or "Not found", "structured_data": schema,
            "links": links, "internal_links": [x["url"] for x in links if same_site(url, x["url"])],
            "external_links": [x["url"] for x in links if not same_site(url, x["url"])],
            "commerce_signals": commerce, "page_type": page_type,
            "product_meta": product_meta,
            "indexable": "noindex" not in metadata["robots"].lower(), "date_checked": now(),
            "content_hash": hashlib.sha256(html.encode()).hexdigest(), "word_count": len(text.split())}
