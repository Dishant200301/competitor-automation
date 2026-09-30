from app.extraction.pages import extract_page
from app.extraction.catalog import extract_catalog
from app.evidence.registry import EvidenceRegistry
from app.classification.business import classify
from app.validation.engine import validate, validated_projection


def test_real_product_fields_missing_values_stay_missing(dataset):
    p = dataset['products'][0]
    assert p['product_name']=='Linen Shirt'
    assert p['price']=='42.50'
    assert p['currency']=='USD'
    assert p['availability']=='Not found'
    assert p['sale_price'] is None
    assert dataset['company']['industry']=='Fashion & Apparel'
    assert dataset['company']['business_model']=='E-commerce'
    assert dataset['validation']['passed']


def test_collection_is_not_a_product():
    p=extract_page('<h1>Linen Shirts</h1><a href="/collections/linen">Linen</a>', 'https://shop.example/collections/linen')
    data=extract_catalog([p],EvidenceRegistry())
    assert not data['products']
    assert data['categories'][0]['category_name']=='Linen'


def test_unknown_site_never_defaults_to_software_or_india():
    p=extract_page('<h1>Welcome</h1>', 'https://example.com/')
    c=classify([p],EvidenceRegistry())
    assert c['industry']=='Not verified'
    assert c['geographic_market']=='Not verified'
    assert c['business_model']=='Not verified'


def test_zero_products_with_product_links_fails(dataset):
    dataset['products']=[]
    assert not validate(dataset)['passed']


def test_corrupted_evidence_fails(dataset):
    dataset['products'][0]['price']='99999'
    assert not validate(dataset)['passed']


def test_unlinked_claim_is_not_in_report(dataset):
    dataset['company']['revenue']='1 billion'
    assert 'revenue' not in validated_projection(dataset)['company']


def test_no_default_currency():
    p=extract_page('<script type="application/ld+json">{"@type":"Product","name":"Item","offers":{"price":5}}</script>','https://example.com/item')
    data=extract_catalog([p],EvidenceRegistry())
    assert data['products'][0]['currency']=='Not found'
    assert data['price_range_summary']=='Not publicly disclosed'


def test_second_industry():
    p=extract_page('<h1>Software as a service</h1><p>Software API database CRM developer tools for developers and businesses</p>','https://cloud.example/')
    c=classify([p],EvidenceRegistry())
    assert c['industry']=='Technology & Software'
    assert c['business_model']=='SaaS'


def test_filter_urls_are_not_extra_categories():
    page=extract_page('<a href="/collections/linen">Linen</a><a href="/collections/linen?page=2">2</a><a href="/collections/linen?filter.size=M">M</a>','https://shop.example/')
    assert len(extract_catalog([page],EvidenceRegistry())['categories'])==1
