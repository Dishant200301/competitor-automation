"""Explicit Supabase persistence; SQLite is an opt-in development backend."""
import hashlib
import json
import sqlite3
import uuid
from pathlib import Path
from datetime import datetime, timezone
import httpx
from app.core.config import settings


def now(): return datetime.now(timezone.utc).isoformat()


class DatabaseClient:
    def __init__(self, backend=None, path=None):
        self.backend = backend or settings.DATABASE_BACKEND
        self.path = path or settings.SQLITE_DB_PATH
        if self.backend not in {"sqlite", "supabase"}: raise ValueError("Unsupported database backend")
        if self.backend == "sqlite":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
            with self.connect() as c:
                c.execute("CREATE TABLE IF NOT EXISTS intelligence_runs (id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
                c.execute("CREATE TABLE IF NOT EXISTS intelligence_datasets (run_id TEXT PRIMARY KEY, payload TEXT NOT NULL, digest TEXT NOT NULL)")
        self._client = None

    def connect(self): return sqlite3.connect(self.path, timeout=30)

    def remote(self):
        if self._client is None:
            from supabase import create_client
            key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_SECRET_KEY
            if not settings.SUPABASE_URL or not key:
                raise RuntimeError("Supabase URL and service-role key required. Select DATABASE_BACKEND=sqlite explicitly for local development.")
            self._client = create_client(settings.SUPABASE_URL, key)
        return self._client

    def create_run(self, run_id, source_type, source_input, options=None):
        project_id = str(uuid.uuid4())
        run = dict(id=run_id, project_id=project_id, source_type=source_type, source_input=source_input,
                   status="queued", current_step="Queued", progress_percentage=0, error_message=None,
                   pdf_url=None, created_at=now(), updated_at=now(), options=options or {})
        if self.backend == "sqlite":
            with self.connect() as c: c.execute("INSERT INTO intelligence_runs VALUES (?, ?)", (run_id, json.dumps(run)))
        else:
            self.remote().rpc("create_research_run", {"run_record":run}).execute()
        return run

    def get_run(self, run_id):
        if self.backend == "sqlite":
            with self.connect() as c: row = c.execute("SELECT payload FROM intelligence_runs WHERE id=?", (run_id,)).fetchone()
            return json.loads(row[0]) if row else None
        rows = self.remote().table("research_runs").select("*").eq("id", run_id).execute().data
        return rows[0] if rows else None

    def update_run(self, run_id, **changes):
        allowed = {"status", "current_step", "progress_percentage", "error_message", "pdf_url"}
        if set(changes) - allowed: raise ValueError("Unknown run fields")
        changes["updated_at"] = now()
        if self.backend == "sqlite":
            with self.connect() as c:
                row = c.execute("SELECT payload FROM intelligence_runs WHERE id=?", (run_id,)).fetchone()
                if not row: raise ValueError("Unknown run")
                payload = json.loads(row[0]); payload.update(changes)
                c.execute("UPDATE intelligence_runs SET payload=? WHERE id=?", (json.dumps(payload), run_id))
        else: self.remote().table("research_runs").update(changes).eq("id", run_id).execute()

    def save_dataset(self, run_id, dataset):
        # An immutable snapshot is committed atomically alongside normalized rows.
        payload = json.dumps(dataset, sort_keys=True, ensure_ascii=False)
        digest = hashlib.sha256(payload.encode()).hexdigest()
        if self.backend == "sqlite":
            with self.connect() as c:
                c.execute("INSERT INTO intelligence_datasets VALUES (?, ?, ?)", (run_id, payload, digest))
        else:
            self.remote().rpc("commit_research_dataset", {"run_uuid":run_id, "dataset":dataset, "digest":digest}).execute()

    def get_dataset(self, run_id):
        if self.backend == "sqlite":
            with self.connect() as c: row = c.execute("SELECT payload,digest FROM intelligence_datasets WHERE run_id=?", (run_id,)).fetchone()
            if not row: return None
            payload, digest = row
            dataset = json.loads(payload)
        else:
            rows = self.remote().table("research_datasets").select("payload,digest").eq("research_run_id", run_id).execute().data
            if not rows: return None
            dataset, digest = rows[0]["payload"], rows[0]["digest"]
            payload = json.dumps(dataset, sort_keys=True, ensure_ascii=False)
        if hashlib.sha256(payload.encode()).hexdigest() != digest: raise ValueError("Dataset integrity check failed")
        return dataset

    def get_validation_report(self, run_id):
        return (self.get_dataset(run_id) or {}).get("validation")

    def claim_next_run(self):
        if self.backend == "supabase":
            result = self.remote().rpc("claim_research_run", {}).execute().data
            return result if isinstance(result, str) else None
        with self.connect() as c:
            c.execute("BEGIN IMMEDIATE")
            rows = c.execute("SELECT id,payload FROM intelligence_runs ORDER BY rowid").fetchall()
            for run_id,payload in rows:
                run = json.loads(payload)
                if run['status'] != 'queued': continue
                run.update(status='running',current_step='Claimed by worker',updated_at=now())
                c.execute("UPDATE intelligence_runs SET payload=? WHERE id=?",(json.dumps(run),run_id))
                return run_id
        return None

    def get_run_summary(self, run_id):
        data = self.get_dataset(run_id) or {}
        return {
            "company": data.get("company"),
            "competitors": data.get("competitors", []),
            "social_profiles": data.get("social_profiles", []),
            "keywords": data.get("keywords", [])[:25],
            "products": data.get("products", [])[:20],
            "categories": data.get("categories", [])[:20],
            **{key+"_count": len(data.get(key, [])) for key in ("pages", "products", "categories", "services", "keywords")}
        }


db = DatabaseClient()
