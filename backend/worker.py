"""Database-backed job consumer. Multiple workers claim jobs atomically."""
import asyncio
from app.database.connection import db
from app.services.research.orchestrator import orchestrator
from app.utils.logger import logger


async def main():
    logger.info("Worker started (backend: %s). Waiting for queued research jobs...", db.backend)
    while True:
        try:
            run_id = await asyncio.to_thread(db.claim_next_run)
            if not run_id:
                await asyncio.sleep(3)
                continue
            logger.info("Claimed research run: %s", run_id)
            try:
                await asyncio.wait_for(orchestrator.execute_run_async(run_id), timeout=3600)
                logger.info("Finished research run: %s", run_id)
            except (TimeoutError, asyncio.CancelledError):
                await asyncio.to_thread(
                    db.update_run,
                    run_id,
                    status="failed",
                    current_step="Worker interrupted or time budget exhausted",
                    error_message="Create a new run to retry; existing evidence is preserved",
                )
                raise
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.warning("Error claiming or checking for jobs: %s. Retrying in 5s...", exc)
            await asyncio.sleep(5)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker stopped by user (KeyboardInterrupt).")

