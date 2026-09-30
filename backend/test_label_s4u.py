import asyncio
import os
import sys
from app.database.connection import db
from app.services.research.orchestrator import orchestrator

import uuid

async def run_test():
    run_id = f"label-s4u-{uuid.uuid4().hex[:8]}"
    db.create_run(run_id, "website", "https://label-s4u.com/")
    print("Starting orchestrator execution for https://label-s4u.com/ ...")
    await orchestrator.execute_run_async(run_id)
    print("Execution finished!\n")
    
    run = db.get_run(run_id)
    summary = db.get_run_summary(run_id)
    val = db.get_validation_report(run_id)
    company = db.get_company(run_id)
    categories = db.get_categories(run_id)
    products = db.get_products(run_id)
    competitors = db.get_competitors(run_id)
    keywords = db.get_keywords(run_id)
    
    print("=== RUN STATUS ===", run.get("status"))
    print("=== ERROR (IF ANY) ===", run.get("error_message"))
    print("=== COMPANY NAME ===", company.get("company_name"))
    print("=== INDUSTRY ===", company.get("industry"))
    print("=== SUB-INDUSTRY ===", company.get("sub_industry"))
    print("=== BUSINESS MODEL ===", company.get("business_model"))
    print("=== TARGET AUDIENCE ===", company.get("target_audience"))
    print("=== GEOGRAPHIC REACH ===", company.get("geographic_market"))
    print("=== PRICE POSITIONING ===", company.get("price_range_summary"))
    print(f"=== CATEGORIES COUNT ({len(categories)}) ===", [c["category_name"] for c in categories[:8]])
    print(f"=== PRODUCTS COUNT ({len(products)}) ===", [p["product_name"] for p in products[:5]])
    print(f"=== KEYWORDS COUNT ({len(keywords)}) ===", [f"{k['keyword']} ({k['intent']})" for k in keywords[:6]])
    print(f"=== COMPETITORS COUNT ({len(competitors)}) ===")
    for c in competitors:
        print(f"  - [{c.get('competitor_type')}] {c.get('competitor_name')} ({c.get('website')})")
    print("\n=== VALIDATION AUDIT ===")
    print("STATUS:", val.get("status"))
    print("PASSED CHECKS:")
    for p in val.get("passed_checks", []):
        print(f"  - {p}")
    print("FAILED CHECKS:", val.get("failed_checks"))
    print("WARNINGS:", val.get("warnings"))
    print("PDF URL:", run.get("pdf_url"))

    # Verify dataset exports
    dataset_dir = os.path.join("data", "reports", "datasets", run_id)
    if os.path.exists(dataset_dir):
        print(f"\n=== EXPORTED DATASETS IN {dataset_dir} ===")
        for f in os.listdir(dataset_dir):
            size = os.path.getsize(os.path.join(dataset_dir, f))
            print(f"  - {f} ({size} bytes)")

if __name__ == "__main__":
    asyncio.run(run_test())
