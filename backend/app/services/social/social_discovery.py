from urllib.parse import urlparse
from typing import List, Dict, Any

SOCIAL_DOMAINS = {
    "twitter.com": "Twitter/X",
    "x.com": "Twitter/X",
    "linkedin.com": "LinkedIn",
    "github.com": "GitHub",
    "facebook.com": "Facebook",
    "instagram.com": "Instagram",
    "youtube.com": "YouTube"
}

class SocialDiscovery:
    def discover_profiles(self, pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen_urls = set()
        profiles = []

        for page in pages:
            for link in page.get("external_links", []):
                try:
                    parsed = urlparse(link)
                    domain = parsed.netloc.lower()
                    if domain.startswith("www."):
                        domain = domain[4:]
                    if domain in SOCIAL_DOMAINS and link not in seen_urls:
                        # Skip bare share links or root homepages
                        if len(parsed.path) > 2 and "share" not in parsed.path.lower():
                            seen_urls.add(link)
                            profiles.append({
                                "platform": SOCIAL_DOMAINS[domain],
                                "profile_url": link
                            })
                except Exception:
                    continue

        return profiles

social_discovery = SocialDiscovery()
