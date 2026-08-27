"""
tests/test_scalability_10k.py
=============================
ReconPilot 2.0: Scalability Benchmark & High-Volume Generation Test.
Tests 1,000-record and 10,000-record scalable dataset generation and ground-truth validation.
"""

import time
import pytest
from backend.synthetic_data.generator import generate_merchant_dataset


def test_1000_record_generation_performance():
    start = time.perf_counter()
    inv, set_rows, bnk_rows, gt = generate_merchant_dataset("saas", total_count=1000, seed=42)
    duration = time.perf_counter() - start

    assert len(inv) == 1000
    assert len(set_rows) == 1000
    assert len(bnk_rows) == 1000
    assert len(gt) == 1000
    assert duration < 2.0  # Fast sub-2s generation for 1k records


def test_10000_record_generation_performance():
    start = time.perf_counter()
    inv, set_rows, bnk_rows, gt = generate_merchant_dataset("enterprise", total_count=10000, seed=42)
    duration = time.perf_counter() - start

    assert len(inv) == 10000
    assert len(set_rows) == 10000
    assert len(bnk_rows) == 10000
    assert len(gt) == 10000
    assert duration < 10.0  # Scalable sub-10s generation for 10k records
