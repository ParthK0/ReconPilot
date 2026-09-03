"""
tests/test_job_queue.py
=======================
Tests for Asynchronous Reconciliation Job Queue.
"""

import time
import pytest
from backend.services.job_queue import JobQueueManager, JobProgress


def test_job_queue_manager_submission():
    manager = JobQueueManager(max_workers=2)
    test_org_id = f"tenant_finops_{int(time.time() * 1000)}"
    job_id = manager.submit_job(
        batch_id="test-async-batch-001",
        org_id=test_org_id,
        merchant_type="retail",
    )

    assert job_id is not None
    job = manager.get_job(job_id)
    assert job is not None
    assert job.batch_id == "test-async-batch-001"
    assert job.org_id == test_org_id
    assert job.status in ("queued", "processing", "completed", "failed")

    jobs_list = manager.list_jobs(org_id=test_org_id)
    assert len(jobs_list) == 1
    assert jobs_list[0].job_id == job_id
