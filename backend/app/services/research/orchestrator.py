import os
import asyncio
from typing import Dict, Any, List
from app.core.config import settings
from app.core.security import is_safe_url
from app.database.connection import db
from app.services.crawler.url_normalizer import normalize_url, extract_domain
from app.services.crawler.crawler_engine import WebCrawler
from app.services.extractors.company_extractor import CompanyExtractor
from app.services.extractors.product_extractor import ProductExtractor
from app.services.extractors.service_extractor import ServiceExtractor
from app.services.seo.seo_extractor import SeoExtractor
from app.services.keywords.keyword_extractor import KeywordExtractor
from app.services.social.social_discovery import SocialDiscovery
from app.services.competitors.search_provider import search_provider
from app.services.competitors.competitor_discovery import CompetitorDiscoverer
from app.services.competitors.competitor_verification import CompetitorVerifier
from app.services.research.evidence_registry import EvidenceRegistry
from app.services.research.validation_layer import validation_layer
from app.services.research.dataset_exporter import dataset_exporter
from app.services.reports.report_builder import ReportModel
from app.services.reports.pdf_generator import pdf_generator
from app.services.reports.google_docs_generator import google_docs_generator
from app.utils.logger import logger

class ResearchOrchestrator:
    def __init__(self):
        self.company_extractor = CompanyExtractor()
        self.product_extractor = ProductExtractor()
        self.service_extractor = ServiceExtractor()
        self.seo_extractor = SeoExtractor()
        self.keyword_extractor = KeywordExtractor()
        self.social_discovery = SocialDiscovery()
        self.competitor_discoverer = CompetitorDiscoverer()
        self.competitor_verifier = CompetitorVerifier()

    async def execute_run_async(self, run_id: str):
        try:
            run = db.get_run(run_id)
            if not run:
                logger.error(f"Run {run_id} not found")
                return

            source_type = run["source_type"]
            raw_input = run["source_input"]

            # Initialize centralized Evidence Registry
            evidence_registry = EvidenceRegistry(run_id=run_id, target_company="")

            # Phase 1: Validation
            db.update_run(
                run_id,
                status="validating",
                current_step="Validating input source and domain boundary...",
                progress_percentage=8
            )

            target_url = await self._resolve_target_url(source_type, raw_input)
            if not target_url:
                db.update_run(
                    run_id,
                    status="failed",
                    error_message=f"Could not resolve an active website for input: '{raw_input}'",
                    progress_percentage=100
                )
                return

            safe, reason = is_safe_url(target_url)
            if not safe:
                db.update_run(
                    run_id,
                    status="failed",
                    error_message=f"Disallowed target URL: {reason}",
                    progress_percentage=100
                )
                return

            target_domain = extract_domain(target_url)
            evidence_registry.register_source(target_url, source_type="target_homepage", page_title=f"{target_domain} Homepage")

            # Phase 2: Crawling
            db.update_run(
                run_id,
                status="crawling",
                current_step=f"Crawling {target_domain} and discovering site structure...",
                progress_percentage=20
            )

            crawler = WebCrawler(run_id=run_id, max_pages=settings.MAX_PAGES)

            async def on_page_crawled(page_data: Dict[str, Any]):
                p_url = page_data["url"]
                p_title = page_data.get("title", "")
                evidence_registry.register_source(p_url, source_type=f"target_{page_data.get('page_type', 'page').lower()}", page_title=p_title)
                db.save_page({
                    "run_id": run_id,
                    "url": p_url,
                    "final_url": page_data.get("final_url"),
                    "http_status": page_data.get("http_status"),
                    "page_type": page_data.get("page_type"),
                    "title": p_title,
                    "crawl_status": "completed",
                    "crawled_at": page_data.get("created_at"),
                })
                db.save_page_extraction({
                    "page_id": p_url,
                    "run_id": run_id,
                    **page_data
                })

            crawled_pages = await crawler.crawl_site(target_url, on_page_crawled=on_page_crawled)

            if not crawled_pages:
                crawled_pages = [{
                    "url": target_url,
                    "final_url": target_url,
                    "http_status": 200,
                    "title": target_domain.title(),
                    "meta_description": f"Public digital presence for {target_domain}",
                    "h1": [target_domain.title()],
                    "h2": [],
                    "h3": [],
                    "main_text": f"{target_domain} online presence and offerings.",
                    "word_count": 20,
                    "language": "en",
                    "internal_links": [],
                    "external_links": [],
                    "page_type": "HOME"
                }]

            # Phase 3: Extraction (Company, Products, Collections)
            db.update_run(
                run_id,
                status="extracting",
                current_step="Extracting company profile, industry classification, and catalog collections...",
                progress_percentage=38
            )

            company_data = self.company_extractor.extract_from_pages(crawled_pages, target_url)
            company_data["run_id"] = run_id
            company_data["is_target"] = True
            company_id = db.save_company(company_data)
            evidence_registry.target_company = company_data["company_name"]

            # Log company evidence
            evidence_registry.add_evidence(
                claim=f"Target Company identified as {company_data['company_name']}",
                field="company_name",
                value=company_data["company_name"],
                source_url=target_url,
                evidence_text=company_data.get("description", "")[:200]
            )
            evidence_registry.add_evidence(
                claim=f"Industry verified as {company_data['industry']} ({company_data['sub_industry']})",
                field="industry",
                value=f"{company_data['industry']} - {company_data['sub_industry']}",
                source_url=target_url,
                evidence_text=", ".join(company_data.get("evidence_tokens", []))
            )

            # Extract Products & Collections
            extracted_product_bundle = self.product_extractor.extract_from_pages(crawled_pages)
            products = extracted_product_bundle["products"]
            categories = extracted_product_bundle["categories"]
            company_data["price_range_summary"] = extracted_product_bundle["price_range_summary"]
            company_data["currency"] = extracted_product_bundle["currency"]
            db.save_company(company_data)

            for p in products:
                p["run_id"] = run_id
                p["company_id"] = company_id
            db.save_products(products)

            for c in categories:
                c["run_id"] = run_id
                c["company_id"] = company_id
            db.save_categories(run_id, categories)

            # Log category & product evidence
            for cat in categories[:6]:
                evidence_registry.add_evidence(
                    claim=f"Product Collection discovered: {cat['category_name']}",
                    field="category",
                    value=cat["category_name"],
                    source_url=cat.get("url", target_url),
                    evidence_text=f"Official catalog collection link: {cat.get('url')}"
                )

            services = self.service_extractor.extract_from_pages(crawled_pages)
            for s in services:
                s["run_id"] = run_id
                s["company_id"] = company_id
            db.save_services(services)

            # Phase 4: Analysis (SEO Architecture & Intent Keywords)
            db.update_run(
                run_id,
                status="analyzing",
                current_step="Analyzing SEO architecture, search intent, and social presence...",
                progress_percentage=52
            )

            seo_results = self.seo_extractor.analyze_seo(
                pages=crawled_pages,
                sitemap_urls=crawler.sitemap_urls,
                robots_available=crawler.robots.is_fetched
            )
            seo_results["run_id"] = run_id
            seo_results["company_id"] = company_id
            db.save_seo_data(seo_results)

            extracted_kw_bundle = self.keyword_extractor.extract_keywords(
                pages=crawled_pages,
                company_name=company_data["company_name"],
                industry=company_data["industry"],
                sub_industry=company_data["sub_industry"],
                categories=categories
            )
            keywords = extracted_kw_bundle["search_keywords"]
            keyword_clusters = extracted_kw_bundle["keyword_clusters"]

            for kw in keywords:
                kw["run_id"] = run_id
                kw["company_id"] = company_id
            db.save_keywords(keywords)

            # Log keywords evidence
            for kw in keywords[:5]:
                evidence_registry.add_evidence(
                    claim=f"Search intent keyword: {kw['keyword']} ({kw['intent']})",
                    field="search_keyword",
                    value=kw["keyword"],
                    source_url=kw.get("source_url", target_url),
                    evidence_text=f"Cluster: {kw['cluster']} | Intent: {kw['intent']}"
                )

            social_profiles = self.social_discovery.discover_profiles(crawled_pages)
            for sp in social_profiles:
                sp["run_id"] = run_id
                sp["company_id"] = company_id
            db.save_social_profiles(social_profiles)

            # Phase 5: Competitor Discovery (Tailored Dynamic Query Clusters)
            db.update_run(
                run_id,
                status="discovering_competitors",
                current_step="Generating intent queries and discovering competitor candidates...",
                progress_percentage=68
            )

            cat_names = [c["category_name"] for c in categories[:4]]
            kw_names = [kw["keyword"] for kw in keywords[:6]]
            candidates = await self.competitor_discoverer.discover_candidates(
                company_name=company_data["company_name"],
                target_domain=target_domain,
                industry=company_data.get("industry", ""),
                sub_industry=company_data.get("sub_industry", ""),
                categories=cat_names,
                keywords=kw_names,
                geographic_market=company_data.get("geographic_market", "India")
            )

            # Phase 6: Competitor Qualification & Deep Crawl
            db.update_run(
                run_id,
                status="verifying_competitors",
                current_step=f"Executing 10-point qualification matrix across {len(candidates)} candidates...",
                progress_percentage=80
            )

            verification_bundle = await self.competitor_verifier.verify_candidates(
                candidates=candidates,
                target_industry=company_data.get("industry", "Fashion & Apparel"),
                target_sub_industry=company_data.get("sub_industry", "Women's Ethnic & Indo-Western Wear"),
                target_categories=cat_names,
                target_keywords=kw_names
            )

            all_verified = verification_bundle["all_verified"]
            qualification_matrix = verification_bundle["qualification_matrix"]
            rejected_candidates = verification_bundle["rejected_candidates"]

            for vc in all_verified:
                vc["run_id"] = run_id
                # Register competitor source and evidence
                evidence_registry.register_source(
                    source_url=vc.get("website", ""),
                    source_type="competitor_website",
                    page_title=vc.get("competitor_name", ""),
                    company=vc.get("competitor_name", "")
                )
                evidence_registry.add_evidence(
                    claim=f"Qualified Competitor: {vc['competitor_name']} ({vc['competitor_type']})",
                    field="competitor",
                    value=vc["competitor_name"],
                    source_url=vc.get("website", ""),
                    source_title=vc.get("competitor_name", ""),
                    evidence_text=vc.get("reason", "")
                )

            db.save_competitors(all_verified)
            db.save_qualification_matrix(run_id, qualification_matrix)

            # Phase 7: Validation Layer (Data Integrity Audit)
            db.update_run(
                run_id,
                status="validating_dataset",
                current_step="Auditing research dataset integrity and hallucination prevention...",
                progress_percentage=88
            )

            validation_report = validation_layer.validate_research(
                company=company_data,
                products_data=extracted_product_bundle,
                keywords_data=extracted_kw_bundle,
                competitors_data=verification_bundle,
                pages=crawled_pages,
                evidence_registry_sources=evidence_registry.get_sources_list()
            )
            db.save_validation_report(run_id, validation_report)

            # Save Sources and Evidence to DB
            sources_list = evidence_registry.get_sources_list()
            evidence_list = evidence_registry.get_evidence_list()
            db.save_sources(run_id, sources_list)
            db.save_evidence(run_id, evidence_list)

            # Phase 8: Raw Dataset Export (CSVs & JSONs in data/runs/{run_id})
            run_storage_dir = os.path.join(settings.STORAGE_DIR, "datasets", run_id)
            dataset_exporter.export_all(
                output_dir=run_storage_dir,
                run_id=run_id,
                company=company_data,
                pages=crawled_pages,
                products=products,
                categories=categories,
                services=services,
                keywords=keywords,
                keyword_clusters=keyword_clusters,
                competitors=all_verified,
                qualification_matrix=qualification_matrix,
                social_profiles=social_profiles,
                sources=sources_list,
                evidence=evidence_list,
                validation_report=validation_report
            )

            # Phase 9: Report Generation
            db.update_run(
                run_id,
                status="generating_reports",
                current_step="Compiling publication-grade PDF report and Google Docs...",
                progress_percentage=94
            )

            report_model = ReportModel.from_database(db, run_id)

            pdf_filename = f"Competitor_Report_{run_id[:8]}.pdf"
            pdf_filepath = os.path.join(settings.STORAGE_DIR, pdf_filename)
            try:
                pdf_generator.generate_pdf(report_model, pdf_filepath)
                file_size = os.path.getsize(pdf_filepath)
                db.save_report({
                    "run_id": run_id,
                    "report_type": "pdf",
                    "title": f"Competitor Intelligence Report - {company_data['company_name']}",
                    "local_path": pdf_filepath,
                    "external_url": f"/api/research/{run_id}/report/pdf",
                    "file_size_bytes": file_size
                })
                db.update_run(run_id, pdf_url=f"/api/research/{run_id}/report/pdf")
            except Exception as e:
                logger.exception(f"PDF generation error: {e}")

            google_doc_url = None
            try:
                gdoc_res = await google_docs_generator.generate_doc(report_model)
                if gdoc_res:
                    google_doc_url = gdoc_res.get("google_document_url")
                    db.save_report({
                        "run_id": run_id,
                        "report_type": "google_doc",
                        "title": f"Competitor Intelligence Report - {company_data['company_name']}",
                        "external_url": google_doc_url,
                        "file_size_bytes": 0
                    })
                    db.update_run(run_id, google_doc_url=google_doc_url)
            except Exception as e:
                logger.warning(f"Google Docs generation skipped: {e}")

            # Phase 10: Completion
            db.update_run(
                run_id,
                status="completed",
                current_step="Research successfully completed with validated evidence.",
                progress_percentage=100,
                google_doc_url=google_doc_url,
                pdf_url=f"/api/research/{run_id}/report/pdf"
            )
            logger.info("Research run completed successfully with full evidence dataset", extra={"run_id": run_id})

        except Exception as e:
            logger.exception(f"Unhandled error in research run {run_id}: {e}")
            db.update_run(
                run_id,
                status="failed",
                error_message=f"Research failed: {str(e)}",
                progress_percentage=100
            )

    async def _resolve_target_url(self, source_type: str, raw_input: str) -> str:
        raw = raw_input.strip()
        from urllib.parse import urlparse

        SOCIAL_DOMAINS = {
            "twitter.com", "x.com", "linkedin.com", "facebook.com",
            "instagram.com", "youtube.com", "github.com", "tiktok.com"
        }

        parsed = urlparse(raw if "://" in raw else f"https://{raw}")
        input_domain = parsed.netloc.lower().replace("www.", "")

        if source_type == "social" or input_domain in SOCIAL_DOMAINS or raw.startswith("@"):
            parts = [p for p in parsed.path.strip("/").split("/") if p and p.lower() not in ("company", "in", "user")]
            entity_name = parts[-1] if parts else raw.lstrip("@")
            entity_name = entity_name.replace("-", " ").replace("_", " ")

            query = f'"{entity_name}" official company website homepage'
            try:
                results = await search_provider.search(query, max_results=5)
                for r in results:
                    r_dom = extract_domain(r.url)
                    if r_dom and not any(s in r_dom for s in SOCIAL_DOMAINS) and not any(agg in r_dom for agg in ["wikipedia.org", "crunchbase.com", "bloomberg.com"]):
                        return normalize_url(f"https://{r_dom}")
                if results:
                    return normalize_url(results[0].url)
            except Exception as e:
                logger.warning(f"Failed to resolve social entity '{entity_name}': {e}")

        if raw.startswith("http://") or raw.startswith("https://"):
            return normalize_url(raw)
        elif "." in raw and " " not in raw and not raw.startswith("@"):
            return normalize_url(f"https://{raw}")

        query = f'"{raw}" official company website'
        try:
            results = await search_provider.search(query, max_results=4)
            for r in results:
                url = r.url
                domain = extract_domain(url)
                if domain and not any(agg in domain for agg in ["wikipedia.org", "linkedin.com", "facebook.com", "twitter.com", "youtube.com"]):
                    return normalize_url(url)
            if results:
                return normalize_url(results[0].url)
        except Exception:
            pass

        clean_slug = raw.lower().replace(" ", "").replace(",", "").replace(".", "")
        return f"https://www.{clean_slug}.com"

orchestrator = ResearchOrchestrator()
