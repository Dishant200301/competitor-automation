"""Live acceptance harness. Never imports Label-specific rules into application code."""
import argparse
import asyncio
import json
import uuid
from pathlib import Path
from app.database.connection import DatabaseClient
from app.services.research.orchestrator import ResearchOrchestrator
from app.core.config import settings


async def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--database',choices=['supabase','sqlite'],default='supabase')
    parser.add_argument('--run-id',help='Inspect an existing completed run instead of recrawling')
    args=parser.parse_args()
    database=DatabaseClient(args.database)
    run_id=args.run_id or str(uuid.uuid4())
    if not args.run_id:
        database.create_run(run_id,'website','https://label-s4u.com/')
        print('Run:',run_id,flush=True)
        await ResearchOrchestrator(database).execute_run_async(run_id)
    run=database.get_run(run_id)
    data=database.get_dataset(run_id) or {}
    company=data.get('company',{})
    labels=' '.join(c['category_name'].lower()+' '+c['url'].lower() for c in data.get('categories',[]))
    checks={
        'website_crawled':bool(data.get('pages')),
        'sitemap_discovered':bool(data.get('crawl',{}).get('sitemaps')),
        'robots_handled':bool(data.get('crawl',{}).get('robots')),
        'individual_products_extracted':bool(data.get('products')),
        'ecommerce_detected':company.get('business_model')=='E-commerce',
        'fashion_classified':company.get('industry')=='Fashion & Apparel',
        'keyword_hypotheses':bool(data.get('keywords')),
        'intent_classified':all(k.get('intent') for k in data.get('keywords',[])),
        'competitor_candidates_discovered':bool(data.get('qualification_matrix')),
        'competitors_independently_verified':bool(data.get('competitors')),
        'competitor_classes_valid':all(c['competitor_type'] in {'DIRECT','ADJACENT','MARKETPLACE / SEARCH'} for c in data.get('competitors',[])),
        'rejections_recorded':any(c['verification_status']=='NOT QUALIFIED' for c in data.get('qualification_matrix',[])),
        'evidence_stored':bool(data.get('evidence')),
        'supabase_persistence':database.backend=='supabase' and bool(data),
        'validation_passes':data.get('validation',{}).get('passed',False),
        'pdf_generated':run is not None and run['status']=='completed' and (Path(settings.STORAGE_DIR)/f'Competitor_Report_{run_id}.pdf').is_file(),
        'missing_metrics_not_invented':all(k.get('search_volume') is None or k.get('volume_source') for k in data.get('keywords',[])),
    }
    for expected in ('ethnic-suit','co-ord','anarkali','sharara','indo-western','kaftan','farshi','lehenga','shirts','ready-to-ship','new-in'):
        checks['collection_'+expected]=expected in labels
    output={'run_id':run_id,'checks':checks,'passed':all(checks.values()),'counts':{k:len(data.get(k,[])) for k in ('pages','products','categories','keywords','competitors','evidence')}}
    path=Path(settings.STORAGE_DIR)/'datasets'/run_id/'acceptance.json';path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(output,indent=2),encoding='utf-8')
    print(json.dumps(output,indent=2))
    if not output['passed']: raise SystemExit(1)

if __name__=='__main__':asyncio.run(main())
