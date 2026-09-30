# Competitor Research & Intelligence

Website first: crawl → extract → infer → discover → independently verify → validate → persist → report.
Python/FastAPI and React. NovaCrawl's pinned MIT extraction core is isolated in `backend/app/crawler/novacrawl_adapter.py`; bounded crawling, robots, sitemaps, security and research orchestration are maintained separately. Reports use Jinja2, CSS and WeasyPrint. No Google Docs API or Supabase Storage.

## Setup

1. Install Python 3.11+ and `pip install -r backend/requirements.txt`.
2. Copy `.env.example` to `.env`, configuring Supabase URL and a **server-side service-role key**.
3. Apply `backend/app/database/migrations/002_research_platform.sql` once in Supabase SQL Editor. The old 001 migration is legacy and not required for this version.
4. Install WeasyPrint native dependencies. On Debian/Ubuntu: `apt install libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0`. On Windows install MSYS2 Pango and set `WEASYPRINT_DLL_DIRECTORIES` to its DLL folder. See https://doc.courtbouillon.org/weasyprint/stable/first_steps.html.
5. Optional JavaScript rendering: `python -m playwright install chromium`.
6. In `backend`, run `python main.py` and `python worker.py` in separate terminals. In `frontend`, run `npm install` then `npm run dev`.

CLI (from backend):

```sh
python research.py https://label-s4u.com/
python research.py https://another-public-site.example/ --company-name 'Optional context'
```

Supabase is the default and failures never silently fall back. For **local development only**, set `DATABASE_BACKEND=sqlite` for the API or use `--database sqlite` on the CLI. Local reports clearly identify SQLite persistence. Credentials already present in `.env` are not rewritten.

Search defaults to the free DDGS provider. Set `SEARCH_PROVIDER=serper` and `SERPER_API_KEY` only if you want that optional paid provider. Any other legacy provider setting selects the free provider. Search failure produces an explicit limitation, not invented candidates. No AI model is needed.

## Data and evidence

All required entity tables have UUID IDs, run relationships, timestamps, uniqueness constraints and lookup indexes. Flexible extracted attributes are stored as JSONB inside normalized entity tables. `commit_research_dataset` atomically inserts the snapshot and entity batches; an existing run snapshot cannot be overwritten. Raw HTML and hashes are retained separately from normalized pages. Evidence links each reported entity field to a fetched source, method and check date. The dataset export includes provenance, search queries, rejection decisions, errors and unverified fields.

Reports reload the persisted snapshot, check its digest, revalidate it, and project only evidence-linked entity fields. A failed extraction or PDF renderer leaves the run failed, never completed with a fictitious URL. Keyword phrases are search hypotheses; frequency is stored separately and never represented as search volume. Currency is never defaulted. Price ranges are per currency and explicitly sampled. Collection headings never count as products.

Company classification is a conservative rule-based inference. Unsupported industries, audiences and markets remain unverified. Geographic market inference requires a country near explicit shipping, delivery or service-availability language; it does not establish complete coverage. DIRECT requires industry, offering, audience, country and business model overlap. ADJACENT permits missing audience/market evidence but still requires actual offering and industry overlap. Marketplace candidates undergo the same crawl verification. No named competitor allowlist or Label S4U-specific logic is used.

## API

- `POST /api/research`: `{"source_input":"https://example.com/", "company_name":"optional", "product_url":"optional", "service_url":"optional", "social_url":"optional"}`. Website is required; optional inputs are context, not claims. Same-site product/service URLs seed the crawl.
- `GET /api/research/{id}/status`, `/summary`, `/validation`
- `GET /api/research/{id}/report/pdf`
- `POST /api/research/{id}/generate-pdf`: persisted validated datasets only
- `GET /api/research/{id}/dataset/research.json` or `products.csv`, `categories.csv`, `services.csv`, `keywords.csv`, `competitors.csv`, `qualification_matrix.csv`, `sources.csv`, `evidence.csv`, `social_profiles.csv`

## Security and deployment boundaries

The default server binds only to loopback. Set `API_TOKEN` for API access when exposing it; requests then require `Authorization: Bearer ...`. The bundled UI is intended for loopback use; deploy a same-origin authenticated gateway for shared access. Supabase anonymous/authenticated clients have no access to the research tables. Keep service-role credentials on the backend.

Crawler DNS answers must all be public; connections are pinned to a checked IP with the original TLS SNI. Redirects are checked again. Robots failures fail closed except 404/410. Crawls enforce response-size, attempt, page, sitemap and depth limits. Playwright requests use the checked transport and block third-party requests and non-GET methods. This may limit some JavaScript websites; limitations are recorded. HTML templates escape data and cannot fetch remote/local resources; CSV cells are formula-escaped.

The API enqueues jobs in the database; `python worker.py` claims them atomically using PostgreSQL row locks. Queued jobs survive API restarts. A hard worker termination can leave a claimed run incomplete; operators should mark that run failed and enqueue a fresh run, preserving existing evidence. Graceful interruptions and one-hour run timeouts mark runs failed. `JOB_MODE=inline` is available for local development only. Before multi-tenant/high-volume production deployment, add tenant ownership policies, rate limits, worker supervision/stale-job recovery, monitored backups and deployment-specific integration tests. Docker Compose starts the API and worker with a shared report volume.

## Verification

```sh
cd backend
python -m pytest tests -q
python test_label_s4u.py --database supabase
cd ../frontend
npm run build
```

The live acceptance harness records individual checks and exits nonzero on missing requirements. An unavailable search service, blocked target, missing Supabase migration, or missing PDF native libraries is a failed/incomplete acceptance run, not a fabricated success.

NovaCrawl upstream: https://github.com/SArfrz/NovaCrawl (commit and MIT notice in `backend/app/crawler/vendor/NOTICE.md`).
