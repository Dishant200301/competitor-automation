import os
import sys
from pathlib import Path
os.environ['DATABASE_BACKEND'] = 'sqlite'
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pytest
from app.extraction.pages import extract_page
from app.extraction.catalog import extract_catalog
from app.classification.business import classify
from app.evidence.registry import EvidenceRegistry
from app.keywords.research import research_keywords
from app.validation.engine import validate


@pytest.fixture
def dataset():
    html = '''<html lang="en"><title>North Loom</title><meta name="description" content="Apparel and fashion for women in India.">
    <nav><a href="/collections/linen-shirts">Linen Shirts</a></nav><h1>Women's linen shirts and clothing</h1>
    <p>Fashion apparel for women. Shipping to India. Add to cart</p><a href="/products/linen-shirt">Linen Shirt</a>
    <script type="application/ld+json">{"@type":"Organization","name":"North Loom"}</script>
    <script type="application/ld+json">{"@type":"Product","name":"Linen Shirt","url":"/products/linen-shirt","sku":"L1","offers":{"price":"42.50","priceCurrency":"USD"}}</script></html>'''
    pages = [extract_page(html, 'https://northloom.example/')]
    registry = EvidenceRegistry()
    company = classify(pages, registry)
    catalog = extract_catalog(pages, registry)
    kw = research_keywords(pages, catalog, company, registry)
    data = {'company':company,'pages':pages,**catalog,**kw,'competitors':[],'social_profiles':[],
            'sources':registry.sources,'evidence':registry.evidence,'qualification_matrix':[],
            'discovery_queries':[],'errors':[],'crawl':{'sitemaps':[],'robots':[]},'raw_pages':[],
            'persistence_backend':'sqlite'}
    data['validation'] = validate(data)
    return data
