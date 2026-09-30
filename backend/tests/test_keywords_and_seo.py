from app.keywords.research import intent
from app.validation.engine import validate
from app.competitors.research import assess, queries_for


def test_keyword_metrics_not_fabricated(dataset):
    assert dataset['keywords']
    assert all(k['search_volume'] is None and k['cpc'] is None for k in dataset['keywords'])
    assert dataset['website_terms']
    dataset['keywords'][0]['search_volume']=1000
    assert not validate(dataset)['passed']


def test_intent():
    assert intent('how to choose linen')[0]=='Informational'
    assert intent('buy linen shirts')[0]=='Transactional'
    assert intent('shirts near me')[0]=='Local'
    assert intent('compare shirts')[0]=='Commercial Investigation'


def test_discovery_is_target_grounded(dataset):
    qs=queries_for(dataset['company'],dataset,dataset['keywords'])
    assert qs
    assert not any('competitors' in q for _,q in qs)
    assert any('Linen Shirts' in q for _,q in qs)


def test_competitor_requires_real_offerings(dataset):
    c=dataset['company']
    empty={'products':[],'categories':dataset['categories'],'services':[]}
    assert assess(c,dataset,c,empty,dataset['pages'])['verification_status']=='NOT QUALIFIED'


def test_unknown_geography_cannot_be_direct(dataset):
    c=dict(dataset['company'],geographic_market='Not verified')
    assert assess(c,dataset,c,dataset,dataset['pages'])['verification_status']=='ADJACENT'


def test_unrelated_industry_rejected(dataset):
    c=dict(dataset['company'],industry='Technology & Software')
    assert assess(dataset['company'],dataset,c,dataset,dataset['pages'])['verification_status']=='NOT QUALIFIED'


def test_conflicting_audience_is_not_adjacent(dataset):
    candidate=dict(dataset['company'],target_audience=['men'])
    assert assess(dataset['company'],dataset,candidate,dataset,dataset['pages'])['verification_status']=='NOT QUALIFIED'
