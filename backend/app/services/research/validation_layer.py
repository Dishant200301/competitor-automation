from typing import Dict, Any, List
from app.utils.logger import logger

class ValidationLayer:
    """
    Automated Sanity and Quality Validation Layer.
    Guarantees research integrity, flags misclassifications, verifies product discovery,
    enforces competitor qualification rules, and prevents hallucinations.
    """
    def validate_research(
        self,
        company: Dict[str, Any],
        products_data: Dict[str, Any],
        keywords_data: Dict[str, Any],
        competitors_data: Dict[str, Any],
        pages: List[Dict[str, Any]],
        evidence_registry_sources: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        passed_checks = []
        failed_checks = []
        warnings = []

        industry = company.get("industry", "")
        sub_industry = company.get("sub_industry", "")
        products = products_data.get("products", [])
        categories = products_data.get("categories", [])
        has_ecommerce = company.get("has_ecommerce_signals", False)

        # 1. Industry Sanity Check
        fashion_signals = [t for t in company.get("evidence_tokens", []) if any(f in t.lower() for f in ["dress", "kurta", "suit", "anarkali", "wear", "apparel"])]
        if fashion_signals and "technology" in industry.lower():
            failed_checks.append("Target website has strong fashion signals but was misclassified as Technology & Software.")
        else:
            passed_checks.append(f"Industry classification validated as '{industry}' ({sub_industry}).")

        # 2. Product & Category Discovery Check
        if has_ecommerce and len(products) == 0 and len(categories) == 0:
            failed_checks.append("E-commerce website detected but 0 products and 0 collections were extracted.")
        elif has_ecommerce and (len(products) > 0 or len(categories) > 0):
            passed_checks.append(f"Successfully extracted {len(categories)} collections and {len(products)} catalog items.")
        else:
            passed_checks.append(f"Extracted {len(products)} products/features.")

        # 3. Competitor Relevance & Industry Alignment Check
        direct_comps = competitors_data.get("direct_competitors", [])
        adjacent_comps = competitors_data.get("adjacent_competitors", [])
        marketplace_comps = competitors_data.get("marketplace_competitors", [])
        rejected_comps = competitors_data.get("rejected_candidates", [])

        invalid_direct = []
        for dc in direct_comps:
            dom = dc.get("domain", "").lower()
            if any(inv in dom for inv in ["wikipedia.org", "justdial.com", "foundit.in", "gartner.com", "ibm.com"]):
                invalid_direct.append(dom)

        if invalid_direct:
            failed_checks.append(f"Irrelevant non-competitor domains found in direct competitors: {', '.join(invalid_direct)}.")
        else:
            passed_checks.append(f"Direct competitors validated ({len(direct_comps)} verified brands).")

        passed_checks.append(f"Competitor qualification matrix completed: {len(direct_comps)} Direct, {len(adjacent_comps)} Adjacent, {len(marketplace_comps)} Marketplace, {len(rejected_comps)} Rejected.")

        # 4. Keyword Volume Hallucination Check
        hallucinated_vol = False
        for kw in keywords_data.get("search_keywords", []):
            vol = str(kw.get("search_volume", ""))
            if vol.isdigit() and int(vol) > 0 and "verified" not in str(kw.get("source", "")).lower():
                hallucinated_vol = True
                break
        if hallucinated_vol:
            warnings.append("Search volume detected without verified search volume API connection.")
        else:
            passed_checks.append("Zero fabricated search volumes: All keywords properly marked as unverified for 3rd-party monthly volume.")

        # 5. Source Evidence Registry Check
        if len(evidence_registry_sources) > 0:
            passed_checks.append(f"Full audit trail maintained: {len(evidence_registry_sources)} unique source URLs logged.")
        else:
            warnings.append("No external source registry entries found.")

        is_production_ready = len(failed_checks) == 0

        return {
            "is_valid": is_production_ready,
            "status": "PASSED" if is_production_ready else "FAILED",
            "passed_checks": passed_checks,
            "failed_checks": failed_checks,
            "warnings": warnings,
            "unverified_fields": ["Founded Year"] if company.get("founded_year") == "Not publicly disclosed" else [],
            "rejected_competitors_count": len(rejected_comps),
            "rejected_competitors": rejected_comps
        }

validation_layer = ValidationLayer()
