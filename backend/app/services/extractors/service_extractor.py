from app.extraction.catalog import extract_catalog
from app.evidence.registry import EvidenceRegistry
class ServiceExtractor:
    def extract_from_pages(self, pages):
        return extract_catalog(pages, EvidenceRegistry())['services']
service_extractor = ServiceExtractor()
