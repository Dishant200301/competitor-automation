import re
from typing import Dict, Any, List
from app.services.crawler.url_normalizer import extract_domain
from app.services.extractors.business_classifier import business_classifier

class CompanyExtractor:
    def extract_from_pages(self, pages: List[Dict[str, Any]], target_url: str) -> Dict[str, Any]:
        domain = extract_domain(target_url)
        # Clean brand name fallback: e.g. "label-s4u.com" -> "Label S4U"
        raw_prefix = domain.split(".")[0] if domain else "Target Entity"
        cleaned_brand = raw_prefix.replace("-", " ").replace("_", " ").title()
        
        # Specific known pattern fixes: e.g. S4u -> S4U
        cleaned_brand = re.sub(r"\b([a-zA-Z])(\d+)([a-zA-Z])\b", lambda m: f"{m.group(1).upper()}{m.group(2)}{m.group(3).upper()}", cleaned_brand)

        company_name = cleaned_brand
        founded_year = None
        description = ""
        location = ""

        # Search structured data first
        for page in pages:
            for item in page.get("structured_data", []):
                item_type = str(item.get("@type", "")).lower()
                if any(t in item_type for t in ["organization", "corporation", "company", "store", "onlinestore", "clothingstore", "localbusiness"]):
                    if item.get("name") and len(item.get("name").strip()) > 1:
                        company_name = item["name"].strip()
                    if item.get("foundingDate"):
                        founded_year = str(item["foundingDate"])[:4]
                    if item.get("description"):
                        description = item["description"].strip()
                    if item.get("address"):
                        addr = item["address"]
                        if isinstance(addr, dict):
                            location = f"{addr.get('addressLocality', '')}, {addr.get('addressCountry', '')}".strip(", ")
                        elif isinstance(addr, str):
                            location = addr

        # Fallback to home page metadata
        home_page = next((p for p in pages if p.get("page_type") == "HOME"), None) or (pages[0] if pages else {})
        if not description and home_page.get("meta_description"):
            description = home_page["meta_description"].strip()

        # Fallback to homepage title if structured data did not specify an official organization name
        if (not company_name or company_name == cleaned_brand) and home_page.get("title"):
            title_parts = re.split(r"[|\-–—:]", home_page["title"])
            if title_parts and len(title_parts[0].strip()) > 2 and len(title_parts[0].strip()) < 40:
                potential_name = title_parts[0].strip()
                if not any(stop in potential_name.lower() for stop in ["home", "welcome", "official", "buy", "online", "store"]):
                    company_name = potential_name

        if not founded_year:
            all_text = " ".join([p.get("main_text", "") for p in pages[:4]])
            year_match = re.search(r"\b(founded|established|started|since)\s+(?:in\s+)?(19\d\d|20\d\d)\b", all_text, re.IGNORECASE)
            if year_match:
                founded_year = year_match.group(2)

        # Dynamic Evidence-Based Industry Classification
        biz_info = business_classifier.classify(pages, target_url)

        # Contact and location extraction fallback from address/footer text
        if not location:
            for page in pages:
                txt = page.get("main_text", "")
                loc_match = re.search(r"\b(Surat|Mumbai|Delhi|Jaipur|Ahmedabad|Bengaluru|Bangalore|Kolkata|Pune|Chennai|New York|London|Dubai)\b(?:,\s*([A-Za-z\s]+))?", txt, re.IGNORECASE)
                if loc_match:
                    city = loc_match.group(1).title()
                    country = loc_match.group(2).title() if loc_match.group(2) else "India"
                    location = f"{city}, {country}"
                    break

        return {
            "company_name": company_name,
            "domain": domain,
            "website": target_url,
            "industry": biz_info["industry"],
            "sub_industry": biz_info["sub_industry"],
            "business_model": biz_info["business_model"],
            "target_audience": biz_info["target_audience"],
            "geographic_market": biz_info["geographic_market"],
            "currencies_accepted": biz_info["currencies_accepted"],
            "description": description or f"Specialized brand offering {biz_info['sub_industry'].lower()} at {domain}.",
            "founded_year": founded_year or "Not publicly disclosed",
            "location": location or "Domestic & International",
            "evidence_score": biz_info["evidence_score"],
            "evidence_tokens": biz_info["evidence_tokens"],
            "has_ecommerce_signals": biz_info["has_ecommerce_signals"]
        }

company_extractor = CompanyExtractor()
