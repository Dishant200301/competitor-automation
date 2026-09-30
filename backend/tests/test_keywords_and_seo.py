import pytest
from app.services.keywords.keyword_extractor import KeywordExtractor
from app.services.seo.seo_extractor import SeoExtractor

def test_keyword_extraction():
    pages = [{
        "url": "https://example.com",
        "title": "Cloud Analytics Platform - Realtime Database Solutions",
        "h1": ["Enterprise Analytics Platform"],
        "h2": ["Realtime Stream Processing", "Cloud Database Cost Pricing"],
        "main_text": "Our enterprise analytics platform offers real-time streaming queries and cloud database capabilities.",
    }]

    extractor = KeywordExtractor()
    keywords = extractor.extract_keywords(pages, company_name="Acme")
    assert len(keywords) > 0

    kw_terms = [k["keyword"] for k in keywords]
    assert any("analytics" in term for term in kw_terms)
    assert any("platform" in term for term in kw_terms)

def test_seo_observations():
    pages = [
        {"url": "https://example.com", "page_type": "HOME", "title": "Home", "canonical_url": "https://example.com"},
        {"url": "https://example.com/blog", "page_type": "BLOG", "title": "Blog"},
        {"url": "https://example.com/pricing", "page_type": "PRICING", "title": "Pricing"},
    ]

    extractor = SeoExtractor()
    seo_res = extractor.analyze_seo(
        pages=pages,
        sitemap_urls=["https://example.com/sitemap.xml"],
        robots_available=True
    )

    assert seo_res["sitemap_available"] is True
    assert seo_res["robots_txt_available"] is True
    assert seo_res["has_blog"] is True
    assert seo_res["has_pricing"] is True
    assert len(seo_res["observations"]) >= 3
