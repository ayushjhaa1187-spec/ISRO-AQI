"""
api/v1/export.py
----------------
Async export job endpoints.

Routes:
    POST /export                → Submit a new export job, returns ExportJob (status=pending)
    GET  /export/{job_id}       → Poll job status; returns download_url when complete

In DEV_MODE, jobs are stored in-process (dict). In production, use a Redis-backed
Celery/ARQ task queue and persist job state in the database.
"""

from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Dict, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse

from core.config import settings
from models.schemas import ExportFormat, ExportJob, ExportRequest, ExportStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/export", tags=["Export"])


# ---------------------------------------------------------------------------
# In-process job store (DEV_MODE only)
# ---------------------------------------------------------------------------

_JOB_STORE: Dict[str, ExportJob] = {}


# ---------------------------------------------------------------------------
# Background task simulation (DEV_MODE)
# ---------------------------------------------------------------------------

async def _simulate_export(job_id: str) -> None:
    """
    Simulate an export job progressing through states.

    In DEV_MODE we immediately mark the job as completed with a dummy URL.
    In a real deployment this would enqueue a Celery / ARQ task.
    """
    import asyncio

    job = _JOB_STORE.get(job_id)
    if job is None:
        return

    # Simulate brief processing delay
    await asyncio.sleep(2)

    now = datetime.now(tz=timezone.utc)

    # Build a plausible download URL
    filename = (
        f"{job.layer}_{job.start.isoformat()}_to_{job.end.isoformat()}.{job.format.value}"
    )
    download_url = f"/static/exports/{job_id}/{filename}"

    _JOB_STORE[job_id] = job.model_copy(
        update={
            "status": ExportStatus.COMPLETED,
            "completed_at": now,
            "download_url": download_url,
            "progress_pct": 100,
        }
    )
    logger.info("Export job %s completed → %s", job_id, download_url)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "",
    summary="Submit an export job",
    description=(
        "Submit an async export job for a raster layer over a date range. "
        "Supported formats: GeoTIFF, CSV (pixel values), PDF (map report). "
        "Returns a job ID that can be polled via GET /export/{job_id}."
    ),
    response_model=ExportJob,
    status_code=202,
    responses={
        422: {"description": "Validation error (invalid dates, format, or layer)"},
    },
)
async def create_export_job(
    request: ExportRequest,
    background_tasks: BackgroundTasks,
) -> ExportJob:
    """
    Create and enqueue an export job.

    Validates the request, assigns a UUID job ID, records the job in the
    store (or task queue in production), and immediately returns with
    status=pending.
    """
    if request.start > request.end:
        raise HTTPException(
            status_code=422,
            detail=f"start ({request.start}) must be ≤ end ({request.end}).",
        )

    max_range_days = 366
    if (request.end - request.start).days > max_range_days:
        raise HTTPException(
            status_code=422,
            detail=f"Date range exceeds maximum allowed {max_range_days} days.",
        )

    valid_layers = {"aqi", "hcho", "fire", "pm25", "pm10"}
    if request.layer not in valid_layers:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown layer '{request.layer}'. Valid: {sorted(valid_layers)}",
        )

    job_id = str(uuid.uuid4())
    now = datetime.now(tz=timezone.utc)

    job = ExportJob(
        job_id=job_id,
        status=ExportStatus.PENDING,
        layer=request.layer,
        start=request.start,
        end=request.end,
        format=request.format,
        created_at=now,
        completed_at=None,
        download_url=None,
        error_message=None,
        progress_pct=0,
    )

    if settings.DEV_MODE:
        _JOB_STORE[job_id] = job
        # Run the simulation as a background task
        background_tasks.add_task(_simulate_export, job_id)
    else:
        # Production: enqueue via Redis/Celery
        # from workers.tasks import export_task
        # export_task.delay(job_id, request.model_dump())
        # For now, raise until worker is wired up.
        raise HTTPException(
            status_code=503,
            detail="Export worker not connected. Set DEV_MODE=true for local testing.",
        )

    logger.info(
        "Export job %s created: layer=%s, %s→%s, format=%s",
        job_id,
        request.layer,
        request.start,
        request.end,
        request.format,
    )
    return job


@router.get(
    "/{job_id}",
    summary="Poll export job status",
    description=(
        "Retrieve the current status and (when complete) the download URL of an "
        "export job. Poll this endpoint until status is 'completed' or 'failed'."
    ),
    response_model=ExportJob,
    responses={
        404: {"description": "Job not found"},
    },
)
async def get_export_job(job_id: str) -> ExportJob:
    """
    Return the current state of an export job by ID.

    In DEV_MODE, after ~2 seconds the job transitions to 'completed' with a
    download URL. Returns 404 if the job ID is unknown.
    """
    job = _JOB_STORE.get(job_id)
    if job is None:
        raise HTTPException(
            status_code=404,
            detail=f"Export job '{job_id}' not found. It may have expired or never existed.",
        )
    return job


@router.get(
    "",
    summary="List recent export jobs",
    description="Returns all in-memory export jobs (DEV_MODE only). Useful for debugging.",
    response_model=None,
)
async def list_export_jobs(limit: int = 20) -> dict:
    """Return a list of the most recent export jobs (DEV_MODE only)."""
    if not settings.DEV_MODE:
        raise HTTPException(
            status_code=403,
            detail="Job listing is only available in DEV_MODE.",
        )

    jobs = sorted(_JOB_STORE.values(), key=lambda j: j.created_at, reverse=True)[:limit]
    return {
        "total": len(_JOB_STORE),
        "jobs": [j.model_dump(mode="json") for j in jobs],
    }
