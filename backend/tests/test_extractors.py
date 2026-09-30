import pytest
from app.services.extractors.page_classifier import classify_page_url
from app.services.extractors.page_extractor import extract_structured_page_data
from app.services.extractors.company_extractor import CompanyExtractor
from app.services.extractors.product_extractor import ProductExtractor
from app.services.extractors.service_extractor import ServiceExtractor

def test_page_classification():
    assert classify_page_url("https://example.com/pricing") == "PRICING"
    assert classify_page_url("https://example.com/about-us") == "ABOUT"
    assert classify_page_url("https://example.com/products/analytics") == "PRODUCT"
    assert classify_page_url("https://example.com/services/consulting") == "SERVICE"
    assert classify_page_url("https://example.com/case-studies/client-a") == "CASE_STUDY"
    assert classify_page_url("https://example.com/blog/2026/how-to-grow") == "BLOG"
    assert classify_page_url("https://example.com/") == "HOME"

def test_structured_page_extraction():
    sample_html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>Acme Cloud - Enterprise Analytics</title>
        <meta name="description" content="Acme Cloud provides high-performance data analytics." />
        <link rel="canonical" href="https://acme.com/analytics" />
        <script type="application/ld+json">
        {
            "@type": "Product",
            "name": "Acme Data Engine",
            "description": "Real-time stream processor"
        }
        </script>
    </head>
    <body>
        <h1>Real-time Analytics Engine</h1>
        <h2>Stream Processing</h2>
        <p>Analyze petabytes of events with sub-second query latency.</p>
        <a href="/pricing">View Plans</a>
        <a href="https://linkedin.com/company/acme-cloud">LinkedIn</a>
    </body>
    </html>
    """
    data = extract_structured_page_data(
        url="https://acme.com/analytics",
        final_url="https://acme.com/analytics",
        html=sample_html,
        status_code=200
    )

    assert data["title"] == "Acme Cloud - Enterprise Analytics"
    assert "high-performance" in data["meta_description"]
    assert "Real-time Analytics Engine" in data["h1"]
    assert len(data["structured_data"]) == 1
    assert data["structured_data"][0]["name"] == "Acme Data Engine"
    assert "https://acme.com/pricing" in data["internal_links"]
    assert "https://linkedin.com/company/acme-cloud" in data["external_links"]

def test_company_and_product_extraction():
    pages = [{
        "url": "https://acme.com",
        "final_url": "https://acme.com",
        "page_type": "HOME",
        "title": "Acme Cloud - Home",
        "meta_description": "Global leader in real-time enterprise data processing.",
        "h1": ["Acme Cloud Platform"],
        "main_text": "Founded in 2021, Acme Cloud builds modern database infrastructure.",
        "structured_data": [{
            "@type": "Organization",
            "name": "Acme Cloud Technologies",
            "foundingDate": "2021"
        }]
    }, {
        "url": "https://acme.com/products/engine",
        "final_url": "https://acme.com/products/engine",
        "page_type": "PRODUCT",
        "h1": ["Acme Data Engine"],
        "h2": ["Sub-second latency", "Zero downtime"],
        "meta_description": "High performance SQL query engine.",
        "structured_data": [{
            "@type": "Product",
            "name": "Acme Data Engine",
            "description": "High performance SQL query engine."
        }]
    }]

    co_extractor = CompanyExtractor()
    company = co_extractor.extract_from_pages(pages, "https://acme.com")
    assert company["company_name"] == "Acme Cloud Technologies"
    assert company["founded_year"] == "2021"

    prod_extractor = ProductExtractor()
    products = prod_extractor.extract_from_pages(pages)
    assert len(products) >= 1
    assert products[0]["product_name"] == "Acme Data Engine"
