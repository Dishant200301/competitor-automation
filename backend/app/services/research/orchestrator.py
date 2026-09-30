import asyncio
import csv
import json
from pathlib import Path
from urllib.parse import urlsplit
from app.core.config import settings
from app.database.connection import db
from app.crawler.crawl_manager import WebCrawler
from app.crawler.url_discovery import normalize_url, same_site
from app.extraction.catalog import extract_catalog
from app.classification.business import classify
from app.evidence.registry import EvidenceRegistry, record
from app.keywords.research import research_keywords
from app.competitors.research import discover, verify
from app.validation.engine import validate
from app.reports.builder import generate_report
from app.utils.logger import logger


SOCIAL = {'instagram.com':'Instagram','facebook.com':'Facebook','youtube.com':'YouTube','linkedin.com':'LinkedIn',
          'pinterest.com':'Pinterest','x.com':'X','twitter.com':'X','tiktok.com':'TikTok'}


def social_links(pages, registry):
    results, seen = [], set()
    for page in pages:
        for link in page.get('external_links', []):
            try: parsed = urlsplit(link)
            except Exception: continue
            host = (parsed.hostname or '').removeprefix('www.').lower()
            if host not in SOCIAL: continue
            raw_path = parsed.path.strip('/')
            if not raw_path: continue
            lower_path = raw_path.lower()
            if any(x in lower_path for x in ('/share', '/intent', '/sharer', 'sharer.php', '/p/', '/reel/', '/stories/', '/post/', '/hashtag/', '/tags/', '/login', '/signup', 'tr?')):
                continue
            username = raw_path.split('/')[0]
            if not username or username.lower() in ('home', 'explore', 'feed', 'search', 'terms', 'privacy', 'help', 'about', 'login', 'signup'):
                continue
            clean_url = f"https://{host}/{username}"
            if clean_url in seen: continue
            seen.add(clean_url)
            results.append(record({'platform':SOCIAL[host], 'profile_url':clean_url, 'username':username,
                                   'follower_count':None, 'post_count':None, 'recent_activity':'Verified official profile',
                                   'content_themes':'Not verified', 'association':'Linked from official website'}, page, registry, 'official_site_link', clean_url))
    return results


def export_dataset(dataset, directory):
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    (directory/'research.json').write_text(json.dumps(dataset, indent=2, ensure_ascii=False), encoding='utf-8')
    for name in ('products','categories','services','keywords','competitors','qualification_matrix','sources','evidence','social_profiles'):
        rows = dataset.get(name, [])
        if not rows: continue
        fields = sorted({k for row in rows for k in row})
        with (directory/f'{name}.csv').open('w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fields); writer.writeheader()
            for row in rows:
                safe = {}
                for key,value in row.items():
                    if isinstance(value,(dict,list)): value=json.dumps(value,ensure_ascii=False)
                    if isinstance(value,str) and value.lstrip().startswith(('=','+','-','@')): value="'"+value
                    safe[key]=value
                writer.writerow(safe)


class ResearchOrchestrator:
    def __init__(self, database=None, provider=None):
        self.db = database or db
        self.provider = provider

    async def execute_run_async(self, run_id):
        database = self.db
        try:
            run = await asyncio.to_thread(database.get_run, run_id)
            if not run: raise ValueError('Unknown research run')
            url = normalize_url(run['source_input'])
            async def stage(status, progress, message):
                await asyncio.to_thread(database.update_run, run_id, status=status, progress_percentage=progress, current_step=message)
            await stage('crawling', 15, 'Crawling target and preserving original evidence')
            crawler = WebCrawler(run_id=run_id)
            seeds = [v for k,v in run.get('options',{}).items() if k in {'product_url','service_url'} and v and same_site(v,url)]
            pages = await crawler.crawl_site(url, seed_urls=seeds)
            if not pages: raise ValueError('No public indexable target pages could be crawled; no company or competitor claims generated')
            await stage('extracting', 35, 'Extracting target offerings and business signals')
            registry = EvidenceRegistry()
            for page in pages: registry.source(page)
            company = classify(pages, registry)
            catalog = extract_catalog(pages, registry)
            keywords = research_keywords(pages, catalog, company, registry)
            profiles = social_links(pages, registry)
            await stage('discovering_competitors', 55, 'Searching from observed target categories and offerings')
            candidates, queries, search_errors = await discover(company, catalog, keywords['keywords'], self.provider)
            await stage('verifying_competitors', 68, 'Independently crawling and comparing candidate offerings')
            competitors, matrix, competitor_pages, competitor_raw, competitor_errors = await verify(candidates, company, catalog, registry, run_id)
            competitor_products = [{**p, 'competitor_id':c['id']} for c in competitors for p in c.pop('product_records', [])]
            data = {'run_id':run_id, 'persistence_backend':database.backend, 'company':company, 'pages':pages,
                    **catalog, **keywords, 'social_profiles':profiles, 'competitors':competitors, 'competitor_products':competitor_products,
                    'competitor_keywords':[], 'competitor_pages':competitor_pages, 'qualification_matrix':matrix,
                    'discovery_queries':queries, 'sources':registry.sources, 'evidence':registry.evidence,
                    'raw_pages':crawler.raw_records+competitor_raw, 'pricing':[{'product_id':p['id'], 'price':p['price'], 'currency':p['currency'], 'source_url':p['source_url'], 'date_checked':p['date_checked']} for p in catalog['products'] if p['price'] is not None],
                    'crawl':{'sitemaps':crawler.sitemap_records, 'robots':crawler.robots.records, 'discovered_urls':crawler.sitemap_urls},
                    'errors':crawler.errors+search_errors+competitor_errors,
                    'input_context':run.get('options',{})}
            await stage('validating_dataset', 85, 'Validating evidence and classifications')
            data['validation'] = validate(data)
            await asyncio.to_thread(database.save_dataset, run_id, data)
            # Exports and PDF consume the persisted snapshot, never transient extraction objects.
            persisted = await asyncio.to_thread(database.get_dataset, run_id)
            directory = Path(settings.STORAGE_DIR)/'datasets'/run_id
            await asyncio.to_thread(export_dataset, persisted, directory)
            if not data['validation']['passed']:
                raise ValueError('Validation failed: ' + '; '.join(data['validation']['failures']))
            await stage('generating_reports', 94, 'Rendering the validated database snapshot')
            await asyncio.to_thread(generate_report, database, run_id, Path(settings.STORAGE_DIR)/f'Competitor_Report_{run_id}.pdf')
            await asyncio.to_thread(database.update_run, run_id, status='completed', current_step='Research complete; review limitations in the report', progress_percentage=100, pdf_url=f'/api/research/{run_id}/report/pdf')
        except Exception as exc:
            logger.error('Research run %s failed (%s)', run_id, type(exc).__name__)
            await asyncio.to_thread(database.update_run, run_id, status='failed', progress_percentage=100, current_step='Research stopped', error_message=str(exc)[:500])


orchestrator = ResearchOrchestrator()
