import os
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from app.core.config import settings
from app.utils.logger import logger

class DatabaseClient:
    def __init__(self):
        self.db_path = settings.SQLITE_DB_PATH
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_sqlite()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_sqlite(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS research_runs (
                id TEXT PRIMARY KEY,
                source_type TEXT NOT NULL,
                source_input TEXT NOT NULL,
                status TEXT NOT NULL,
                current_step TEXT,
                progress_percentage INTEGER DEFAULT 0,
                error_message TEXT,
                google_doc_url TEXT,
                pdf_url TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS run_data_store (
                run_id TEXT PRIMARY KEY,
                company TEXT,
                competitors TEXT,
                pages TEXT,
                page_extractions TEXT,
                products TEXT,
                categories TEXT,
                services TEXT,
                keywords TEXT,
                social_profiles TEXT,
                seo TEXT,
                reports TEXT,
                qualification_matrix TEXT,
                validation_report TEXT,
                sources TEXT,
                evidence TEXT
            );
            """)
            conn.commit()

            # Ensure columns exist if table was previously created with fewer columns
            existing_cols = [row[1] for row in cursor.execute("PRAGMA table_info(run_data_store)").fetchall()]
            for new_col in ["categories", "qualification_matrix", "validation_report", "sources", "evidence"]:
                if new_col not in existing_cols:
                    try:
                        cursor.execute(f"ALTER TABLE run_data_store ADD COLUMN {new_col} TEXT")
                        conn.commit()
                    except Exception:
                        pass

    def create_run(self, run_id: str, source_type: str, source_input: str) -> Dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO research_runs (
                    id, source_type, source_input, status, current_step, progress_percentage, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (run_id, source_type, source_input, "queued", "Initialized", 0, now, now))
            cursor.execute("""
                INSERT OR IGNORE INTO run_data_store (run_id) VALUES (?)
            """, (run_id,))
            conn.commit()
        return self.get_run(run_id)

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM research_runs WHERE id = ?", (run_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None

    def update_run(self, run_id: str, **kwargs):
        if not kwargs:
            return
        now = datetime.now(timezone.utc).isoformat()
        kwargs["updated_at"] = now
        set_clauses = [f"{k} = ?" for k in kwargs.keys()]
        values = list(kwargs.values()) + [run_id]

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE research_runs SET {', '.join(set_clauses)} WHERE id = ?", values)
            conn.commit()

    def _save_json_field(self, run_id: str, field_name: str, data: Any):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO run_data_store (run_id) VALUES (?)
            """, (run_id,))
            cursor.execute(f"""
                UPDATE run_data_store SET {field_name} = ? WHERE run_id = ?
            """, (json.dumps(data), run_id))
            conn.commit()

    def _get_json_field(self, run_id: str, field_name: str) -> Any:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT {field_name} FROM run_data_store WHERE run_id = ?", (run_id,))
            row = cursor.fetchone()
            if row and row[0]:
                try:
                    return json.loads(row[0])
                except Exception:
                    return None
        return None

    def save_page(self, page_dict: Dict[str, Any]):
        run_id = page_dict.get("run_id")
        if run_id:
            pages = self.get_pages(run_id)
            pages.append(page_dict)
            self._save_json_field(run_id, "pages", pages)

    def save_page_extraction(self, extraction_dict: Dict[str, Any]):
        run_id = extraction_dict.get("run_id")
        if run_id:
            extractions = self._get_json_field(run_id, "page_extractions") or []
            extractions.append(extraction_dict)
            self._save_json_field(run_id, "page_extractions", extractions)

    def save_pages(self, run_id: str, pages: List[Dict[str, Any]]):
        self._save_json_field(run_id, "pages", pages)

    def get_pages(self, run_id: str) -> List[Dict[str, Any]]:
        return self._get_json_field(run_id, "pages") or []

    def save_company(self, company: Dict[str, Any]) -> str:
        run_id = company.get("run_id")
        company_id = str(uuid.uuid4())
        company["id"] = company_id
        if run_id:
            self._save_json_field(run_id, "company", company)
        return company_id

    def get_company(self, run_id: str) -> Optional[Dict[str, Any]]:
        return self._get_json_field(run_id, "company")

    def save_products(self, products: List[Dict[str, Any]]):
        if not products:
            return
        run_id = products[0].get("run_id")
        if run_id:
            self._save_json_field(run_id, "products", products)

    def get_products(self, run_id: str) -> List[Dict[str, Any]]:
        return self._get_json_field(run_id, "products") or []

    def save_categories(self, run_id: str, categories: List[Dict[str, Any]]):
        self._save_json_field(run_id, "categories", categories)

    def get_categories(self, run_id: str) -> List[Dict[str, Any]]:
        return self._get_json_field(run_id, "categories") or []

    def save_services(self, services: List[Dict[str, Any]]):
        if not services:
            return
        run_id = services[0].get("run_id")
        if run_id:
            self._save_json_field(run_id, "services", services)

    def get_services(self, run_id: str) -> List[Dict[str, Any]]:
        return self._get_json_field(run_id, "services") or []

    def save_social_profiles(self, profiles: List[Dict[str, Any]]):
        if not profiles:
            return
        run_id = profiles[0].get("run_id")
        if run_id:
            self._save_json_field(run_id, "social_profiles", profiles)

    def get_social_profiles(self, run_id: str) -> List[Dict[str, Any]]:
        return self._get_json_field(run_id, "social_profiles") or []

    def save_competitors(self, competitors: List[Dict[str, Any]]):
        if not competitors:
            return
        run_id = competitors[0].get("run_id")
        if run_id:
            self._save_json_field(run_id, "competitors", competitors)

    def get_competitors(self, run_id: str) -> List[Dict[str, Any]]:
        return self._get_json_field(run_id, "competitors") or []

    def save_qualification_matrix(self, run_id: str, matrix: List[Dict[str, Any]]):
        self._save_json_field(run_id, "qualification_matrix", matrix)

    def get_qualification_matrix(self, run_id: str) -> List[Dict[str, Any]]:
        return self._get_json_field(run_id, "qualification_matrix") or []

    def save_validation_report(self, run_id: str, report: Dict[str, Any]):
        self._save_json_field(run_id, "validation_report", report)

    def get_validation_report(self, run_id: str) -> Optional[Dict[str, Any]]:
        return self._get_json_field(run_id, "validation_report")

    def save_sources(self, run_id: str, sources: List[Dict[str, Any]]):
        self._save_json_field(run_id, "sources", sources)

    def get_sources(self, run_id: str) -> List[Dict[str, Any]]:
        return self._get_json_field(run_id, "sources") or []

    def save_evidence(self, run_id: str, evidence: List[Dict[str, Any]]):
        self._save_json_field(run_id, "evidence", evidence)

    def get_evidence(self, run_id: str) -> List[Dict[str, Any]]:
        return self._get_json_field(run_id, "evidence") or []

    def save_seo_data(self, seo: Dict[str, Any]):
        run_id = seo.get("run_id")
        if run_id:
            self._save_json_field(run_id, "seo", seo)

    def save_seo(self, run_id: str, seo: Dict[str, Any]):
        self._save_json_field(run_id, "seo", seo)

    def get_seo(self, run_id: str) -> Optional[Dict[str, Any]]:
        return self._get_json_field(run_id, "seo")

    def save_keywords(self, keywords: List[Dict[str, Any]]):
        if not keywords:
            return
        run_id = keywords[0].get("run_id")
        if run_id:
            self._save_json_field(run_id, "keywords", keywords)

    def get_keywords(self, run_id: str) -> List[Dict[str, Any]]:
        return self._get_json_field(run_id, "keywords") or []

    def save_report(self, report_data: Dict[str, Any]):
        run_id = report_data.get("run_id")
        if run_id:
            reports = self._get_json_field(run_id, "reports") or []
            reports.append(report_data)
            self._save_json_field(run_id, "reports", reports)

    def get_run_summary(self, run_id: str) -> Dict[str, Any]:
        company = self.get_company(run_id)
        competitors = self.get_competitors(run_id)
        pages = self.get_pages(run_id)
        products = self.get_products(run_id)
        categories = self.get_categories(run_id)
        services = self.get_services(run_id)
        keywords = self.get_keywords(run_id)

        return {
            "company": company,
            "competitors": competitors,
            "pages_count": len(pages),
            "products_count": len(products),
            "categories_count": len(categories),
            "services_count": len(services),
            "keywords_count": len(keywords),
        }

db = DatabaseClient()
