from urllib.parse import urlparse

def classify_page_url(url: str) -> str:
    path = urlparse(url).path.lower().strip("/")
    if not path:
        return "HOME"
    
    # E-commerce Collections & Categories
    if any(k in path for k in ["collection", "category", "categories", "catalog", "shop", "department"]):
        return "COLLECTION"

    # Individual Products
    if any(k in path for k in ["product", "item", "/p/"]):
        return "PRODUCT"

    # Pricing & Subscription (SaaS)
    if any(k in path for k in ["pricing", "plans", "tier", "subscription", "cost"]):
        return "PRICING"

    # Platform & Solutions
    if any(k in path for k in ["solutions", "platform", "features", "tools"]):
        return "PRODUCT"

    # Services
    if any(k in path for k in ["service", "consulting", "managed", "offering"]):
        return "SERVICE"

    # Case studies & Portfolio
    if any(k in path for k in ["case-stud", "customer", "story", "portfolio", "lookbook"]):
        return "CASE_STUDY"

    # About & Company Profile
    if any(k in path for k in ["about", "story", "team", "company", "leadership", "mission"]):
        return "ABOUT"

    # Policies & Shipping
    if any(k in path for k in ["policy", "policies", "shipping", "delivery", "refund", "returns", "terms"]):
        return "POLICY"

    # Contact & Support
    if any(k in path for k in ["contact", "support", "help", "locate", "stores"]):
        return "CONTACT"

    # Blog / Editorial
    if any(k in path for k in ["blog", "article", "news", "post"]):
        return "BLOG"

    return "OTHER"
