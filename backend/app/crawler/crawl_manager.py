import hashlib
from pathlib import Path
from app.core.config import settings
from app.extraction.pages import extract_page, now
from .transport import SafeTransport
from .robots import RobotsPolicy
from .sitemap import discover_sitemaps
from .url_discovery import normalize_url, same_site, priority, crawlable
from .playwright_crawler import render_page


class WebCrawler:
    def __init__(self, run_id="", max_pages=None, raw_dir=None):
        self.run_id = run_id
        self.max_pages = max_pages or settings.MAX_PAGES
        self.transport = SafeTransport()
        self.robots = RobotsPolicy(self.transport)
        self.sitemap_urls, self.sitemap_records, self.errors, self.raw_records = [], [], [], []
        self.pages = []
        self.raw_dir = Path(raw_dir or Path(settings.STORAGE_DIR) / "raw" / (run_id or "adhoc"))

    def preserve(self, html, url, kind):
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256(html.encode()).hexdigest()
        path = self.raw_dir / f"{digest}.html"
        if not path.exists(): path.write_text(html, encoding="utf-8")
        record = {"url": url, "sha256": digest, "path": str(path), "stage": kind, "date_checked": now(), "raw_html": html}
        self.raw_records.append(record)
        return record

    async def crawl_site(self, start_url, on_page_crawled=None, seed_urls=None):
        start_url = normalize_url(start_url)
        self.sitemap_urls, self.sitemap_records = await discover_sitemaps(start_url, self.transport, self.robots)
        seeds = sorted(set(self.sitemap_urls + (seed_urls or [])), key=priority)
        # Keep collection and descriptive pages in the sample instead of filling it with products.
        products = [x for x in seeds if priority(x) == 0]
        others = [x for x in seeds if priority(x) != 0]
        seeds = products[:max(2, self.max_pages // 2)] + others[:self.max_pages]
        queue = [(start_url, 0)] + [(u, 1) for u in seeds]
        seen, canonical_seen, pages = set(), set(), self.pages
        attempts = 0
        while queue and len(pages) < self.max_pages and attempts < self.max_pages * 4:
            url, depth = queue.pop(0)
            try: url = normalize_url(url)
            except ValueError: continue
            if url in seen or not same_site(url, start_url) or not crawlable(url) or depth > settings.MAX_DEPTH: continue
            seen.add(url)
            attempts += 1
            try:
                if not await self.robots.can_fetch(url):
                    self.errors.append({"url": url, "error": "robots.txt disallowed"}); continue
                r = await self.transport.get(url, boundary=start_url, redirect_check=self.robots.can_fetch)
                if r.status_code != 200 or "html" not in r.headers.get("content-type", ""):
                    self.errors.append({"url": url, "error": f"HTTP {r.status_code} or non-HTML"}); continue
                final = str(r.url)
                raw = self.preserve(r.text, final, "raw")
                page = extract_page(r.text, final)
                if settings.ENABLE_JAVASCRIPT and page["word_count"] < 60:
                    try:
                        rendered = await render_page(final, self.transport, self.robots)
                        rendered_raw = self.preserve(rendered, final, "rendered")
                        page = extract_page(rendered, final)
                        page["rendered_hash"] = rendered_raw["sha256"]
                    except Exception as exc:
                        self.errors.append({"url": final, "error": "Rendering failed: " + type(exc).__name__})
                page["raw_hash"] = raw["sha256"]
                if (page["word_count"] < 10 and not page["structured_data"]) or any(
                    marker in page["title"].lower() for marker in ("just a moment", "access denied", "robot or human", "captcha")):
                    self.errors.append({"url": final, "error": "Empty page or access challenge; unavailable evidence"})
                    continue
                page["indexable"] = page["indexable"] and "noindex" not in r.headers.get("x-robots-tag", "").lower()
                canonical = page.get("canonical_url")
                if canonical and same_site(canonical, start_url):
                    canonical = normalize_url(canonical)
                    if canonical in canonical_seen: continue
                    canonical_seen.add(canonical)
                if page["indexable"]:
                    pages.append(page)
                    if on_page_crawled: await on_page_crawled(page)
                discovered = sorted(page["internal_links"], key=priority)
                for link in discovered:
                    if len(queue) >= self.max_pages * 10: break
                    if link not in seen and all(x[0] != link for x in queue): queue.append((link, depth + 1))
            except Exception as exc:
                self.errors.append({"url": url, "error": type(exc).__name__ + ": " + str(exc)[:180]})
        return pages
