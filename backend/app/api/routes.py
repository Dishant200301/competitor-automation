import os
import uuid
from fastapi import APIRouter, HTTPException, BackgroundTasks, status
from fastapi.responses import FileResponse, JSONResponse

from app.schemas.research import (
    ResearchCreateRequest,
    ResearchCreateResponse,
    ResearchRunResponse,
    ResearchSummaryResponse,
)
from app.database.connection import db
from app.services.research.orchestrator import orchestrator
from app.services.reports.report_builder import ReportModel
from app.services.reports.pdf_generator import pdf_generator
from app.services.reports.google_docs_generator import google_docs_generator
from app.core.config import settings

router = APIRouter(prefix="/api/research", tags=["Research"])

@router.post("", response_model=ResearchCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_research_run(payload: ResearchCreateRequest, background_tasks: BackgroundTasks):
    eff_input = payload.get_effective_input()
    if not eff_input:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A website URL, social link, company, or product input is required."
        )

    eff_type = payload.get_effective_type()
    run_id = str(uuid.uuid4())
    db.create_run(
        run_id=run_id,
        source_type=eff_type,
        source_input=eff_input
    )

    background_tasks.add_task(orchestrator.execute_run_async, run_id)

    return ResearchCreateResponse(
        research_run_id=run_id,
        run_id=run_id,
        status="queued",
        message="Research run initiated successfully."
    )

@router.get("/{run_id}/status", response_model=ResearchRunResponse)
async def get_run_status(run_id: str):
    run = db.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Research run not found.")

    return ResearchRunResponse(
        id=run["id"],
        source_type=run["source_type"],
        source_input=run["source_input"],
        status=run["status"],
        current_step=run.get("current_step"),
        progress_percentage=run.get("progress_percentage", 0),
        error_message=run.get("error_message"),
        google_doc_url=run.get("google_doc_url"),
        pdf_url=run.get("pdf_url"),
        created_at=run["created_at"],
        updated_at=run["updated_at"],
    )

@router.get("/{run_id}/summary", response_model=ResearchSummaryResponse)
async def get_run_summary(run_id: str):
    run = db.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Research run not found.")

    summary = db.get_run_summary(run_id)
    val_rep = db.get_validation_report(run_id)

    return ResearchSummaryResponse(
        run=ResearchRunResponse(
            id=run["id"],
            source_type=run["source_type"],
            source_input=run["source_input"],
            status=run["status"],
            current_step=run.get("current_step"),
            progress_percentage=run.get("progress_percentage", 0),
            error_message=run.get("error_message"),
            google_doc_url=run.get("google_doc_url"),
            pdf_url=run.get("pdf_url"),
            created_at=run["created_at"],
            updated_at=run["updated_at"],
        ),
        company=summary.get("company"),
        competitors=summary.get("competitors", []),
        pages_count=summary.get("pages_count", 0),
        products_count=summary.get("products_count", 0),
        categories_count=summary.get("categories_count", 0),
        services_count=summary.get("services_count", 0),
        keywords_count=summary.get("keywords_count", 0),
        validation_report=val_rep
    )

@router.get("/{run_id}/validation")
async def get_validation_report(run_id: str):
    val_rep = db.get_validation_report(run_id)
    if not val_rep:
        raise HTTPException(status_code=404, detail="Validation report not found for this run.")
    return val_rep

@router.post("/{run_id}/generate-pdf")
async def generate_pdf_report(run_id: str):
    run = db.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Research run not found.")

    report_model = ReportModel.from_database(db, run_id)
    pdf_filename = f"Competitor_Report_{run_id[:8]}.pdf"
    pdf_filepath = os.path.join(settings.STORAGE_DIR, pdf_filename)

    pdf_generator.generate_pdf(report_model, pdf_filepath)
    file_size = os.path.getsize(pdf_filepath)

    db.save_report({
        "run_id": run_id,
        "report_type": "pdf",
        "title": f"Competitor Intelligence Report - {run_id[:8]}",
        "local_path": pdf_filepath,
        "external_url": f"/api/research/{run_id}/report/pdf",
        "file_size_bytes": file_size
    })
    db.update_run(run_id, pdf_url=f"/api/research/{run_id}/report/pdf")

    return {"download_url": f"/api/research/{run_id}/report/pdf"}

@router.get("/{run_id}/report/pdf")
async def download_pdf_report(run_id: str):
    pdf_filename = f"Competitor_Report_{run_id[:8]}.pdf"
    pdf_filepath = os.path.join(settings.STORAGE_DIR, pdf_filename)

    if not os.path.exists(pdf_filepath):
        report_model = ReportModel.from_database(db, run_id)
        pdf_generator.generate_pdf(report_model, pdf_filepath)

    if not os.path.exists(pdf_filepath):
        raise HTTPException(status_code=404, detail="PDF report could not be generated.")

    return FileResponse(
        path=pdf_filepath,
        filename=pdf_filename,
        media_type="application/pdf"
    )

@router.post("/{run_id}/generate-google-doc")
async def generate_google_doc_report(run_id: str):
    run = db.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Research run not found.")

    report_model = ReportModel.from_database(db, run_id)
    res = await google_docs_generator.generate_doc(report_model)
    if not res:
        raise HTTPException(
            status_code=503,
            detail="Google Docs API credentials not configured in backend .env. PDF export is available."
        )

    doc_url = res.get("google_document_url")
    db.update_run(run_id, google_doc_url=doc_url)
    return {"url": doc_url}
