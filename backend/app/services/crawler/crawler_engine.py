import asyncio
from typing import List, Dict, Any, Optional, Callable
import httpx
from bs4 import BeautifulSoup
from app.core.config import settings
from app.core.security import is_safe_url
from app.services.crawler.url_normalizer import normalize_url, extract_domain, is_same_domain
from app.services.crawler.robots_parser import robots_checker
from app.services.crawler.sitemap_discovery import discover_sitemap_urls
from app.services.extractors.page_classifier import classify_page_url
from app.services.extractors.page_extractor import extract_structured_page_data
from app.utils.logger import logger

class RobotsState:
    def __init__(self, is_fetched: bool = True):
        self.is_fetched = is_fetched

class WebCrawler:
    def __init__(self, run_id: str = "", max_pages: int = 15):
        self.run_id = run_id
        self.max_pages = max_pages
        self.sitemap_urls: List[str] = []
        self.robots = RobotsState(is_fetched=True)
        self.headers = {"User-Agent": settings.CRAWLER_USER_AGENT}

    async def crawl_site(
        self,
        start_url: str,
        on_page_crawled: Optional[Callable[[Dict[str, Any]], Any]] = None
    ) -> List[Dict[str, Any]]:
        visited = set()
        queue = [normalize_url(start_url)]
        crawled_results: List[Dict[str, Any]] = []

        try:
            self.sitemap_urls = await discover_sitemap_urls(start_url, limit=10)
            if self.sitemap_urls:
                for s_url in self.sitemap_urls[:5]:
                    norm = normalize_url(s_url)
                    if norm not in queue:
                        queue.append(norm)
        except Exception as e:
            logger.debug(f"Sitemap discovery error: {e}")

        async with httpx.AsyncClient(headers=self.headers, timeout=settings.REQUEST_TIMEOUT, follow_redirects=True) as client:
            while queue and len(crawled_results) < self.max_pages:
                current_url = queue.pop(0)
                if current_url in visited:
                    continue
                visited.add(current_url)

                safe, _ = is_safe_url(current_url)
                if not safe:
                    continue

                try:
                    can_fetch = await robots_checker.can_fetch(current_url)
                    if not can_fetch:
                        continue

                    res = await client.get(current_url)
                    if res.status_code == 200:
                        content_type = res.headers.get("content-type", "")
                        if "html" not in content_type:
                            continue

                        final_url = str(res.url)
                        page_data = extract_structured_page_data(
                            url=current_url,
                            final_url=final_url,
                            html=res.text,
                            status_code=res.status_code
                        )
                        page_type = classify_page_url(final_url)
                        page_data["page_type"] = page_type
                        page_data["http_status"] = res.status_code
                        page_data["word_count"] = len(page_data.get("main_text", "").split())
                        page_data["language"] = "en"

                        crawled_results.append(page_data)

                        if on_page_crawled:
                            try:
                                if asyncio.iscoroutinefunction(on_page_crawled):
                                    await on_page_crawled(page_data)
                                else:
                                    on_page_crawled(page_data)
                            except Exception as cb_err:
                                logger.warning(f"Error in on_page_crawled callback: {cb_err}")

                        # Enqueue internal links
                        for link in page_data.get("internal_links", []):
                            if link not in visited and link not in queue and len(queue) < 30:
                                queue.append(link)

                    await asyncio.sleep(settings.REQUEST_DELAY * 0.2)

                except Exception as e:
                    logger.debug(f"Failed to crawl {current_url}: {e}")

        return crawled_results

# Alias for backwards compatibility
CrawlerEngine = WebCrawler
