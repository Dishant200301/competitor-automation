import json
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit, urljoin
from app.evidence.registry import record, UNKNOWN
from app.crawler.url_discovery import normalize_url, same_site


def money(value):
    try:
        n = Decimal(str(value).replace(",", ""))
        return str(n) if n.is_finite() and n >= 0 else None
    except (InvalidOperation, TypeError): return None


def extract_catalog(pages, registry):
    products, categories, services = [], [], []
    seen_products, seen_cats = set(), set()
    by_url = {p["url"]:p for p in pages}
    for page in pages:
        for link in page.get("links", []):
            path = urlsplit(link["url"]).path
            if urlsplit(link["url"]).query: continue
            if not same_site(link["url"], page["url"]) or not any(t in path for t in ("/collections/", "/category/", "/product-category/")) or "/products/" in path: continue
            url = normalize_url(link["url"])
            if url in seen_cats or not link["text"]: continue
            seen_cats.add(url)
            cat_page = by_url.get(url)
            values = {"category_name": link["text"], "url": url, "product_count": None, "example_products": [],
                      "description": UNKNOWN, "seo_title": UNKNOWN, "meta_description": UNKNOWN, "h1": UNKNOWN}
            if cat_page:
                values.update(description=cat_page["meta_description"] or UNKNOWN, seo_title=cat_page["title"],
                              meta_description=cat_page["meta_description"] or UNKNOWN, h1=cat_page["h1"] or UNKNOWN)
            categories.append(record(values, cat_page or page, registry, "navigation_link", link["text"]))
        for item in page.get("structured_data", []):
            types = item.get("@type", [])
            types = [types] if isinstance(types, str) else types
            if "Service" in types and item.get("name"):
                services.append(record({"service_name": item["name"], "url": item.get("url", page["url"]),
                    "description": item.get("description", UNKNOWN), "category": item.get("serviceType", UNKNOWN)}, page, registry, excerpt=json.dumps(item)))
            if "Product" not in types or not item.get("name"): continue
            offers = item.get("offers") or {}
            offers = offers if isinstance(offers, list) else [offers]
            offer = next((x for x in offers if isinstance(x, dict)), {})
            url = urljoin(page["url"], item.get("url") or offer.get("url") or page["url"])
            key = (url, str(item.get("sku", item["name"])))
            if key in seen_products: continue
            seen_products.add(key)
            brand = item.get("brand", UNKNOWN)
            brand = brand.get("name", UNKNOWN) if isinstance(brand, dict) else brand
            rating = item.get("aggregateRating") or {}
            values = {"product_name": item["name"], "product_url": url, "category": item.get("category", UNKNOWN),
                      "collection": UNKNOWN, "description": item.get("description", UNKNOWN), "price": money(offer.get("price")),
                      "sale_price": None, "currency": offer.get("priceCurrency", UNKNOWN), "sku": item.get("sku", UNKNOWN),
                      "product_id": item.get("productID", UNKNOWN), "availability": offer.get("availability", UNKNOWN),
                      "variants": item.get("hasVariant", []), "offers": offers, "images": item.get("image", []),
                      "rating": rating.get("ratingValue"), "review_count": rating.get("reviewCount"), "brand": brand,
                      "attributes": item.get("additionalProperty", []), "breadcrumbs": [s for s in page["structured_data"] if s.get("@type") == "BreadcrumbList"],
                      "product_schema": item}
            products.append(record(values, page, registry, excerpt=json.dumps(item, ensure_ascii=False)))
        meta = page.get('product_meta', {})
        if page.get('h1') and (page.get('page_type') == 'PRODUCT' or meta.get('og:type') == 'product') and page.get('commerce_signals') and not any(p['source_url'] == page['url'] for p in products):
            values = {'product_name':page['h1'][0], 'product_url':page['url'], 'category':UNKNOWN, 'collection':UNKNOWN,
                      'description':page.get('meta_description') or UNKNOWN,
                      'price':money(meta.get('product:price:amount') or meta.get('og:price:amount')),
                      'currency':meta.get('product:price:currency') or meta.get('og:price:currency') or UNKNOWN,
                      'sale_price':money(meta.get('product:sale_price:amount')), 'availability':meta.get('product:availability',UNKNOWN),
                      'sku':UNKNOWN,'product_id':UNKNOWN,'variants':[],'images':[],'rating':None,'review_count':None,'brand':UNKNOWN,
                      'attributes':[],'breadcrumbs':[],'product_schema':{}}
            products.append(record(values,page,registry,'product_page_heading_and_meta', page['h1'][0] + ' ' + json.dumps(meta)))
        if page.get("page_type") == "SERVICE" and page.get("h1") and not any(s["source_url"] == page["url"] for s in services):
            services.append(record({"service_name": page["h1"][0], "url": page["url"], "description": page["meta_description"] or UNKNOWN}, page, registry, "service_page_heading", page["main_text"][:1000]))
    # A collection heading is never an individual product. Missing products cause validation failure.
    ranges = {}
    for product in products:
        if product["price"] is not None and product["currency"] != UNKNOWN:
            ranges.setdefault(product["currency"], []).append(Decimal(product["price"]))
    summary = "; ".join(f"Sampled product prices ranged from {c} {min(p)} to {max(p)} ({len(p)} products)" for c,p in ranges.items()) or "Not publicly disclosed"
    return {"products": products, "categories": categories, "services": services, "price_range_summary": summary}
