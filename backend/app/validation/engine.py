from app.keywords.research import UNAVAILABLE


def validate(dataset):
    failures, warnings = [], []
    pages, company = dataset["pages"], dataset["company"]
    if not pages: failures.append("No target pages were crawled")
    if company["industry"] == "Not verified": warnings.append("Industry could not be verified")
    if company["industry"] == "Technology & Software" and company["has_ecommerce_signals"]:
        fashion = sum(x in " ".join(p["main_text"].lower() for p in pages) for x in ("kurta", "anarkali", "sharara", "lehenga", "kaftan"))
        if fashion >= 3: failures.append("Software classification contradicts fashion commerce evidence")
    product_links = any("/products/" in u or "/product/" in u for p in pages for u in p["internal_links"])
    if not dataset["products"] and (product_links or (company["has_ecommerce_signals"] and dataset["categories"])):
        failures.append("Product/catalog pages exist but no individual products were extracted")
    sources = {s["id"]:s for s in dataset["sources"]}
    evidence = {e["id"]:e for e in dataset["evidence"]}
    for e in evidence.values():
        s = sources.get(e["source_id"])
        if not s or s["verification_status"] != "verified" or not e["evidence_text"]:
            failures.append("Unavailable or empty evidence: " + e["id"])
    for entity in [company] + sum([dataset[k] for k in ("products", "categories", "services", "keywords", "competitors", "social_profiles")], []):
        if not entity.get("evidence_ids") or any(eid not in evidence for eid in entity["evidence_ids"]):
            failures.append("Entity missing evidence: " + str(entity.get("id")))
        for field, eid in entity.get("field_evidence", {}).items():
            if eid not in evidence or evidence[eid]["value"] != entity.get(field): failures.append("Field evidence mismatch: " + field)
    for keyword in dataset["keywords"]:
        if keyword.get("search_volume") is not None and not keyword.get("volume_source"):
            failures.append("Keyword volume lacks verified source")
    for competitor in dataset["competitors"]:
        checks = competitor["verification"]
        if not checks["website_active"] or not checks["product_match"] or not checks["industry_match"]:
            failures.append("Competitor lacks independently verified overlap")
        if competitor["competitor_type"] == "DIRECT" and not all(checks[k] for k in ("audience_match", "geography_match", "business_model_match")):
            failures.append("DIRECT classification lacks required overlap")
    if not dataset["competitors"]: warnings.append("No independently verified competitors; this is not evidence of no competition")
    warnings += ["Crawl is a bounded sample, not a complete catalog", "Search phrases and intent are inferred; demand and rankings are not measured", UNAVAILABLE]
    return {"passed": not failures, "failures":sorted(set(failures)), "warnings":sorted(set(warnings)), "checks_count": 8}


def validated_projection(dataset):
    """Only evidence-linked entity fields can reach report templates."""
    def project(entity):
        allowed = entity.get("field_evidence", {})
        return {k:v for k,v in entity.items() if k in allowed or k in {"source_url", "date_checked", "evidence_ids", "field_evidence"}}
    result = dict(dataset)
    result["company"] = project(dataset["company"])
    for key in ("products", "categories", "services", "keywords", "competitors", "social_profiles"):
        result[key] = [project(x) for x in dataset[key]]
    return result
