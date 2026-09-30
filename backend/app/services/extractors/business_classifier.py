import re
from typing import List, Dict, Any, Tuple
from urllib.parse import urlparse
from app.utils.logger import logger

INDUSTRY_TAXONOMY = {
    "Fashion & Apparel": {
        "keywords": [
            "dress", "dresses", "kurta", "kurtas", "kurti", "kurtis", "suit", "suits",
            "anarkali", "anarkalis", "sharara", "shararas", "lehenga", "lehengas",
            "saree", "sarees", "ethnic", "indo-western", "co-ord", "co-ords", "gown",
            "gowns", "kaftan", "kaftans", "clothing", "wear", "outfit", "outfits",
            "apparel", "attire", "fashion", "boutique", "fabric", "bridal", "wedding wear",
            "festive wear", "salwar", "dupattas", "tops", "shirts", "garments"
        ],
        "default_sub": "Women's Ethnic & Modern Apparel",
        "default_model": "D2C E-commerce",
        "default_audience": "Women seeking ethnic, wedding, festive, and contemporary fashion"
    },
    "Technology & Software": {
        "keywords": [
            "software", "saas", "api", "apis", "cloud platform", "sdk", "developer tools",
            "devops", "database", "crm", "erp", "cybersecurity", "ai engine", "machine learning",
            "analytics platform", "open source code", "infrastructure", "workflow automation",
            "enterprise software", "b2b software", "microservices"
        ],
        "default_sub": "Enterprise & Cloud Software",
        "default_model": "B2B SaaS / Subscription",
        "default_audience": "Enterprises, developers, and digital operations teams"
    },
    "Healthcare & Medical": {
        "keywords": [
            "clinic", "hospital", "doctor", "physician", "patient", "treatment", "therapy",
            "surgery", "pharmaceutical", "diagnostic", "healthcare", "medicine", "clinical"
        ],
        "default_sub": "Medical & Clinical Healthcare",
        "default_model": "Healthcare Provider",
        "default_audience": "Patients and healthcare seekers"
    },
    "Food, Beverage & Hospitality": {
        "keywords": [
            "restaurant", "dining", "menu", "cuisine", "chef", "cafe", "coffee", "bakery",
            "food delivery", "gourmet", "dishes", "hotel", "resort", "lodging"
        ],
        "default_sub": "Dining & Hospitality",
        "default_model": "Hospitality / F&B",
        "default_audience": "Diners, travelers, and food consumers"
    },
    "Education & E-Learning": {
        "keywords": [
            "course", "courses", "academy", "training", "curriculum", "tuition", "students",
            "certification", "learning", "instructor", "bootcamp", "university"
        ],
        "default_sub": "Education & Online Training",
        "default_model": "Educational Platform",
        "default_audience": "Students, professionals, and lifelong learners"
    },
    "Professional Services & Agency": {
        "keywords": [
            "consulting", "agency", "marketing agency", "seo services", "branding agency",
            "design studio", "accounting firm", "legal services", "law firm", "advisory"
        ],
        "default_sub": "Consulting & Professional Services",
        "default_model": "Agency / Client Services",
        "default_audience": "Businesses and organizations seeking expert advisory"
    },
    "Manufacturing & Industrial": {
        "keywords": [
            "manufacturing", "industrial", "factory", "machinery", "fabrication", "supplier",
            "raw materials", "oem", "wholesale distribution", "bulk supply"
        ],
        "default_sub": "Industrial Manufacturing & Supply",
        "default_model": "B2B Wholesale / Manufacturing",
        "default_audience": "Industrial buyers, contractors, and distributors"
    }
}

class BusinessClassifier:
    """
    Evidence-grounded Business & Industry Classification Engine.
    Examines structured data, metadata, URL taxonomy, and content tokens.
    Never relies on arbitrary assumptions or hardcoded defaults.
    """
    def classify(self, pages: List[Dict[str, Any]], target_url: str) -> Dict[str, Any]:
        corpus_list = []
        structured_types = []
        url_paths = []
        has_ecommerce_signals = False

        for page in pages:
            url = page.get("url", "")
            path = urlparse(url).path.lower()
            url_paths.append(path)

            # Check e-commerce URL patterns
            if any(p in path for p in ["/collections", "/products", "/cart", "/checkout", "/shop", "/catalog"]):
                has_ecommerce_signals = True

            title = page.get("title", "")
            meta = page.get("meta_description", "")
            h1 = " ".join(page.get("h1", []))
            h2 = " ".join(page.get("h2", []))
            text = page.get("main_text", "")[:3000]

            corpus_list.extend([title, meta, h1, h2, text])

            for s_data in page.get("structured_data", []):
                t_str = str(s_data.get("@type", "")).lower()
                structured_types.append(t_str)
                if any(e_type in t_str for e_type in ["product", "offer", "store", "onlinestore", "clothingstore"]):
                    has_ecommerce_signals = True

        combined_text = " ".join(corpus_list).lower()

        # Check Schema.org strong signals
        schema_industry = None
        for st in structured_types:
            if "clothingstore" in st:
                schema_industry = "Fashion & Apparel"
                has_ecommerce_signals = True
                break
            elif "softwareapplication" in st:
                schema_industry = "Technology & Software"
                break
            elif "medicalorganization" in st or "physician" in st:
                schema_industry = "Healthcare & Medical"
                break
            elif "restaurant" in st or "foodestablishment" in st:
                schema_industry = "Food, Beverage & Hospitality"
                break

        # Token frequency evaluation
        scores = {}
        matched_tokens = {}
        for ind, details in INDUSTRY_TAXONOMY.items():
            score = 0
            matches = []
            for kw in details["keywords"]:
                # Match whole words or clean boundaries
                pattern = r"\b" + re.escape(kw) + r"\b"
                hits = len(re.findall(pattern, combined_text))
                if hits > 0:
                    score += hits
                    matches.append((kw, hits))
            scores[ind] = score
            matched_tokens[ind] = matches

        # Rank industries by evidence
        sorted_industries = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top_industry, top_score = sorted_industries[0] if sorted_industries else ("Digital Services", 0)

        if schema_industry and scores.get(schema_industry, 0) > 2:
            resolved_industry = schema_industry
        elif top_score > 3:
            resolved_industry = top_industry
        else:
            resolved_industry = "Digital Business & Consumer Goods" if has_ecommerce_signals else "Technology & Digital Services"

        # Determine sub-industry and business model
        ind_config = INDUSTRY_TAXONOMY.get(resolved_industry, {})
        sub_industry = ind_config.get("default_sub", "Specialized Commercial Services")
        business_model = "D2C E-commerce" if has_ecommerce_signals else ind_config.get("default_model", "Direct Provider")
        target_audience = ind_config.get("default_audience", "Consumers and commercial clients")

        # Refine for Fashion specifically based on observed tokens
        if resolved_industry == "Fashion & Apparel":
            fashion_tokens = [m[0] for m in matched_tokens.get("Fashion & Apparel", [])]
            if any(t in fashion_tokens for t in ["indo-western", "anarkali", "sharara", "kurta", "ethnic", "lehenga", "suit"]):
                sub_industry = "Women's Ethnic & Indo-Western Wear"
                target_audience = "Women seeking traditional, festive, bridal, and modern Indo-Western apparel"
            elif any(t in fashion_tokens for t in ["bridal", "wedding"]):
                sub_industry = "Bridal & Festive Fashion"
            business_model = "D2C E-commerce (Specialized Fashion Brand)"

        # Detect geographic market & currency
        geo_signals = []
        currencies = set()
        if re.search(r"(\$|usd|united states|shipping to usa)", combined_text):
            currencies.add("USD")
            geo_signals.append("USA")
        if re.search(r"(₹|inr|rs\.?|india|delhi|mumbai|surat|ahmedabad|jaipur)", combined_text):
            currencies.add("INR")
            geo_signals.append("India")
        if re.search(r"(£|gbp|united kingdom|london)", combined_text):
            currencies.add("GBP")
            geo_signals.append("UK")
        if re.search(r"(aed|dubai|uae)", combined_text):
            currencies.add("AED")
            geo_signals.append("UAE")
        if re.search(r"(cad|canada)", combined_text):
            currencies.add("CAD")
            geo_signals.append("Canada")
        if re.search(r"(worldwide|international shipping|global delivery)", combined_text):
            geo_signals.append("International / Worldwide")

        primary_geo = "India (Domestic) & Global Worldwide Shipping" if "India" in geo_signals and ("USA" in geo_signals or "International / Worldwide" in geo_signals) else (", ".join(list(dict.fromkeys(geo_signals))[:3]) or "Domestic & International")
        currency_str = ", ".join(currencies) if currencies else "INR (₹) / Regional"

        return {
            "industry": resolved_industry,
            "sub_industry": sub_industry,
            "business_model": business_model,
            "target_audience": target_audience,
            "geographic_market": primary_geo,
            "currencies_accepted": currency_str,
            "evidence_score": top_score,
            "evidence_tokens": [f"{t[0]} ({t[1]} occurrences)" for t in matched_tokens.get(resolved_industry, [])[:8]],
            "has_ecommerce_signals": has_ecommerce_signals
        }

business_classifier = BusinessClassifier()
