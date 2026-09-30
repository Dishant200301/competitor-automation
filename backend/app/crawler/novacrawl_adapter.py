"""Adapt NovaCrawl's MIT-licensed extraction core (see vendor/NOTICE.md)."""
from bs4 import BeautifulSoup
from .vendor.seo_extractor import SEOExtractor


def extract_metadata(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    result = SEOExtractor.create_empty_result(url, 0, 200)
    for method in (SEOExtractor.extract_basic_seo_data, SEOExtractor.extract_meta_tags,
                   SEOExtractor.extract_json_ld, SEOExtractor.extract_opengraph_tags,
                   SEOExtractor.extract_hreflang):
        method(soup, result)
    return result
