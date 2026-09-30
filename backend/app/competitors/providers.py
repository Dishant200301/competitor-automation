"""Optional paid providers never run unless explicitly selected."""
import asyncio
from abc import ABC, abstractmethod
import httpx
from app.core.config import settings


class SearchProvider(ABC):
    @abstractmethod
    async def search(self, query): ...


class FreeSearchProvider(SearchProvider):
    async def search(self, query):
        def search():
            from ddgs import DDGS
            return list(DDGS(timeout=15).text(query, max_results=6))
        rows = await asyncio.to_thread(search)
        return [{"url":r["href"], "title":r.get("title", ""), "snippet":r.get("body", ""), "provider":"ddgs"} for r in rows]


class SerperProvider(SearchProvider):
    async def search(self, query):
        if not settings.effective_serper_key: raise ValueError("SERPER_API_KEY is not configured")
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post("https://google.serper.dev/search", headers={"X-API-KEY":settings.effective_serper_key}, json={"q":query, "num":6})
            response.raise_for_status()
            return [{"url":r["link"], "title":r.get("title", ""), "snippet":r.get("snippet", ""), "provider":"serper"} for r in response.json().get("organic", [])]


def get_provider():
    if settings.SEARCH_PROVIDER == "serper": return SerperProvider()
    return FreeSearchProvider()
