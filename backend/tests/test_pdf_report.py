import os
import pytest
from app.services.reports.report_builder import ReportModel
from app.services.reports.pdf_generator import pdf_generator
from app.core.config import settings

def test_pdf_generation_creates_valid_file(tmp_path):
    output_pdf = str(tmp_path / "test_report.pdf")

    model = ReportModel(
        run_data={"id": "run-12345", "source_type": "website", "source_input": "https://example.com"},
        company_data={
            "company_name": "Example Corp",
            "domain": "example.com",
            "website": "https://example.com",
            "industry": "Cloud Infrastructure",
            "description": "Enterprise cloud services.",
            "founded_year": "2020",
            "location": "San Francisco, CA"
        },
        competitors=[{
            "competitor_name": "TestCompetitor One",
            "website": "https://competitor-one.com",
            "competitor_type": "Direct",
            "confidence_level": "HIGH",
            "reason": "Offers identical cloud infrastructure and targets enterprise software teams.",
            "evidence_urls": ["https://techradar.com/review/example-vs-one"]
        }],
        seo_data={"observations": ["Sitemap verified", "Active blog presence"]},
        keywords=[{"keyword": "cloud infrastructure", "keyword_type": "Product", "frequency": 12}],
        products=[{"product_name": "Example Compute", "category": "Cloud"}],
        services=[{"service_name": "Managed Hosting", "category": "DevOps"}],
        social_profiles=[{"platform": "LinkedIn", "profile_url": "https://linkedin.com/company/example"}],
        pages=[{"url": "https://example.com", "page_type": "HOME"}]
    )

    result_path = pdf_generator.generate_pdf(model, output_pdf)
    assert os.path.exists(result_path)
    assert os.path.getsize(result_path) > 1000  # Valid non-empty PDF file
