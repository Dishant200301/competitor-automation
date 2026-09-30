import re
import asyncio
from app.core.config import settings
from app.crawler.url_discovery import domain, normalize_url
from app.crawler.crawl_manager import WebCrawler
from app.classification.business import classify
from app.extraction.catalog import extract_catalog
from app.evidence.registry import record
from .providers import get_provider

STOP = {"the", "and", "for", "with", "online", "shop", "buy", "new", "all", "collection", "collections", "sale", "home", "our", "your", "set", "sets"}
STOP |= {"red", "blue", "green", "yellow", "purple", "wine", "pink", "black", "white", "cotton", "silk", "wear", "festive", "designer", "premium", "piece", "pieces", "wedding"}


def tokens(terms):
    return {w[:-1] if w.endswith("s") and not w.endswith("ss") else w for w in re.findall(r"[a-z]{3,}", " ".join(terms).lower()) if w not in STOP}


def queries_for(company, catalog, keywords):
    queries = []
    audience = company.get('target_audience')
    market = company.get('geographic_market')
    context = ' '.join((audience[:2] if isinstance(audience, list) else []) + (market[:1] if isinstance(market, list) else []))
    for cat in catalog["categories"]:
        name = cat["category_name"]
        if any(x in name.lower() for x in ("ready to ship", "new in", "explore all", "under ", "sale", "plus size")): continue
        if tokens([name]): queries.append(("category_similarity", name + " " + context + " online store"))
        if len(queries) >= 2: break
    for product in catalog["products"][:2]: queries.append(("product_alternatives", product["product_name"] + " alternatives"))
    for service in catalog["services"][:2]: queries.append(("service_similarity", service["service_name"] + " providers"))
    for keyword in keywords[:3]: queries.append(("search_intent_overlap", keyword["keyword"]))
    markets = company.get("geographic_market")
    if isinstance(markets, list) and queries: queries.append(("geographic_overlap", queries[0][1] + " " + markets[0]))
    return list(dict.fromkeys(queries))[:settings.MAX_SEARCH_QUERIES]


NON_COMPETITOR_DOMAINS = {
    "instagram.com", "facebook.com", "youtube.com", "linkedin.com", "pinterest.com",
    "twitter.com", "x.com", "tiktok.com", "wikipedia.org", "reddit.com", "quora.com",
    "medium.com", "amazon.com", "amazon.in", "flipkart.com", "ebay.com", "trustpilot.com",
    "justdial.com", "indiamart.com", "yelp.com", "yellowpages.com", "github.com",
    "google.com", "play.google.com", "apps.apple.com", "shopify.com", "wordpress.com",
    "blogspot.com", "wix.com", "cloudflare.com"
}


async def discover(company, catalog, keywords, provider=None):
    provider = provider or get_provider()
    queries = queries_for(company, catalog, keywords)
    candidates, errors, seen = [], [], {company["domain"]}
    for strategy, query in queries:
        try:
            for result in await provider.search(query):
                try: url = normalize_url(result["url"])
                except ValueError: continue
                host = domain(url)
                if not host or host in seen or any(host == d or host.endswith("." + d) for d in NON_COMPETITOR_DOMAINS):
                    continue
                seen.add(host)
                candidates.append({"url": url, "domain": host, "discovery_query": query, "discovery_strategy": strategy, "search_result": result})
        except Exception as exc:
            errors.append({"stage":"search", "query":query, "error":type(exc).__name__})
    return candidates[:settings.MAX_CANDIDATES], queries, errors


def assess(target, target_catalog, candidate, catalog, pages):
    target_terms = tokens([p["product_name"] for p in target_catalog["products"]] + [c["category_name"] for c in target_catalog["categories"]] + [s["service_name"] for s in target_catalog["services"]])
    candidate_terms = tokens([p["product_name"] for p in catalog["products"]] + [s["service_name"] for s in catalog["services"]])
    overlap = sorted(target_terms & candidate_terms)
    industry = target["industry"] != "Not verified" and target["industry"] == candidate["industry"]
    audience = isinstance(target["target_audience"], list) and isinstance(candidate["target_audience"], list) and bool(set(target["target_audience"]) & set(candidate["target_audience"]))
    geography = isinstance(target["geographic_market"], list) and isinstance(candidate["geographic_market"], list) and bool(set(target["geographic_market"]) & set(candidate["geographic_market"]))
    model = target["business_model"] != "Not verified" and target["business_model"] == candidate["business_model"]
    category_phrases = [tokens([c['category_name']]) for c in target_catalog['categories']]
    offering_phrases = [tokens([p['product_name']]) for p in catalog['products']] + [tokens([s['service_name']]) for s in catalog['services']]
    phrase_overlap = any(term and term <= offering for term in category_phrases for offering in offering_phrases)
    product = len(overlap) >= 2 or (len(overlap) >= 1 and phrase_overlap)
    qualification = "NOT QUALIFIED"
    audience_conflict = isinstance(target['target_audience'], list) and isinstance(candidate['target_audience'], list) and not audience
    if pages and industry and product and not audience_conflict:
        if candidate["business_model"] == "Marketplace": qualification = "MARKETPLACE / SEARCH"
        elif audience and geography and model: qualification = "DIRECT"
        else: qualification = "ADJACENT"
    return {"industry_match":industry, "product_match":product, "audience_match":bool(audience),
            "geography_match":bool(geography), "business_model_match":model, "search_intent_match":product and model,
            "relevant_products_found":bool(catalog["products"] or catalog["services"]), "website_active":bool(pages),
            "overlap_terms":overlap, "verification_status":qualification,
            "pricing_overlap":"Not verified", "reason": "Observed offering overlap: " + ", ".join(overlap) if qualification != "NOT QUALIFIED" else "Insufficient independently crawled industry and offering overlap"}


async def verify(candidates, company, catalog, registry, run_id):
    verified, matrix, pages_all, raw_all, errors = [], [], [], [], []
    for candidate in candidates:
        crawler = WebCrawler(run_id=run_id, max_pages=5)
        try:
            pages = await asyncio.wait_for(crawler.crawl_site("https://" + candidate["domain"] + "/", seed_urls=[candidate["url"]]), timeout=settings.COMPETITOR_CRAWL_TIMEOUT)
        except TimeoutError:
            pages = crawler.pages
            crawler.errors.append({'url':candidate['url'], 'error':'Competitor crawl time budget exhausted; partial evidence only'})
        pages_all.extend(pages); raw_all.extend(crawler.raw_records); errors.extend(crawler.errors)
        if not pages:
            matrix.append({**candidate, "verification_status":"NOT QUALIFIED", "website_active":False, "reason":"Website unavailable or robots disallowed verification", "evidence_urls":[]})
            continue
        profile = classify(pages, registry)
        offerings = extract_catalog(pages, registry)
        checks = assess(company, catalog, profile, offerings, pages)
        matrix.append({**candidate, **checks, "evidence_urls":[p["url"] for p in pages]})
        if checks["verification_status"] == "NOT QUALIFIED": continue
        item = record({"competitor_name":profile["company_name"], "website":profile["website"], "domain":candidate["domain"],
                       "competitor_type":checks["verification_status"], "reason":checks["reason"],
                       "description":profile["description"], "products":[p["product_name"] for p in offerings["products"]],
                       "pricing_model":offerings["price_range_summary"], "verification":checks,
                       "evidence_urls":[p["url"] for p in pages]}, pages[0], registry, "cross_site_comparison", str(checks))
        item["comparison_evidence_ids"] = company["evidence_ids"] + profile["evidence_ids"] + [eid for p in offerings["products"] + offerings["services"] for eid in p["evidence_ids"]]
        item["product_records"] = offerings["products"]
        verified.append(item)
    return verified, matrix, pages_all, raw_all, errors
