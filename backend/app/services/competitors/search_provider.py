import os
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from datetime import datetime, timezone
import httpx
from app.core.config import settings
from app.utils.logger import logger

class SearchResult:
    def __init__(self, title: str, url: str, snippet: str, position: int = 0):
        self.title = title
        self.url = url
        self.snippet = snippet
        self.position = position
        self.retrieved_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "position": self.position,
            "retrieved_at": self.retrieved_at
        }

class BaseSearchProvider(ABC):
    @abstractmethod
    async def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        pass

class SerpApiProvider(BaseSearchProvider):
    """
    1. Primary Search Provider via serpapi.com (Google Search).
    """
    def __init__(self, api_key: str = ""):
        self.api_key = api_key or settings.effective_serpapi_key

    async def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        results: List[SearchResult] = []
        if not self.api_key:
            return results

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.get(
                    "https://serpapi.com/search.json",
                    params={
                        "q": query,
                        "api_key": self.api_key,
                        "engine": "google",
                        "num": max_results
                    }
                )
                if res.status_code == 200:
                    data = res.json()
                    if "error" in data:
                        logger.warning(f"SerpApi quota/credit ended: {data.get('error')}. Seamlessly proceeding to next provider.")
                        return []
                    organic = data.get("organic_results", [])
                    for i, r in enumerate(organic):
                        results.append(SearchResult(
                            title=r.get("title", ""),
                            url=r.get("link", ""),
                            snippet=r.get("snippet", ""),
                            position=r.get("position", i + 1)
                        ))
                    if results:
                        logger.info(f"SerpApi (1st) returned {len(results)} results for '{query}'")
                        return results
                    else:
                        logger.warning(f"SerpApi returned 0 organic results for '{query}'. Seamlessly proceeding to next provider.")
                else:
                    logger.warning(f"SerpApi credit/status error (HTTP {res.status_code}): {res.text[:120]}. Seamlessly proceeding to next provider.")
        except Exception as e:
            logger.warning(f"SerpApi request exception for '{query}': {e}. Seamlessly proceeding to next provider.")

        return results

class TavilyProvider(BaseSearchProvider):
    """
    2. Secondary Search Provider via api.tavily.com (AI Search).
    """
    def __init__(self, api_key: str = ""):
        self.api_key = api_key or settings.TAVILY_API_KEY

    async def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        results: List[SearchResult] = []
        if not self.api_key:
            return results

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": self.api_key,
                        "query": query,
                        "max_results": max_results,
                        "search_depth": "basic",
                        "include_domains": []
                    }
                )
                if res.status_code == 200:
                    data = res.json()
                    if "error" in data:
                        logger.warning(f"Tavily quota/credit ended: {data.get('error')}. Seamlessly proceeding to next provider.")
                        return []
                    for i, r in enumerate(data.get("results", [])):
                        results.append(SearchResult(
                            title=r.get("title", ""),
                            url=r.get("url", ""),
                            snippet=r.get("content", ""),
                            position=i + 1
                        ))
                    if results:
                        logger.info(f"Tavily (2nd) returned {len(results)} results for '{query}'")
                        return results
                    else:
                        logger.warning(f"Tavily returned 0 results for '{query}'. Seamlessly proceeding to next provider.")
                else:
                    logger.warning(f"Tavily credit/status error (HTTP {res.status_code}): {res.text[:120]}. Seamlessly proceeding to next provider.")
        except Exception as e:
            logger.warning(f"Tavily request exception for '{query}': {e}. Seamlessly proceeding to next provider.")

        return results

class SerperProvider(BaseSearchProvider):
    """
    3. Tertiary Search Provider via google.serper.dev.
    """
    def __init__(self, api_key: str = ""):
        self.api_key = api_key or settings.effective_serper_key

    async def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        results: List[SearchResult] = []
        if not self.api_key:
            return results

        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                res = await client.post(
                    "https://google.serper.dev/search",
                    headers={
                        "X-API-KEY": self.api_key,
                        "Content-Type": "application/json"
                    },
                    json={
                        "q": query,
                        "num": max_results
                    }
                )
                if res.status_code == 200:
                    data = res.json()
                    organic = data.get("organic", [])
                    for i, r in enumerate(organic):
                        results.append(SearchResult(
                            title=r.get("title", ""),
                            url=r.get("link", ""),
                            snippet=r.get("snippet", ""),
                            position=r.get("position", i + 1)
                        ))
                    if results:
                        logger.info(f"Serper (3rd) returned {len(results)} results for '{query}'")
                        return results
                    else:
                        logger.warning(f"Serper returned 0 organic results for '{query}'. Seamlessly proceeding to next provider.")
                else:
                    logger.warning(f"Serper credit/status error (HTTP {res.status_code}): {res.text[:120]}. Seamlessly proceeding to next provider.")
        except Exception as e:
            logger.warning(f"Serper request exception for '{query}': {e}. Seamlessly proceeding to next provider.")

        return results

class DuckDuckGoProvider(BaseSearchProvider):
    """
    4. Quaternary Free Fallback Provider via DuckDuckGo.
    """
    async def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        results: List[SearchResult] = []
        try:
            from duckduckgo_search import DDGS
            ddgs = DDGS()
            raw_results = ddgs.text(query, max_results=max_results)
            for i, r in enumerate(raw_results or []):
                results.append(SearchResult(
                    title=r.get("title", ""),
                    url=r.get("href", ""),
                    snippet=r.get("body", ""),
                    position=i + 1
                ))
            if results:
                logger.info(f"DuckDuckGo (4th Fallback) returned {len(results)} results for '{query}'")
        except Exception as e:
            logger.warning(f"DuckDuckGo fallback search exception for '{query}': {e}")
        return results

class CompositeSearchProvider(BaseSearchProvider):
    """
    Automatic Failover Chain (No crash/error if credit expires):
    1. First: SerpApi (serpapi.com)
       If credit runs out or errors ->
    2. Second: Tavily (api.tavily.com)
       If credit runs out or errors ->
    3. Third: Serper (google.serper.dev)
       If credit runs out or errors ->
    4. Fourth: DuckDuckGo (Free unlimited fallback)
    """
    def __init__(self):
        self.serpapi = SerpApiProvider()
        self.tavily = TavilyProvider()
        self.serper = SerperProvider()
        self.ddg = DuckDuckGoProvider()

    async def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        # Step 1: SerpApi (1st)
        if settings.effective_serpapi_key:
            results = await self.serpapi.search(query, max_results=max_results)
            if results:
                return results
            logger.info("SerpApi (1st) credit exhausted or returned 0 results. Seamlessly switching to Tavily (2nd)...")

        # Step 2: Tavily (2nd)
        if settings.TAVILY_API_KEY:
            results = await self.tavily.search(query, max_results=max_results)
            if results:
                return results
            logger.info("Tavily (2nd) credit exhausted or returned 0 results. Seamlessly switching to Serper (3rd)...")

        # Step 3: Serper (3rd)
        if settings.effective_serper_key:
            results = await self.serper.search(query, max_results=max_results)
            if results:
                return results
            logger.info("Serper (3rd) credit exhausted or returned 0 results. Seamlessly switching to DuckDuckGo (4th)...")

        # Step 4: DuckDuckGo (4th fallback)
        return await self.ddg.search(query, max_results=max_results)

search_provider = CompositeSearchProvider()
