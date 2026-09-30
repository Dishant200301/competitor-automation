# Competitor Research & Intelligence System

A production-ready competitor research tool built with **FastAPI**, **React + TypeScript + Vite**, **Tailwind CSS**, **Crawl4AI**, **ReportLab**, and **Supabase PostgreSQL**.

---

## Key Principles & Capabilities

- **Factual, Traceable Data**: Every extracted fact, product, keyword, and competitor is traceable directly to its source URL.
- **Deterministic Extraction**: Zero AI hallucinations for core page extraction, SEO discovery, and keyword analysis.
- **Minimal Utilitarian UI**: Clean editorial design with no sidebars, no marketing fluff, and no unnecessary dashboard clutter.
- **SSRF Protection & Safe Crawling**: Enforces domain boundaries, blocking private IP ranges, loopbacks, and cloud metadata endpoints.
- **Resilient Multi-Tier Persistence**: Supabase PostgreSQL persistence with local SQLite fallback for uninterrupted local development and testing.
- **Professional Reports**: A4 PDF report generation using ReportLab and Google Docs integration.

---

## Tech Stack

- **Frontend**: React 19, TypeScript, Vite, Tailwind CSS (Utilitarian Minimalist design)
- **Backend**: Python 3.13, FastAPI, Pydantic v2, Crawl4AI, Trafilatura, BeautifulSoup4, httpx
- **PDF Engine**: ReportLab (A4 pagination, dynamic comparison tables, source references)
- **Database**: Supabase PostgreSQL with Row Level Security (RLS) & Local SQLite fallback

---

## Project Structure

```
competitor-simple/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── SourceTypeSelect.tsx
│   │   │   ├── ResearchInput.tsx
│   │   │   ├── RunResearchButton.tsx
│   │   │   ├── ResearchProgress.tsx
│   │   │   ├── ResearchComplete.tsx
│   │   │   └── ErrorMessage.tsx
│   │   ├── pages/
│   │   │   └── ResearchPage.tsx
│   │   ├── services/
│   │   │   └── api.ts
│   │   ├── types/
│   │   │   └── research.ts
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── index.css
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.js
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── routes.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   └── security.py
│   │   ├── database/
│   │   │   ├── connection.py
│   │   │   └── migrations/
│   │   │       └── 001_initial_schema.sql
│   │   ├── schemas/
│   │   │   └── research.py
│   │   ├── services/
│   │   │   ├── crawler/
│   │   │   │   ├── crawler_engine.py
│   │   │   │   ├── robots_parser.py
│   │   │   │   ├── sitemap_discovery.py
│   │   │   │   └── url_normalizer.py
│   │   │   ├── extractors/
│   │   │   │   ├── company_extractor.py
│   │   │   │   ├── page_classifier.py
│   │   │   │   ├── page_extractor.py
│   │   │   │   ├── product_extractor.py
│   │   │   │   └── service_extractor.py
│   │   │   ├── competitors/
│   │   │   │   ├── competitor_discovery.py
│   │   │   │   ├── competitor_verification.py
│   │   │   │   └── search_provider.py
│   │   │   ├── keywords/
│   │   │   │   └── keyword_extractor.py
│   │   │   ├── reports/
│   │   │   │   ├── google_docs_generator.py
│   │   │   │   ├── pdf_generator.py
│   │   │   │   └── report_builder.py
│   │   │   ├── research/
│   │   │   │   └── orchestrator.py
│   │   │   ├── seo/
│   │   │   │   └── seo_extractor.py
│   │   │   └── social/
│   │   │       └── social_discovery.py
│   │   └── utils/
│   │       └── logger.py
│   ├── tests/
│   │   ├── test_api_endpoints.py
│   │   ├── test_extractors.py
│   │   ├── test_keywords_and_seo.py
│   │   ├── test_pdf_report.py
│   │   └── test_url_and_security.py
│   ├── main.py
│   └── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## Quick Start

### 1. Backend Setup

```bash
# In backend directory
pip install -r requirements.txt

# Start FastAPI backend
python main.py
```

FastAPI server runs on `http://127.0.0.1:8000`. Health check available at `http://127.0.0.1:8000/api/health`.

### 2. Frontend Setup

```bash
# In frontend directory
npm install
npm run dev
```

Vite dev server starts on `http://127.0.0.1:5173`.

### 3. Running Unit & Integration Tests

```bash
# In backend directory
pytest tests/ -v
```

---

## API Reference

- `POST /api/research`: Enqueue a research job (Website, Company, Product, Service, or Social).
- `GET /api/research/{id}/status`: Poll real-time progress and active step.
- `GET /api/research/{id}/summary`: Retrieve structured company info, verified competitors, and discovery metrics.
- `GET /api/research/{id}/report/pdf`: Stream/download generated A4 PDF report.
- `POST /api/research/{id}/generate-google-doc`: Generate Google Doc report via Google Docs API.
