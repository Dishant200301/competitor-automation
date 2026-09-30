import pytest
from app.services.crawler.url_normalizer import normalize_url, extract_domain, is_same_domain
from app.core.security import is_safe_url

def test_url_normalization_cleans_tracking_and_fragments():
    url = "https://example.com/products/tool?utm_source=twitter&utm_medium=cpc&ref=affiliate#pricing"
    normalized = normalize_url(url)
    assert "utm_source" not in normalized
    assert "utm_medium" not in normalized
    assert "ref" not in normalized
    assert "#pricing" not in normalized
    assert normalized == "https://example.com/products/tool"

def test_url_normalization_trailing_slash():
    assert normalize_url("https://example.com/about/") == "https://example.com/about"
    assert normalize_url("https://example.com/") == "https://example.com/"

def test_extract_domain():
    assert extract_domain("https://www.stripe.com/docs") == "stripe.com"
    assert extract_domain("http://sub.example.co.uk:8080/path") == "sub.example.co.uk"

def test_is_same_domain():
    assert is_same_domain("https://example.com/about", "https://example.com/pricing") is True
    assert is_same_domain("https://www.example.com", "https://example.com") is True
    assert is_same_domain("https://competitor.com", "https://example.com") is False

def test_ssrf_protection_blocks_internal_hosts():
    # Loopback
    safe, reason = is_safe_url("http://127.0.0.1:8000/secret")
    assert not safe
    assert "blocked" in reason or "private" in reason

    # Localhost
    safe, reason = is_safe_url("http://localhost:3000")
    assert not safe

    # Cloud metadata endpoint
    safe, reason = is_safe_url("http://169.254.169.254/latest/meta-data")
    assert not safe

    # Valid public URL
    safe, reason = is_safe_url("https://stripe.com")
    assert safe
