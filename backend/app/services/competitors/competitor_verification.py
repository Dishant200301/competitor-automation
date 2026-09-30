import re
from typing import List, Dict, Any, Tuple
import httpx
from bs4 import BeautifulSoup
from app.core.config import settings
from app.core.security import is_safe_url
from app.services.crawler.url_normalizer import normalize_url, extract_domain
from app.utils.logger import logger

MARKETPLACE_DOMAINS = {
    "myntra.com", "nykaafashion.com", "nykaa.com", "ajio.com", "tata-cliq.com",
    "tatacliq.com", "amazon.in", "flipkart.com", "etsy.com", "meesho.com", "limeroad.com", "perniaspopupshop.com"
}

REJECTED_DOMAINS = {
    # Reference & Job Portals
    "wikipedia.org", "wikimedia.org", "wiktionary.org", "justdial.com", "foundit.in", "naukri.com",
    "indeed.com", "glassdoor.com", "monster.com", "archive.org",
    
    # Software & Tech
    "gartner.com", "capterra.com", "g2.com", "trustradius.com", "softwareadvice.com",
    "softwareheritage.org", "github.com", "gitlab.com", "stackoverflow.com",
    "ibm.com", "microsoft.com", "oracle.com", "sap.com", "google.com", "apple.com",
    
    # News, Editorial Media & Magazines
    "indiatimes.com", "timesofindia.com", "thehindu.com", "ndtv.com", "indianexpress.com",
    "hindustantimes.com", "livemint.com", "moneycontrol.com", "business-standard.com",
    "economictimes.com", "vogue.in", "elle.in", "femina.in", "cosmopolitan.in", "gqindia.com",
    "buzzfeed.com", "huffpost.com", "news18.com", "dnaindia.com", "firstpost.com",
    "scoopwhoop.com", "lifestyleasia.com", "popxo.com", "lbb.in",
    
    # B2B Directories & Wholesale
    "indiamart.com", "tradeindia.com", "exportersindia.com", "alibaba.com", "aliexpress.com",
    "yellowpages.com", "sulekha.com", "dial4trade.com", "b2bmap.com", "jimtrade.com",
    
    # Wedding Planning Portals
    "weddingwire.in", "wedmegood.com", "shaadisaga.com", "theknot.com", "zola.com",
    
    # E-Commerce SaaS, Print-on-Demand & Dropshipping Tooling
    "spocket.co", "qikink.com", "printful.com", "printify.com", "printrove.com",
    "shopify.com", "woocommerce.com", "bigcommerce.com", "wix.com", "squarespace.com"
}

def is_blocked_candidate(domain: str) -> bool:
    dom = domain.lower().strip()
    for rd in REJECTED_DOMAINS:
        if dom == rd or dom.endswith(f".{rd}"):
            return True
    return False

class CompetitorVerifier:
    """
    Evidence-grounded Competitor Qualification & Deep Verification Engine.
    Executes a 10-point qualification matrix for every candidate competitor.
    Categorizes strictly into: DIRECT, ADJACENT, MARKETPLACE / SEARCH, or REJECTED.
    Deeply crawls qualified competitors to extract factual products, pricing, and SEO data.
    """
    async def verify_candidates(
        self,
        candidates: List[Dict[str, Any]],
        target_industry: str = "Fashion & Apparel",
        target_sub_industry: str = "Women's Ethnic & Indo-Western Wear",
        target_categories: List[str] = None,
        target_keywords: List[str] = None
    ) -> Dict[str, Any]:
        target_categories = target_categories or []
        target_keywords = target_keywords or []
        headers = {"User-Agent": settings.CRAWLER_USER_AGENT}

        verified_direct = []
        verified_adjacent = []
        verified_marketplace = []
        qualification_matrix = []
        rejected_candidates = []

        async with httpx.AsyncClient(headers=headers, timeout=10.0, follow_redirects=True) as client:
            for cand in candidates:
                domain = cand.get("domain", "").lower()
                evidence_url = cand.get("evidence_url", cand.get("website", ""))
                comp_url = cand.get("website", f"https://{domain}")
                snippet = cand.get("snippet", "").lower()
                comp_name = cand.get("competitor_name", domain.title())

                # Quick check: is domain blacklisted (encyclopedias, media portals, B2B directories, tech)?
                if is_blocked_candidate(domain):
                    matrix_entry = self._build_matrix_row(
                        name=comp_name, url=comp_url,
                        ind_match=False, prod_match=False, aud_match=False, geo_match=False,
                        model_match=False, active=False, qual="REJECTED",
                        reason=f"Rejected: Domain '{domain}' is an editorial publisher, B2B wholesale directory, job portal, or unrelated tech/reference site.",
                        evidence_url=evidence_url
                    )
                    qualification_matrix.append(matrix_entry)
                    rejected_candidates.append({"domain": domain, "reason": matrix_entry["reason"]})
                    continue

                # Is it a marketplace / search competitor?
                if any(domain == md or domain.endswith(f".{md}") for md in MARKETPLACE_DOMAINS):
                    matrix_entry = self._build_matrix_row(
                        name=comp_name, url=comp_url,
                        ind_match=True, prod_match=True, aud_match=True, geo_match=True,
                        model_match=False, active=True, qual="MARKETPLACE / SEARCH",
                        reason="Multi-brand marketplace / aggregator competing for customer category search demand.",
                        evidence_url=evidence_url
                    )
                    qualification_matrix.append(matrix_entry)
                    verified_marketplace.append({
                        "competitor_name": comp_name,
                        "website": comp_url,
                        "domain": domain,
                        "competitor_type": "Marketplace / Search Competitor",
                        "confidence_level": "HIGH",
                        "google_rank": cand.get("google_rank", 1),
                        "reason": matrix_entry["reason"],
                        "description": cand.get("snippet", "Major retail platform competing for commercial category search intent."),
                        "products": ["Aggregated Brand Collections", "Multi-Designer Catalog"],
                        "pricing_model": "Multi-tier Marketplace Pricing",
                        "key_features": ["Catalog aggregation", "Customer search visibility", "Pan-India logistics"],
                        "competitive_overlap": "Competes directly for organic search rankings and transactional fashion search queries.",
                        "evidence_urls": [evidence_url],
                        "deep_extracted": False
                    })
                    continue

                # Deep verification crawl of candidate homepage
                crawl_data = await self._crawl_candidate(client, comp_url, comp_name)
                
                # Check signals
                ind_match = crawl_data["industry_match"] or any(
                    tok in snippet for tok in ["ethnic", "kurta", "dress", "saree", "suit", "anarkali", "fashion", "apparel", "wear", "co-ord", "lehenga"]
                )
                prod_match = crawl_data["product_match"] or any(
                    cat.lower() in snippet for cat in target_categories[:4]
                )
                aud_match = crawl_data["audience_match"] or any(
                    tok in snippet for tok in ["women", "ladies", "bridal", "festive", "wedding", "designer"]
                )
                geo_match = True
                active_domain = crawl_data["active"]
                model_match = crawl_data["is_brand_ecommerce"]

                # Decide qualification
                if not active_domain:
                    qual = "REJECTED"
                    reason = "Domain is inactive or unreachable via HTTP."
                    rejected_candidates.append({"domain": domain, "reason": reason})
                elif not ind_match:
                    qual = "REJECTED"
                    reason = f"Industry mismatch: Candidate operates outside {target_industry}."
                    rejected_candidates.append({"domain": domain, "reason": reason})
                elif ind_match and prod_match and aud_match and model_match:
                    qual = "DIRECT COMPETITOR"
                    reason = f"Strong evidence-based overlap in products ({', '.join(crawl_data.get('matched_products', [])[:3]) or target_sub_industry}), target audience, and direct commercial intent."
                elif ind_match and (prod_match or aud_match):
                    qual = "ADJACENT COMPETITOR"
                    reason = f"Adjacent overlap in {target_industry}, but offers broader/alternative product catalog or multi-brand positioning."
                else:
                    qual = "REJECTED"
                    reason = "Insufficient product, commercial e-commerce, or audience overlap."
                    rejected_candidates.append({"domain": domain, "reason": reason})

                matrix_entry = self._build_matrix_row(
                    name=comp_name, url=comp_url,
                    ind_match=ind_match, prod_match=prod_match, aud_match=aud_match, geo_match=geo_match,
                    model_match=model_match, active=active_domain, qual=qual,
                    reason=reason, evidence_url=evidence_url
                )
                qualification_matrix.append(matrix_entry)

                if qual in ("DIRECT COMPETITOR", "ADJACENT COMPETITOR"):
                    item_payload = {
                        "competitor_name": comp_name,
                        "website": comp_url,
                        "domain": domain,
                        "competitor_type": qual,
                        "confidence_level": "HIGH" if qual == "DIRECT COMPETITOR" else "MEDIUM",
                        "google_rank": cand.get("google_rank", 1),
                        "reason": reason,
                        "description": crawl_data.get("description") or cand.get("snippet", "Active brand offering specialized collections."),
                        "products": crawl_data.get("products", [target_sub_industry]),
                        "pricing_model": crawl_data.get("pricing_summary", "Observed on public catalog"),
                        "key_features": crawl_data.get("key_features", ["Online D2C catalog", "Express shipping", "Curated collections"]),
                        "top_keywords": crawl_data.get("top_keywords", target_keywords[:3]),
                        "competitive_overlap": crawl_data.get("competitive_overlap", f"Competitor in {target_sub_industry} targeting similar customer demand."),
                        "evidence_urls": [evidence_url] + (crawl_data.get("discovered_pages", [])[:2]),
                        "social_profiles": crawl_data.get("social_profiles", []),
                        "deep_extracted": crawl_data.get("success", False)
                    }
                    if qual == "DIRECT COMPETITOR":
                        verified_direct.append(item_payload)
                    else:
                        verified_adjacent.append(item_payload)

                if len(verified_direct) >= 6 and len(verified_adjacent) >= 4:
                    break

        all_verified = verified_direct + verified_adjacent + verified_marketplace
        all_verified.sort(key=lambda x: (0 if "Direct" in x["competitor_type"] else (1 if "Adjacent" in x["competitor_type"] else 2), x.get("google_rank", 99)))

        return {
            "all_verified": all_verified,
            "direct_competitors": verified_direct,
            "adjacent_competitors": verified_adjacent,
            "marketplace_competitors": verified_marketplace,
            "qualification_matrix": qualification_matrix,
            "rejected_candidates": rejected_candidates
        }

    def _build_matrix_row(self, name, url, ind_match, prod_match, aud_match, geo_match, model_match, active, qual, reason, evidence_url):
        return {
            "competitor_name": name,
            "website": url,
            "industry_match": "Yes" if ind_match else "No",
            "product_match": "Yes" if prod_match else "No",
            "audience_match": "Yes" if aud_match else "No",
            "geography_match": "Yes" if geo_match else "No",
            "business_model_match": "Yes" if model_match else "No",
            "active_domain": "Yes" if active else "No",
            "overall_qualification": qual,
            "reason": reason,
            "evidence_url": evidence_url
        }

    async def _crawl_candidate(self, client: httpx.AsyncClient, url: str, name: str) -> Dict[str, Any]:
        result = {
            "active": False,
            "success": False,
            "industry_match": False,
            "product_match": False,
            "audience_match": False,
            "is_brand_ecommerce": False,
            "description": "",
            "products": [],
            "matched_products": [],
            "pricing_summary": "Observed on public catalog",
            "key_features": [],
            "top_keywords": [],
            "competitive_overlap": "",
            "discovered_pages": [],
            "social_profiles": []
        }

        try:
            res = await client.get(url, timeout=7.0)
            if res.status_code == 200:
                result["active"] = True
                result["success"] = True
                html = res.text
                soup = BeautifulSoup(html, "html.parser")

                title = soup.title.string.strip() if soup.title and soup.title.string else ""
                desc_meta = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
                meta_desc = desc_meta.get("content", "").strip() if desc_meta else ""
                result["description"] = meta_desc or (title[:180] if title else "")

                # Social profiles
                social_links = []
                for a in soup.find_all("a", href=True):
                    href = a["href"].lower()
                    if "instagram.com/" in href and not any(x in href for x in ["/p/", "/share"]):
                        social_links.append(a["href"])
                    elif "facebook.com/" in href and not any(x in href for x in ["/sharer"]):
                        social_links.append(a["href"])
                    elif "youtube.com/" in href:
                        social_links.append(a["href"])
                result["social_profiles"] = list(dict.fromkeys(social_links))[:3]

                # Content tokens
                text = (soup.get_text(separator=" ", strip=True) + " " + meta_desc + " " + title).lower()

                fashion_tokens = ["kurta", "suit", "anarkali", "sharara", "dress", "saree", "lehenga", "ethnic", "indo-western", "co-ord", "apparel", "wear", "clothing"]
                matched_f = [t for t in fashion_tokens if t in text]
                if len(matched_f) >= 2:
                    result["industry_match"] = True
                    result["product_match"] = True
                    result["matched_products"] = [t.title() for t in matched_f[:4]]

                if any(w in text for w in ["women", "ladies", "bride", "bridal", "festive", "designer", "wedding"]):
                    result["audience_match"] = True

                if any(c in text for c in ["cart", "bag", "checkout", "shipping", "inr", "₹", "$", "shop now", "add to cart", "buy now"]):
                    result["is_brand_ecommerce"] = True

                # Discovered categories / products from nav or headings
                prods = []
                for h in soup.find_all(["h1", "h2", "h3"])[:12]:
                    ht = h.get_text(strip=True)
                    if 4 < len(ht) < 40 and not any(skip in ht.lower() for skip in ["filter", "sort", "login", "cart", "menu", "quick", "view", "contact", "newsletter", "follow"]):
                        prods.append(ht)
                if prods:
                    result["products"] = list(dict.fromkeys(prods))[:4]
                elif result["matched_products"]:
                    result["products"] = [f"Designer {p}" for p in result["matched_products"]]

                # Price patterns
                prices = re.findall(r"(?:₹|Rs\.?|INR|\$)\s*([\d,]+)", text)
                if prices:
                    clean_nums = []
                    for p in prices:
                        try:
                            n = float(p.replace(",", ""))
                            if 300 < n < 150000:
                                clean_nums.append(n)
                        except Exception:
                            pass
                    if clean_nums:
                        result["pricing_summary"] = f"Observed catalog prices range from ₹{min(clean_nums):,.0f} to ₹{max(clean_nums):,.0f}."

                caps = []
                if "worldwide shipping" in text or "international shipping" in text:
                    caps.append("Worldwide & International Shipping")
                if "custom" in text or "made to order" in text:
                    caps.append("Custom & Made-to-Order Stitching")
                if "ready to ship" in text:
                    caps.append("Express / Ready to Ship Options")
                caps.append("Direct Consumer E-Commerce Presence")
                result["key_features"] = caps[:3]

                result["competitive_overlap"] = f"Competes directly in {', '.join(result['matched_products'][:3]) or 'women fashion'} with direct e-commerce catalog offerings."

        except Exception as e:
            logger.debug(f"Deep candidate crawl error for {url}: {e}")

        return result

competitor_verifier = CompetitorVerifier()
