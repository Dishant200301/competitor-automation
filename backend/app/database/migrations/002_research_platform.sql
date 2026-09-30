-- Apply once in the Supabase SQL editor. Uses public schema; no Storage dependency.
BEGIN;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE TABLE IF NOT EXISTS public.projects (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), name text NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS public.research_runs (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), project_id uuid NOT NULL REFERENCES public.projects(id),
 source_type text NOT NULL, source_input text NOT NULL, options jsonb NOT NULL DEFAULT '{}',
 status text NOT NULL DEFAULT 'queued', current_step text, progress_percentage integer NOT NULL DEFAULT 0 CHECK(progress_percentage BETWEEN 0 AND 100),
 error_message text, pdf_url text, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS research_runs_project_idx ON public.research_runs(project_id);
CREATE TABLE IF NOT EXISTS public.research_datasets (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), research_run_id uuid NOT NULL UNIQUE REFERENCES public.research_runs(id),
 payload jsonb NOT NULL, digest text NOT NULL, validated boolean NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
-- Shared envelope: inspectable JSONB preserves vendor-specific product attributes without losing evidence.
DO $$
DECLARE tbl text;
BEGIN
 FOREACH tbl IN ARRAY ARRAY['target_companies','pages','raw_pages','products','categories','services','keywords','keyword_clusters','competitors','competitor_products','competitor_keywords','social_profiles','pricing','sources','evidence','validation_results','research_errors'] LOOP
  EXECUTE format('CREATE TABLE IF NOT EXISTS public.%I (
   id uuid PRIMARY KEY DEFAULT gen_random_uuid(), research_run_id uuid NOT NULL REFERENCES public.research_runs(id),
   url text, domain text, keyword text, competitor_id uuid, source_id uuid,
   record_key text NOT NULL, data jsonb NOT NULL,
   created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
   UNIQUE(research_run_id, record_key))',tbl);
  EXECUTE format('CREATE INDEX IF NOT EXISTS %I ON public.%I(research_run_id)',tbl||'_run_idx',tbl);
  EXECUTE format('CREATE INDEX IF NOT EXISTS %I ON public.%I(url)',tbl||'_url_idx',tbl);
  EXECUTE format('CREATE INDEX IF NOT EXISTS %I ON public.%I(domain)',tbl||'_domain_idx',tbl);
  EXECUTE format('CREATE INDEX IF NOT EXISTS %I ON public.%I(source_id)',tbl||'_source_idx',tbl);
  EXECUTE format('CREATE INDEX IF NOT EXISTS %I ON public.%I(competitor_id)',tbl||'_competitor_idx',tbl);
  EXECUTE format('CREATE INDEX IF NOT EXISTS %I ON public.%I(keyword)',tbl||'_keyword_idx',tbl);
  EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY',tbl);
  EXECUTE format('REVOKE ALL ON public.%I FROM anon, authenticated',tbl);
  EXECUTE format('GRANT SELECT, INSERT ON public.%I TO service_role',tbl);
 END LOOP;
END $$;
ALTER TABLE public.evidence ADD CONSTRAINT evidence_source_fk FOREIGN KEY(source_id) REFERENCES public.sources(id);
ALTER TABLE public.competitor_products ADD CONSTRAINT competitor_product_fk FOREIGN KEY(competitor_id) REFERENCES public.competitors(id);
ALTER TABLE public.competitor_keywords ADD CONSTRAINT competitor_keyword_fk FOREIGN KEY(competitor_id) REFERENCES public.competitors(id);
ALTER TABLE public.projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.research_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.research_datasets ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.projects,public.research_runs,public.research_datasets FROM anon,authenticated;
GRANT SELECT,INSERT,UPDATE ON public.projects,public.research_runs TO service_role;
GRANT SELECT,INSERT ON public.research_datasets TO service_role;
CREATE OR REPLACE FUNCTION public.create_research_run(run_record jsonb) RETURNS uuid
LANGUAGE plpgsql SECURITY INVOKER SET search_path=public AS $$
BEGIN
 INSERT INTO projects(id,name) VALUES ((run_record->>'project_id')::uuid,run_record->>'source_input');
 INSERT INTO research_runs(id,project_id,source_type,source_input,options)
 VALUES ((run_record->>'id')::uuid,(run_record->>'project_id')::uuid,run_record->>'source_type',run_record->>'source_input',coalesce(run_record->'options','{}'));
 RETURN (run_record->>'id')::uuid;
END $$;
CREATE OR REPLACE FUNCTION public.commit_research_dataset(run_uuid uuid,dataset jsonb,digest text) RETURNS uuid
LANGUAGE plpgsql SECURITY INVOKER SET search_path=public AS $$
DECLARE tbl text; key text; rows jsonb; item jsonb; n integer;
BEGIN
 IF NOT EXISTS(SELECT 1 FROM research_runs WHERE id=run_uuid) THEN RAISE EXCEPTION 'Unknown run'; END IF;
 -- Unique run constraint deliberately prevents replacing the original evidence.
 INSERT INTO research_datasets(research_run_id,payload,digest,validated)
 VALUES(run_uuid,dataset,digest,coalesce((dataset->'validation'->>'passed')::boolean,false));
 FOREACH tbl IN ARRAY ARRAY['sources','evidence','target_companies','pages','raw_pages','products','categories','services','keywords','keyword_clusters','competitors','competitor_products','competitor_keywords','social_profiles','pricing','validation_results','research_errors'] LOOP
  key := CASE tbl WHEN 'target_companies' THEN 'company' WHEN 'validation_results' THEN 'validation' WHEN 'research_errors' THEN 'errors' ELSE tbl END;
  rows := coalesce(dataset->key,'[]');
  IF jsonb_typeof(rows)='object' THEN rows:=jsonb_build_array(rows); END IF;
  n:=0;
  FOR item IN SELECT value FROM jsonb_array_elements(rows) LOOP
   n:=n+1;
   EXECUTE format('INSERT INTO public.%I(id,research_run_id,url,domain,keyword,competitor_id,source_id,record_key,data) VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9)',tbl)
    USING coalesce((item->>'id')::uuid,gen_random_uuid()),run_uuid,coalesce(item->>'url',item->>'source_url'),item->>'domain',item->>'keyword',
          (item->>'competitor_id')::uuid,(item->>'source_id')::uuid,coalesce(item->>'id',n::text),item;
  END LOOP;
 END LOOP;
 RETURN run_uuid;
END $$;
REVOKE ALL ON FUNCTION public.create_research_run(jsonb) FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.commit_research_dataset(uuid,jsonb,text) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.create_research_run(jsonb),public.commit_research_dataset(uuid,jsonb,text) TO service_role;
CREATE OR REPLACE FUNCTION public.claim_research_run() RETURNS uuid
LANGUAGE plpgsql SECURITY INVOKER SET search_path=public AS $$
DECLARE job uuid;
BEGIN
 SELECT id INTO job FROM research_runs WHERE status='queued' ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 1;
 IF job IS NOT NULL THEN UPDATE research_runs SET status='running',current_step='Claimed by worker',updated_at=now() WHERE id=job; END IF;
 RETURN job;
END $$;
REVOKE ALL ON FUNCTION public.claim_research_run() FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.claim_research_run() TO service_role;
COMMIT;
