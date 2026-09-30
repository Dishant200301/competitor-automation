from typing import List, Dict, Any, Set
from app.services.competitors.search_provider import search_provider
from app.services.crawler.url_normalizer import extract_domain
from app.utils.logger import logger

AGGREGATOR_AND_IRRELEVANT_DOMAINS = {
    # Reference & Encyclopedias
    "wikipedia.org", "wikimedia.org", "wiktionary.org", "archive.org",
    
    # Generic Job Portals & Hiring
    "justdial.com", "foundit.in", "naukri.com", "indeed.com", "glassdoor.com", "monster.com",
    
    # Tech Research & Software Review Aggregators
    "gartner.com", "capterra.com", "g2.com", "trustradius.com", "softwareadvice.com",
    "softwareheritage.org", "github.com", "gitlab.com", "stackoverflow.com",
    "ibm.com", "microsoft.com", "oracle.com", "sap.com", "google.com", "apple.com",
    
    # Social Networks & Discussion Forums
    "reddit.com", "quora.com", "medium.com", "youtube.com", "tiktok.com",
    "facebook.com", "instagram.com", "pinterest.com", "linkedin.com", "twitter.com", "x.com",
    
    # News, Editorial Media & Magazine Portals (Publishers, not brand competitors)
    "indiatimes.com", "timesofindia.com", "thehindu.com", "ndtv.com", "indianexpress.com",
    "hindustantimes.com", "livemint.com", "moneycontrol.com", "business-standard.com",
    "economictimes.com", "vogue.in", "elle.in", "femina.in", "cosmopolitan.in", "gqindia.com",
    "buzzfeed.com", "huffpost.com", "news18.com", "dnaindia.com", "firstpost.com",
    "scoopwhoop.com", "lifestyleasia.com", "popxo.com", "lbb.in",
    
    # Wedding Planning Portals & Vendor Directories
    "weddingwire.in", "wedmegood.com", "shaadisaga.com", "theknot.com", "zola.com",
    
    # B2B Wholesale Listing Directories
    "indiamart.com", "tradeindia.com", "exportersindia.com", "alibaba.com", "aliexpress.com",
    "yellowpages.com", "sulekha.com", "dial4trade.com", "b2bmap.com", "jimtrade.com",
    
    # E-Commerce SaaS, Print-on-Demand & Dropshipping Tooling
    "spocket.co", "qikink.com", "printful.com", "printify.com", "printrove.com",
    "shopify.com", "woocommerce.com", "bigcommerce.com", "wix.com", "squarespace.com",
    
    # Government & Financial
    "gov.in", "nic.in", "forbes.com", "bloomberg.com", "crunchbase.com"
}

def is_blocked_domain(domain: str) -> bool:
    dom = domain.lower().strip()
    for blocked in AGGREGATOR_AND_IRRELEVANT_DOMAINS:
        if dom == blocked or dom.endswith(f".{blocked}"):
            return True
    return False

class CompetitorDiscoverer:
    """
    Evidence-grounded Competitor Candidate Discovery Engine.
    Dynamically generates search query clusters tailored directly to the target's
    verified industry, sub-industry, discovered product collections, and geographic market.
    Strictly filters encyclopedias, job boards, software repos, editorial blogs, and generic directories.
    """
    async def discover_candidates(
        self,
        company_name: str,
        target_domain: str,
        industry: str = "",
        sub_industry: str = "",
        categories: List[str] = None,
        keywords: List[str] = None,
        geographic_market: str = "India"
    ) -> List[Dict[str, Any]]:
        candidates = []
        seen_domains: Set[str] = {target_domain.lower()} if target_domain else set()
        categories = categories or []
        keywords = keywords or []

        # Filter out generic category names like "New In", "Explore All", "Ready To Ship"
        meaningful_categories = [
            c for c in categories
            if not any(skip in c.lower() for skip in ["new in", "explore all", "ready to ship", "sale", "catalog", "view all"])
        ]

        # Build dynamic query clusters based on target's actual verified profile
        queries = []

        # Cluster A: Brand & Direct Alternatives
        clean_name = company_name.strip()
        if clean_name:
            queries.append(f'"{clean_name}" competitors brands')
            queries.append(f'brands like "{clean_name}"')
            queries.append(f'best alternatives to "{clean_name}"')

        # Cluster B: Sub-industry & Industry in Geography
        geo_tag = "India" if "India" in geographic_market else "online"
        if sub_industry:
            queries.append(f'top {sub_industry} brands in {geo_tag}')
            queries.append(f'best {sub_industry} online store brands')
        elif industry:
            queries.append(f'top {industry} brands {geo_tag}')

        # Cluster C: Meaningful Category-Specific Discovery (e.g. Ethnic Suit Sets, Indo-Western, Sharara Sets, Anarkalis)
        for cat in meaningful_categories[:3]:
            queries.append(f'top {cat} fashion brands in {geo_tag}')
            queries.append(f'buy designer {cat} online brand stores')

        logger.info(f"Generated {len(queries)} dynamic discovery queries for {clean_name} ({industry} - {sub_industry})")

        for query in queries:
            try:
                results = await search_provider.search(query, max_results=8)
                for idx, res in enumerate(results):
                    dom = extract_domain(res.url)
                    if not dom or dom in seen_domains or is_blocked_domain(dom):
                        continue
                    seen_domains.add(dom)

                    comp_name = res.title.split("-")[0].split(":")[0].split("|")[0].strip()
                    if not comp_name or len(comp_name) < 2 or any(b in comp_name.lower() for b in ["buy", "top", "best", "online", "shop", "brands"]):
                        # Fallback to domain brand
                        dom_brand = dom.split(".")[0].replace("-", " ").replace("_", " ").title()
                        comp_name = dom_brand

                    rank = getattr(res, "position", 0) or (idx + 1)
                    candidates.append({
                        "competitor_name": comp_name,
                        "website": f"https://{dom}",
                        "domain": dom,
                        "google_rank": rank,
                        "snippet": res.snippet,
                        "source_query": query,
                        "evidence_url": res.url
                    })
                    if len(candidates) >= 20:
                        break
            except Exception as e:
                logger.warning(f"Error querying search provider for '{query}': {e}")

            if len(candidates) >= 20:
                break

        # Sort candidates by Google organic position
        candidates.sort(key=lambda c: c.get("google_rank", 99))
        logger.info(f"Discovered {len(candidates)} qualified candidate competitors for verification")
        return candidates[:16]

competitor_discovery = CompetitorDiscoverer()
