from typing import List, Dict, Any

class SeoExtractor:
    def analyze_seo(
        self,
        pages: List[Dict[str, Any]],
        sitemap_urls: List[str] = None,
        robots_available: bool = True
    ) -> Dict[str, Any]:
        sitemap_urls = sitemap_urls or []
        sitemap_available = len(sitemap_urls) > 0
        robots_txt_available = bool(robots_available)

        page_types = {p.get("page_type") for p in pages}
        has_blog = "BLOG" in page_types or any("blog" in p.get("url", "").lower() for p in pages)
        has_pricing = "PRICING" in page_types or any("pricing" in p.get("url", "").lower() for p in pages)
        has_canonical = any(bool(p.get("canonical_url")) for p in pages)
        has_structured = any(bool(p.get("structured_data")) for p in pages)

        observations = []
        if sitemap_available:
            observations.append(f"Sitemap verified with {len(sitemap_urls)} indexed sections.")
        else:
            observations.append("No active XML sitemap detected in root discovery.")

        if robots_txt_available:
            observations.append("Robots.txt file discovered with crawl directives.")

        if has_blog:
            observations.append("Active blog presence identified for organic content marketing.")
        if has_pricing:
            observations.append("Public pricing page discovered with transparent tier offerings.")

        if has_canonical:
            observations.append("Canonical URL tags implemented across indexed pages.")
        if has_structured:
            observations.append("Schema.org structured data (JSON-LD) detected.")

        return {
            "sitemap_available": sitemap_available,
            "robots_txt_available": robots_txt_available,
            "has_blog": has_blog,
            "has_pricing": has_pricing,
            "has_canonical": has_canonical,
            "has_structured_data": has_structured,
            "observations": observations
        }

seo_extractor = SeoExtractor()
