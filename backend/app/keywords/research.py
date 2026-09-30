import re
from collections import Counter
from app.evidence.registry import record

UNAVAILABLE = "Not available from verified source"


def intent(term):
    t = term.lower()
    if re.search(r"\b(near me|nearby)\b", t): return "Local", "Purchase intent"
    if re.search(r"\b(vs|compare|comparison|best|alternatives?)\b", t): return "Commercial Investigation", "Comparison intent"
    if re.search(r"\b(how|what|why|guide|tutorial)\b", t): return "Informational", "Problem intent"
    if re.search(r"\b(buy|shop|order|price)\b", t): return "Transactional", "Purchase intent"
    return "Commercial Investigation", "Category intent"


NAV_STOP = {
    "home", "all", "shop", "sale", "new", "cart", "contact", "about", "about us",
    "faq", "faqs", "help", "terms", "privacy", "privacy policy", "track order",
    "view all", "all products", "new arrivals", "best seller", "best sellers",
    "ready to ship", "under 999", "under 1499", "under 1999", "plus size",
    "collection", "collections", "order", "login", "register", "checkout"
}


def research_keywords(pages, catalog, company, registry):
    keywords, seen = [], set()
    by_url = {p["url"]: p for p in pages}
    terms = []
    # 1. Meaningful categories
    for c in catalog.get("categories", []):
        cname = c.get("category_name", "").strip()
        if cname and cname.lower() not in NAV_STOP and len(cname) >= 3:
            terms.append((cname, c["source_url"], "category"))
    # 2. Real product names
    for p in catalog.get("products", [])[:25]:
        pname = p.get("product_name", "").strip()
        if pname and pname.lower() not in NAV_STOP and len(pname) >= 3:
            terms.append((pname, p.get("source_url") or pages[0]["url"], "product"))
    # 3. Services
    for s in catalog.get("services", []):
        sname = s.get("service_name", "").strip()
        if sname and sname.lower() not in NAV_STOP:
            terms.append((sname, s.get("source_url") or pages[0]["url"], "service"))
    if not terms:
        for p in pages:
            for h in p.get("h1", []) + p.get("h2", []):
                hname = (h or "").strip()
                if hname and hname.lower() not in NAV_STOP and len(hname) >= 4:
                    terms.append((hname, p["url"], "heading"))
    for phrase, source, kind in terms:
        phrase = " ".join(phrase.lower().split())
        if phrase in seen or not 3 <= len(phrase) <= 100: continue
        seen.add(phrase)
        search_intent, subtype = intent(phrase)
        p = by_url[source]
        item = record({"keyword": phrase, "cluster": phrase, "intent": search_intent, "intent_type": subtype,
                       "country": "Not verified", "language": p.get("language", "Not found"),
                       "source": "Website-derived search hypothesis", "search_volume": None, "cpc": None,
                       "competition": None, "serp_features": None, "target_ranking": None, "competitor_ranking": None,
                       "volume_source": None, "metrics_status": UNAVAILABLE}, p, registry, "phrase_and_intent_inference", phrase)
        keywords.append(item)
    counts = Counter(re.findall(r"\b[a-z][a-z-]{3,}\b", " ".join(p["main_text"] for p in pages).lower()))
    return {"keywords": keywords[:60], "website_terms": [{"term":t, "occurrences":n} for t,n in counts.most_common(50)],
            "keyword_clusters": [{"cluster":k["cluster"], "keywords":[k["keyword"]], "evidence_ids":k["evidence_ids"]} for k in keywords[:60]]}
