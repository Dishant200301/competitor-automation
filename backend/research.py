"""Run research from the CLI; optional inputs are context, never verified facts."""
import argparse
import asyncio
import json
import uuid
from app.database.connection import DatabaseClient
from app.services.research.orchestrator import ResearchOrchestrator
from app.crawler.url_discovery import normalize_url

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('url')
    parser.add_argument('--database', choices=['supabase','sqlite'], default='supabase')
    parser.add_argument('--company-name')
    parser.add_argument('--product-url')
    parser.add_argument('--social-url')
    args = parser.parse_args()
    database = DatabaseClient(backend=args.database)
    run_id = str(uuid.uuid4())
    database.create_run(run_id, 'website', normalize_url(args.url), {k:v for k,v in vars(args).items() if k.endswith('_url') or k == 'company_name'})
    print('Run:', run_id, flush=True)
    await ResearchOrchestrator(database).execute_run_async(run_id)
    run = database.get_run(run_id)
    print(json.dumps(run, indent=2))
    if run['status'] != 'completed': raise SystemExit(1)

if __name__ == '__main__': asyncio.run(main())
