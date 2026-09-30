from app.classification.taxonomy import INDUSTRY_TAXONOMY
from app.classification.business import classify
from app.evidence.registry import EvidenceRegistry
class BusinessClassifier:
    def classify(self, pages, target_url=''):
        return classify(pages, EvidenceRegistry())
business_classifier = BusinessClassifier()
