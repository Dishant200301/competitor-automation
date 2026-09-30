from app.extraction.catalog import extract_catalog
from app.evidence.registry import EvidenceRegistry
class ProductExtractor:
    def extract_from_pages(self, pages):
        return extract_catalog(pages, EvidenceRegistry())
product_extractor = ProductExtractor()
