from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes import router as research_router
from app.utils.logger import logger

app = FastAPI(
    title="Competitor Research & Intelligence API",
    version="1.0.0",
    description="Automated competitor discovery, public web crawling, SEO/keyword analysis, and reporting."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(research_router)

@app.get("/api/health")
@app.get("/health")
@app.get("/api/ready")
async def health_check():
    return {
        "status": "healthy",
        "service": "competitor-intelligence",
        "database_backend": settings.DATABASE_BACKEND,
        "job_mode": settings.JOB_MODE,
        "search_provider": "serper" if settings.SEARCH_PROVIDER == "serper" else "ddgs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=True)
