"""Compatibility facade for evidence-based classification."""
from app.classification.business import classify
from app.evidence.registry import EvidenceRegistry
class CompanyExtractor:
    def extract_from_pages(self, pages, target_url=''):
        return classify(pages, EvidenceRegistry())
company_extractor = CompanyExtractor()
