import urllib.robotparser
from urllib.parse import urlparse
import httpx
from app.utils.logger import logger

class PoliteRobotsParser:
    def __init__(self, user_agent: str = "*"):
        self.user_agent = user_agent
        self.parsers = {}

    async def can_fetch(self, url: str) -> bool:
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        if base not in self.parsers:
            rp = urllib.robotparser.RobotFileParser()
            robots_url = f"{base}/robots.txt"
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(robots_url)
                    if resp.status_code == 200:
                        rp.parse(resp.text.splitlines())
                    else:
                        rp.allow_all = True
            except Exception:
                rp.allow_all = True
            self.parsers[base] = rp
        return self.parsers[base].can_fetch(self.user_agent, url)

robots_checker = PoliteRobotsParser()
