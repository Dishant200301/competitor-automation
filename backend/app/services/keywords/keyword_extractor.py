"""Legacy facade; search hypotheses never masquerade as measured search demand."""
from app.keywords.research import research_keywords
from app.evidence.registry import EvidenceRegistry
class KeywordExtractor:
    def extract_keywords(self, pages, company_name='', industry='', sub_industry='', categories=None):
        return research_keywords(pages, {'products':[], 'categories':categories or [], 'services':[]},
                                 {'company_name':company_name}, EvidenceRegistry())
keyword_extractor = KeywordExtractor()
