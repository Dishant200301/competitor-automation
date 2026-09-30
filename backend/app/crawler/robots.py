from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser
from app.core.config import settings


class RobotsPolicy:
    def __init__(self, transport):
        self.transport = transport
        self.cache = {}
        self.records = []
        self.is_fetched = False

    async def load(self, url):
        p = urlsplit(url)
        origin = f"{p.scheme}://{p.netloc}"
        if origin in self.cache: return self.cache[origin]
        parser = RobotFileParser(origin + "/robots.txt")
        try:
            r = await self.transport.get(parser.url, boundary=url)
            self.is_fetched = True
            if r.status_code == 200:
                parser.parse(r.text.splitlines())
                state = "parsed"
            elif r.status_code in (404, 410):
                parser.parse([])
                state = "absent"
            else:
                parser.disallow_all = True
                state = "unavailable; deny crawl"
            self.records.append({"url": parser.url, "status": r.status_code, "policy": state, "raw_text": r.text})
        except Exception as exc:
            parser.disallow_all = True
            self.records.append({"url": parser.url, "policy": "unavailable; deny crawl", "error": type(exc).__name__})
        delay = parser.crawl_delay(settings.CRAWLER_USER_AGENT) or parser.crawl_delay("*")
        if delay: self.transport.delay = max(self.transport.delay, delay)
        self.cache[origin] = parser
        return parser

    async def can_fetch(self, url):
        return (await self.load(url)).can_fetch(settings.CRAWLER_USER_AGENT, url)
