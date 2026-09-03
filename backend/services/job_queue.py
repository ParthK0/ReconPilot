"""
backend/services/job_queue.py
=============================
Asynchronous Background Job Queue & Task Manager.
Enables non-blocking background reconciliation execution for high-volume batches (100k+ rows)
with real-time progress tracking, stage notifications, and tenant isolation.
"""

import os
import uuid
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from backend.db.session import SessionLocal
from backend.db.models import ReconciliationJob
from backend.services.pipeline import process_reconciliation_batch
from backend.logging_config import get_logger

logger = get_logger("job_queue")


class JobProgress(BaseModel):
    job_id: str
    org_id: str = "org_default"
    batch_id: str
    status: str = "queued"  # queued, processing, completed, failed
    stage: str = "initializing"  # initializing, rule_matching, ai_micro_batching, gap_detection, snapshot, done
    progress: float = 0.0  # 0.0 to 100.0%
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class JobQueueManager:
    """Thread-safe asynchronous reconciliation job executor."""

    def __init__(self, max_workers: int = 4):
        self._jobs: Dict[str, JobProgress] = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="recon-worker")

    def submit_job(
        self,
        batch_id: str,
        org_id: str = "org_default",
        fee_config: Optional[Any] = None,
        ground_truth: Optional[Any] = None,
        merchant_type: str = "retail",
    ) -> str:
        job_id = str(uuid.uuid4())
        job = JobProgress(
            job_id=job_id,
            org_id=org_id,
            batch_id=batch_id,
            status="queued",
            stage="queued",
            progress=0.0,
        )
        with self._lock:
            self._jobs[job_id] = job

        # Persist initial job record to database
        db = SessionLocal()
        try:
            db_job = ReconciliationJob(
                id=job_id,
                org_id=org_id,
                batch_id=batch_id,
                status="queued",
                stage="queued",
                progress=Decimal("0.00"),
            )
            db.add(db_job)
            db.commit()
            logger.info("Queued reconciliation job '%s' for batch '%s' (org: %s).", job_id, batch_id, org_id)
        except Exception as e:
            logger.warning("Failed to persist initial job to DB: %s", e)
        finally:
            db.close()

        self._executor.submit(
            self._run_job,
            job_id=job_id,
            batch_id=batch_id,
            fee_config=fee_config,
            ground_truth=ground_truth,
            merchant_type=merchant_type,
        )
        return job_id

    def _update_job(self, job_id: str, **kwargs):
        with self._lock:
            if job_id in self._jobs:
                job = self._jobs[job_id]
                for k, v in kwargs.items():
                    setattr(job, k, v)
                job.updated_at = datetime.now(timezone.utc)

        # Sync update to database
        db = SessionLocal()
        try:
            db_job = db.query(ReconciliationJob).filter(ReconciliationJob.id == job_id).first()
            if db_job:
                if "status" in kwargs:
                    db_job.status = kwargs["status"]
                if "stage" in kwargs:
                    db_job.stage = kwargs["stage"]
                if "progress" in kwargs:
                    db_job.progress = Decimal(str(kwargs["progress"]))
                if "completed_at" in kwargs:
                    db_job.completed_at = kwargs["completed_at"]
                if "result" in kwargs:
                    db_job.result_payload = kwargs["result"]
                if "error" in kwargs:
                    db_job.error_message = kwargs["error"]
                db_job.updated_at = datetime.now(timezone.utc)
                db.commit()
        except Exception as e:
            logger.warning("Failed to sync job '%s' update to DB: %s", job_id, e)
        finally:
            db.close()

    def _run_job(
        self,
        job_id: str,
        batch_id: str,
        fee_config: Optional[Any] = None,
        ground_truth: Optional[Any] = None,
        merchant_type: str = "retail",
    ):
        self._update_job(job_id, status="processing", stage="rule_matching", progress=15.0)
        db = SessionLocal()
        try:
            self._update_job(job_id, stage="ai_micro_batching", progress=40.0)
            
            snapshot = process_reconciliation_batch(
                db=db,
                batch_id=batch_id,
                fee_config=fee_config,
                ground_truth=ground_truth,
                merchant_type=merchant_type,
            )

            self._update_job(job_id, stage="gap_detection", progress=85.0)

            result_summary = {
                "batch_id": batch_id,
                "records_processed": snapshot.records_processed,
                "rule_matches": snapshot.rule_matches,
                "ai_verified": snapshot.ai_verified,
                "needs_review": snapshot.needs_review,
                "match_rate": float(snapshot.match_rate) if snapshot.match_rate else 0.0,
                "processing_time_seconds": float(snapshot.processing_time_seconds) if snapshot.processing_time_seconds else 0.0,
            }

            self._update_job(
                job_id,
                status="completed",
                stage="done",
                progress=100.0,
                completed_at=datetime.now(timezone.utc),
                result=result_summary,
            )
            logger.info("Reconciliation job '%s' completed successfully.", job_id)
        except Exception as exc:
            self._update_job(
                job_id,
                status="failed",
                stage="failed",
                error=str(exc),
                completed_at=datetime.now(timezone.utc),
            )
            logger.error("Reconciliation job '%s' failed: %s", job_id, exc)
        finally:
            db.close()

    def get_job(self, job_id: str) -> Optional[JobProgress]:
        with self._lock:
            if job_id in self._jobs:
                return self._jobs[job_id]

        db = SessionLocal()
        try:
            db_job = db.query(ReconciliationJob).filter(ReconciliationJob.id == job_id).first()
            if db_job:
                progress = JobProgress(
                    job_id=db_job.id,
                    org_id=db_job.org_id,
                    batch_id=db_job.batch_id,
                    status=db_job.status,
                    stage=db_job.stage,
                    progress=float(db_job.progress),
                    created_at=db_job.created_at,
                    updated_at=db_job.updated_at,
                    completed_at=db_job.completed_at,
                    result=db_job.result_payload,
                    error=db_job.error_message,
                )
                with self._lock:
                    self._jobs[job_id] = progress
                return progress
        except Exception:
            pass
        finally:
            db.close()
        return None

    def list_jobs(self, org_id: Optional[str] = None) -> List[JobProgress]:
        db = SessionLocal()
        try:
            query = db.query(ReconciliationJob)
            if org_id:
                query = query.filter(ReconciliationJob.org_id == org_id)
            db_jobs = query.order_by(ReconciliationJob.created_at.desc()).all()
            if db_jobs:
                return [
                    JobProgress(
                        job_id=j.id,
                        org_id=j.org_id,
                        batch_id=j.batch_id,
                        status=j.status,
                        stage=j.stage,
                        progress=float(j.progress),
                        created_at=j.created_at,
                        updated_at=j.updated_at,
                        completed_at=j.completed_at,
                        result=j.result_payload,
                        error=j.error_message,
                    )
                    for j in db_jobs
                ]
        except Exception:
            pass
        finally:
            db.close()

        with self._lock:
            jobs = list(self._jobs.values())
            if org_id:
                jobs = [j for j in jobs if j.org_id == org_id]
            return sorted(jobs, key=lambda x: x.created_at, reverse=True)


# Global singleton instance
job_queue = JobQueueManager()
