from urllib.parse import urlsplit, urlunsplit, urljoin, parse_qsl, urlencode
import re

TRACKING = {"gclid", "fbclid", "msclkid", "ref", "sort_by", "variant", "mc_cid", "mc_eid"}


def normalize_url(url: str, base: str = "") -> str:
    url = urljoin(base, url.strip()) if base else url.strip()
    if "://" not in url:
        url = "https://" + url
    p = urlsplit(url)
    if p.scheme not in {"http", "https"} or not p.hostname or p.username or p.password:
        raise ValueError("A public HTTP(S) website URL without credentials is required")
    if p.port not in (None, 80, 443):
        raise ValueError("Only standard HTTP(S) ports are supported")
    host = p.hostname.encode("idna").decode().lower()
    if not re.fullmatch(r"[a-z0-9.-]+|[0-9a-f:]+", host) or ("." not in host and ":" not in host):
        raise ValueError("A valid public website hostname is required")
    query = urlencode(sorted((k, v) for k, v in parse_qsl(p.query) if
                             not k.lower().startswith("utm_") and k.lower() not in TRACKING))
    return urlunsplit((p.scheme, host, p.path or "/", query, ""))


def domain(url):
    return (urlsplit(url).hostname or "").lower().removeprefix("www.")


def same_site(a, b):
    return domain(a) == domain(b)


def priority(url):
    path = urlsplit(url).path.lower()
    if any(x in path for x in ("/products/", "/product/")): return 0
    if any(x in path for x in ("/collections/", "/category/", "/services/")): return 1
    if any(x in path for x in ("about", "shipping", "contact", "pricing")): return 2
    return 3


def crawlable(url):
    p = urlsplit(url)
    return not p.query and not any(x in p.path.lower() for x in
        ("/cart", "/checkout", "/account", "/login", "/logout", "/search", "/admin")) and not p.path.lower().endswith(
        (".pdf", ".jpg", ".png", ".zip", ".mp4", ".css", ".js", ".xml"))
