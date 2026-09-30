from urllib.parse import urlparse, urlunparse, urljoin
import re

TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "gclid", "fbclid", "msclkid", "ref", "mc_cid", "mc_eid"
}

def normalize_url(url: str, base_url: str = "") -> str:
    if not url:
        return ""
    
    url = url.strip()
    if base_url:
        url = urljoin(base_url, url)
        
    parsed = urlparse(url)
    scheme = parsed.scheme.lower() or "https"
    netloc = parsed.netloc.lower()
    
    if netloc.startswith("www."):
        netloc = netloc[4:]
        
    path = parsed.path or "/"
    path = re.sub(r"/+", "/", path)
    if path != "/" and path.endswith("/"):
        path = path[:-1]
        
    clean_query = []
    if parsed.query:
        for pair in parsed.query.split("&"):
            if "=" in pair:
                key, val = pair.split("=", 1)
                if key.lower() not in TRACKING_PARAMS:
                    clean_query.append(pair)
            elif pair.lower() not in TRACKING_PARAMS and pair:
                clean_query.append(pair)
    query_str = "&".join(clean_query)
    
    return urlunparse((scheme, netloc, path, "", query_str, ""))

def extract_domain(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url if "://" in url else f"https://{url}")
    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    if ":" in netloc:
        netloc = netloc.split(":")[0]
    return netloc

def is_same_domain(url1: str, url2: str) -> bool:
    d1 = extract_domain(url1)
    d2 = extract_domain(url2)
    return bool(d1 and d2 and (d1 == d2 or d1.endswith(f".{d2}") or d2.endswith(f".{d1}")))
