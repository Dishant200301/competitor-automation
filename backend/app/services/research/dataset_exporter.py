import os
import csv
import json
from datetime import datetime, timezone
from typing import Dict, Any, List

class DatasetExporter:
    """
    Exports structured research datasets (CSVs and JSONs) for full transparency,
    traceability, and programmatic downstream consumption.
    """
    def export_all(
        self,
        output_dir: str,
        run_id: str,
        company: Dict[str, Any],
        pages: List[Dict[str, Any]],
        products: List[Dict[str, Any]],
        categories: List[Dict[str, Any]],
        services: List[Dict[str, Any]],
        keywords: List[Dict[str, Any]],
        keyword_clusters: Dict[str, List[str]],
        competitors: List[Dict[str, Any]],
        qualification_matrix: List[Dict[str, Any]],
        social_profiles: List[Dict[str, Any]],
        sources: List[Dict[str, Any]],
        evidence: List[Dict[str, Any]],
        validation_report: Dict[str, Any]
    ):
        os.makedirs(output_dir, exist_ok=True)

        # 1. target_company.json
        self._write_json(os.path.join(output_dir, "target_company.json"), company)

        # 2. pages.csv
        self._write_csv(
            os.path.join(output_dir, "pages.csv"),
            pages,
            fieldnames=["url", "final_url", "http_status", "page_type", "title", "word_count", "canonical_url"]
        )

        # 3. products.csv
        self._write_csv(
            os.path.join(output_dir, "products.csv"),
            products,
            fieldnames=["product_name", "category", "price", "availability", "product_url", "description", "source_url"]
        )

        # 4. categories.csv
        self._write_csv(
            os.path.join(output_dir, "categories.csv"),
            categories,
            fieldnames=["category_name", "slug", "url", "source_page"]
        )

        # 5. services.csv
        self._write_csv(
            os.path.join(output_dir, "services.csv"),
            services,
            fieldnames=["service_name", "category", "description", "source_url"]
        )

        # 6. keywords.csv
        self._write_csv(
            os.path.join(output_dir, "keywords.csv"),
            keywords,
            fieldnames=["keyword", "cluster", "intent", "country", "language", "source", "search_volume", "cpc", "source_url", "date_checked"]
        )

        # 7. keyword_clusters.csv
        cluster_rows = []
        for cluster_name, kws in keyword_clusters.items():
            for kw in kws:
                cluster_rows.append({"cluster_name": cluster_name, "keyword": kw})
        self._write_csv(
            os.path.join(output_dir, "keyword_clusters.csv"),
            cluster_rows,
            fieldnames=["cluster_name", "keyword"]
        )

        # 8. competitors.csv
        self._write_csv(
            os.path.join(output_dir, "competitors.csv"),
            competitors,
            fieldnames=["competitor_name", "website", "domain", "competitor_type", "confidence_level", "google_rank", "pricing_model", "reason", "competitive_overlap"]
        )

        # 9. competitor_qualification_matrix.csv
        self._write_csv(
            os.path.join(output_dir, "competitor_qualification_matrix.csv"),
            qualification_matrix,
            fieldnames=["competitor_name", "website", "industry_match", "product_match", "audience_match", "geography_match", "business_model_match", "active_domain", "overall_qualification", "reason", "evidence_url"]
        )

        # 10. social_profiles.csv
        self._write_csv(
            os.path.join(output_dir, "social_profiles.csv"),
            social_profiles,
            fieldnames=["platform", "url", "username", "verified", "follower_count", "source_url"]
        )

        # 11. sources.csv
        self._write_csv(
            os.path.join(output_dir, "sources.csv"),
            sources,
            fieldnames=["source_id", "company", "source_url", "source_type", "page_title", "date_checked", "status"]
        )

        # 12. evidence.csv
        self._write_csv(
            os.path.join(output_dir, "evidence.csv"),
            evidence,
            fieldnames=["evidence_id", "source_id", "claim", "field", "value", "source_url", "source_title", "evidence_text", "evidence_location", "extraction_method", "confidence", "verification_status", "extracted_at"]
        )

        # 13. validation_report.json
        self._write_json(os.path.join(output_dir, "validation_report.json"), validation_report)

        # 14. research_metadata.json
        meta = {
            "run_id": run_id,
            "target_company": company.get("company_name"),
            "target_domain": company.get("domain"),
            "industry": company.get("industry"),
            "sub_industry": company.get("sub_industry"),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "validation_status": validation_report.get("status"),
            "pages_crawled": len(pages),
            "products_discovered": len(products),
            "categories_discovered": len(categories),
            "keywords_analyzed": len(keywords),
            "competitors_verified": len(competitors),
            "evidence_entries": len(evidence)
        }
        self._write_json(os.path.join(output_dir, "research_metadata.json"), meta)

    def _write_json(self, path: str, data: Any):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _write_csv(self, path: str, rows: List[Dict[str, Any]], fieldnames: List[str]):
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for r in rows:
                writer.writerow(r)

dataset_exporter = DatasetExporter()
