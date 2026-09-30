import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent

class Settings(BaseSettings):
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    MAX_PAGES: int = 15
    MAX_DEPTH: int = 3
    CONCURRENT_REQUESTS: int = 5
    REQUEST_TIMEOUT: int = 15
    REQUEST_DELAY: float = 1.0
    MAX_RETRIES: int = 3
    CRAWLER_USER_AGENT: str = "UniversalCompetitorIntelligenceBot/1.0 (+https://github.com/competitor-intelligence; polite research crawler)"

    # Search Providers Priority Order: 1. SerpApi -> 2. Tavily -> 3. Serper -> 4. DuckDuckGo
    SEARCH_PROVIDER: str = "ddgs"
    SERPAPI_API_KEY: str = ""
    serpapi: str = ""
    TAVILY_API_KEY: str = ""
    SERPER_API_KEY: str = ""
    serper: str = ""

    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    SUPABASE_URL: str = ""
    SUPABASE_SECRET_KEY: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    DATABASE_BACKEND: str = "sqlite"
    ENABLE_JAVASCRIPT: bool = True
    MAX_CANDIDATES: int = 8
    COMPETITOR_CRAWL_TIMEOUT: int = 90
    MAX_SEARCH_QUERIES: int = 6
    MAX_RESPONSE_BYTES: int = 5000000
    API_TOKEN: str = ""
    JOB_MODE: str = "inline"
    WEASYPRINT_DLL_DIRECTORIES: str = ""

    SQLITE_DB_PATH: str = str(ROOT_DIR / "backend" / "data" / "research.db")
    STORAGE_DIR: str = str(ROOT_DIR / "backend" / "data" / "reports")

    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REFRESH_TOKEN: str = ""

    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def effective_serper_key(self) -> str:
        return (self.SERPER_API_KEY or self.serper or "").strip()

    @property
    def effective_serpapi_key(self) -> str:
        return (self.SERPAPI_API_KEY or self.serpapi or "").strip()

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

settings = Settings()

os.makedirs(os.path.dirname(settings.SQLITE_DB_PATH), exist_ok=True)
os.makedirs(settings.STORAGE_DIR, exist_ok=True)
