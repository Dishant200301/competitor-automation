import asyncio
import hmac
import uuid
from pathlib import Path
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Header
from fastapi.responses import FileResponse
from app.schemas.research import ResearchCreateRequest
from app.database.connection import db
from app.services.research.orchestrator import orchestrator
from app.reports.builder import generate_report
from app.crawler.url_discovery import normalize_url
from app.core.security import is_safe_url
from app.core.config import settings


def authorize(authorization: str = Header(default='')):
    if settings.API_TOKEN and not hmac.compare_digest(authorization, 'Bearer '+settings.API_TOKEN):
        raise HTTPException(401, 'API token required')


router = APIRouter(prefix='/api/research', tags=['Research'], dependencies=[Depends(authorize)])


def valid_id(run_id):
    try: return str(uuid.UUID(run_id))
    except ValueError: raise HTTPException(422, 'Invalid research run ID')


async def get_run(run_id):
    run_id = valid_id(run_id)
    run = await asyncio.to_thread(db.get_run, run_id)
    if not run: raise HTTPException(404, 'Research run not found')
    return run


@router.post('', status_code=201)
async def create_research_run(payload: ResearchCreateRequest, background_tasks: BackgroundTasks, sync: bool = False):
    try:
        url = normalize_url(payload.get_effective_input())
        safe, reason = is_safe_url(url)
        if not safe: raise ValueError(reason)
    except ValueError as exc: raise HTTPException(400, str(exc))
    run_id = str(uuid.uuid4())
    options = {k:getattr(payload,k) for k in ('company_name','product_url','service_url','social_url') if getattr(payload,k)}
    try: await asyncio.to_thread(db.create_run, run_id, 'website', url, options)
    except Exception: raise HTTPException(503, 'Database unavailable or migration not applied')

    if sync:
        await orchestrator.execute_run_async(run_id)
        run = await asyncio.to_thread(db.get_run, run_id)
        if not run or run.get('status') == 'failed':
            error_msg = (run or {}).get('error_message') or 'Research execution failed'
            raise HTTPException(500, error_msg)
        summary_data = await asyncio.to_thread(db.get_run_summary, run_id)
        validation_data = await asyncio.to_thread(db.get_validation_report, run_id)
        return {'run': run, **summary_data, 'validation_report': validation_data}

    if settings.JOB_MODE == "inline":
        background_tasks.add_task(orchestrator.execute_run_async, run_id)
    return {'research_run_id':run_id,'run_id':run_id,'status':'queued','message':'Research queued'}


@router.post('/execute')
async def execute_research_run(payload: ResearchCreateRequest):
    return await create_research_run(payload, BackgroundTasks(), sync=True)


@router.get('/{run_id}/status')
async def get_run_status(run_id: str): return await get_run(run_id)


@router.get('/{run_id}/summary')
async def get_summary(run_id: str):
    run = await get_run(run_id)
    return {'run':run, **await asyncio.to_thread(db.get_run_summary,run['id']), 'validation_report':await asyncio.to_thread(db.get_validation_report,run['id'])}


@router.get('/{run_id}/validation')
async def get_validation(run_id: str):
    run = await get_run(run_id)
    data = await asyncio.to_thread(db.get_validation_report, run['id'])
    if data is None: raise HTTPException(404,'Validation not available yet')
    return data


@router.get('/{run_id}/report/pdf')
async def download_pdf(run_id: str):
    run = await get_run(run_id)
    path = Path(settings.STORAGE_DIR)/f"Competitor_Report_{run['id']}.pdf"
    if run['status'] != 'completed' or not path.is_file(): raise HTTPException(409, 'Validated PDF is not available')
    return FileResponse(path, filename=path.name, media_type='application/pdf')


@router.get('/{run_id}/report/html')
async def view_html_report(run_id: str):
    run = await get_run(run_id)
    path = Path(settings.STORAGE_DIR)/f"Competitor_Report_{run['id']}.html"
    if run['status'] != 'completed' or not path.is_file(): raise HTTPException(409, 'Validated HTML report is not available')
    return FileResponse(path, filename=path.name, media_type='text/html')


@router.get('/{run_id}/report/docx')
async def download_docx(run_id: str):
    run = await get_run(run_id)
    path = Path(settings.STORAGE_DIR)/f"Competitor_Report_{run['id']}.docx"
    if run['status'] != 'completed': raise HTTPException(409, 'Report is not available yet')
    if not path.is_file():
        from app.reports.docx_builder import generate_docx_report
        try:
            await asyncio.to_thread(generate_docx_report, db, run['id'], path)
        except Exception as exc:
            raise HTTPException(500, f'Failed to generate docx report: {exc}')
    return FileResponse(
        path,
        filename=path.name,
        media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )


@router.post('/{run_id}/generate-pdf')
async def regenerate(run_id: str):
    run = await get_run(run_id)
    try: await asyncio.to_thread(generate_report, db, run['id'], Path(settings.STORAGE_DIR)/f"Competitor_Report_{run['id']}.pdf")
    except ValueError as exc: raise HTTPException(409,str(exc))
    return {'download_url':f"/api/research/{run['id']}/report/pdf"}


@router.get('/{run_id}/dataset/{filename}')
async def download_dataset(run_id: str, filename: str):
    run = await get_run(run_id)
    allowed = {'research.json','products.csv','categories.csv','services.csv','keywords.csv','competitors.csv','qualification_matrix.csv','sources.csv','evidence.csv','social_profiles.csv'}
    if filename not in allowed: raise HTTPException(404,'Unknown export')
    path = Path(settings.STORAGE_DIR)/'datasets'/run['id']/filename
    if not path.is_file(): raise HTTPException(404,'Export not available')
    return FileResponse(path, filename=filename)
