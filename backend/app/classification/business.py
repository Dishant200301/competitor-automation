import re
from app.classification.taxonomy import INDUSTRY_TAXONOMY
from app.evidence.registry import record
from app.crawler.url_discovery import domain


def classify(pages, registry):
    if not pages: raise ValueError("Cannot classify a website with no crawled pages")
    text = " ".join(p["main_text"] for p in pages).lower()
    matches = {industry: [word for word in config["keywords"] if re.search(r"\b" + re.escape(word) + r"\b", text)] for industry,config in INDUSTRY_TAXONOMY.items()}
    industry = max(matches, key=lambda k: len(matches[k]))
    if len(matches[industry]) < 3: industry = "Not verified"
    commerce = any(p.get("commerce_signals") for p in pages)
    product_offers = any(s.get("@type") == "Product" and s.get("offers") for p in pages for s in p.get("structured_data", []))
    model = "E-commerce" if commerce or product_offers else "Not verified"
    for pattern, label in [(r"\bsoftware as a service\b|\bsaas\b", "SaaS"), (r"\bmanufactur(?:er|ing)\b", "Manufacturing"),
                           (r"\bagency\b", "Agency"), (r"\bmarketplace\b|\bmulti-brand\b", "Marketplace")]:
        if re.search(pattern, text): model = label; break
    if model == "Not verified" and any(p.get("page_type") == "SERVICE" for p in pages): model = "Service business"
    audience = [t for t in ("women", "men", "children", "developers", "businesses", "students", "patients", "retailers") if re.search(r"\b" + t + r"\b", text)]
    markets = [c for c in ("India", "United States", "United Kingdom", "Canada", "Australia", "UAE") if re.search(
        r"\b(?:shipping|delivery|deliver|serving|available|customers|across|pan)[^.!?]{0,50}\b" + c.lower() + r"\b", text)]
    home = pages[0]
    name = None
    for s in home.get("structured_data", []):
        if s.get("@type") in ("Organization", "Store", "ClothingStore", "OnlineStore") and s.get("name"):
            name = s["name"]; break
    values = {"company_name": name or home["title"] or "Not verified", "website": home["url"], "domain": domain(home["url"]),
              "description": home["meta_description"] or "Not found", "industry": industry,
              "sub_industry": ", ".join(matches.get(industry, [])[:5]) or "Not verified", "business_model": model,
              "target_audience": audience or "Not verified", "geographic_market": markets or "Not verified",
              "has_ecommerce_signals": commerce or product_offers, "classification_method": "Rule-based inference from observed site signals"}
    result = record(values, home, registry, "site_signal_inference", home["main_text"][:2000])
    # Each inferred field references the pages that actually contain its supporting signals.
    for field, terms in [("industry", matches.get(industry, [])), ("target_audience", audience), ("geographic_market", markets),
                         ("business_model", [model.lower(), "add to cart", "shopify", "woocommerce"])]:
        result["field_evidence"].pop(field, None)
        for page in pages:
            found = [t for t in terms if t.lower() in page["main_text"].lower() or t.lower() in page.get("commerce_signals", [])]
            if found:
                eid = registry.claim(page, field, values[field], "; ".join(found), "site_signal_inference", .75)
                result["evidence_ids"].append(eid)
                result["field_evidence"][field] = eid
        if field == "business_model" and model == "E-commerce" and product_offers:
            page = next(p for p in pages if any(s.get("@type") == "Product" and s.get("offers") for s in p["structured_data"]))
            eid = registry.claim(page, field, model, "Product schema with offers", "schema_inference", .9)
            result["field_evidence"][field] = eid
            result["evidence_ids"].append(eid)
    return result
