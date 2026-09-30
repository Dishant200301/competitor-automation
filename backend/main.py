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
        "search_chain_priority": ["1_serpapi", "2_tavily", "3_serper", "4_duckduckgo"],
        "serpapi_configured": bool(settings.effective_serpapi_key),
        "tavily_configured": bool(settings.TAVILY_API_KEY),
        "serper_configured": bool(settings.effective_serper_key)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=True)
