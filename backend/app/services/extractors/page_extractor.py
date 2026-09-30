from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import json
from typing import Dict, Any, List
from app.services.crawler.url_normalizer import normalize_url, is_same_domain

def extract_structured_page_data(url: str, final_url: str, html: str, status_code: int) -> Dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    
    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    
    meta_desc = ""
    desc_tag = soup.find("meta", attrs={"name": lambda n: n and n.lower() == "description"})
    if not desc_tag:
        desc_tag = soup.find("meta", attrs={"property": "og:description"})
    if desc_tag and desc_tag.get("content"):
        meta_desc = desc_tag["content"].strip()
        
    canonical_url = ""
    can_tag = soup.find("link", attrs={"rel": "canonical"})
    if can_tag and can_tag.get("href"):
        canonical_url = urljoin(final_url, can_tag["href"].strip())
        
    h1s = [h.get_text(separator=" ", strip=True) for h in soup.find_all("h1") if h.get_text(strip=True)]
    h2s = [h.get_text(separator=" ", strip=True) for h in soup.find_all("h2") if h.get_text(strip=True)]
    
    # JSON-LD structured data
    structured_data = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        if script.string:
            try:
                data = json.loads(script.string.strip())
                if isinstance(data, list):
                    structured_data.extend(data)
                elif isinstance(data, dict):
                    if "@graph" in data and isinstance(data["@graph"], list):
                        structured_data.extend(data["@graph"])
                    else:
                        structured_data.append(data)
            except Exception:
                continue

    # Internal & external links
    internal_links = []
    external_links = []
    seen_links = set()
    
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        full_url = normalize_url(urljoin(final_url, href))
        if not full_url or full_url in seen_links:
            continue
        seen_links.add(full_url)
        
        if is_same_domain(final_url, full_url):
            internal_links.append(full_url)
        else:
            external_links.append(full_url)

    # Clean text extraction - remove scripts, styles, navigation, footer and noise for pristine data
    soup_clean = BeautifulSoup(html, "html.parser")
    for s in soup_clean(["script", "style", "noscript", "svg", "iframe", "nav", "footer"]):
        s.decompose()
    raw_text = soup_clean.get_text(separator=" ", strip=True)
    import re as _re
    main_text = _re.sub(r"\s+", " ", raw_text).strip()

    return {
        "url": url,
        "final_url": final_url,
        "status_code": status_code,
        "title": title,
        "meta_description": meta_desc,
        "canonical_url": canonical_url,
        "h1": h1s,
        "h2": h2s,
        "main_text": main_text,
        "structured_data": structured_data,
        "internal_links": internal_links,
        "external_links": external_links
    }
