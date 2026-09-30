"""Render with all network requests mediated by the same checked HTTP transport."""
from .url_discovery import same_site


async def render_page(url, transport, robots):
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            context = await browser.new_context(service_workers="block")
            request_count = 0
            async def route(request_route):
                nonlocal request_count
                request_count += 1
                req = request_route.request
                if request_count > 80 or req.method != "GET" or req.resource_type in {"image", "font", "media", "websocket"}:
                    return await request_route.abort()
                if not same_site(req.url, url): return await request_route.abort()
                try:
                    if not await robots.can_fetch(req.url): return await request_route.abort()
                    r = await transport.get(req.url, boundary=url, redirect_check=robots.can_fetch)
                    headers = {k:v for k,v in r.headers.items() if k.lower() not in {"content-encoding", "content-length", "transfer-encoding"}}
                    await request_route.fulfill(status=r.status_code, headers=headers, body=r.content)
                except Exception:
                    try: await request_route.abort()
                    except Exception: pass  # Browser may have closed while the request was in flight.
            await context.route("**/*", route)
            page = await context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_timeout(1500)
            return await page.content()
        finally:
            if 'context' in locals():
                await context.unroute_all(behavior="ignoreErrors")
            await browser.close()
