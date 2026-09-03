#!/usr/bin/env python3
"""Executable counterexamples for the 2026-09-02 statistics snapshot.

This script intentionally confirms fail-open behavior in the pinned producer
revision.  A repaired revision should make this script fail and should replace
it with rejection regressions in the producer's own suite.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
CODE = HERE.parent / "structural-basis" / "code"
sys.path.insert(0, str(CODE))
import importance_statistics as stats  # noqa: E402


def main():
    # An omitted genuinely active coordinate is silently discarded.
    root = stats.largest_generalized_root(
        np.diag([1.0, 1.0]), np.diag([1.0, 100.0]),
        active_indices=[0])
    assert root["root"] == 1.0 and root["vector"][1] == 0.0

    # One flattened batch makes ddof=1 variance NaN; it escapes the function.
    ess = stats.batch_means_ess(
        np.array([0.0]), np.array([1.0]),
        np.zeros((1, 1, 1)), 10)
    assert math.isnan(float(ess[0]))

    # Materially inconsistent raw moments are clamped to a false full ESS.
    ess = stats.batch_means_ess(
        np.array([10.0]), np.array([0.0]),
        np.array([[[9.0], [11.0]], [[9.0], [11.0]]]), 10)
    assert float(ess[0]) == 40.0

    # Negative envelope-z batches are accepted when their mean is positive.
    ratio = stats.ratio_matrix_delta(
        np.array([[[[1.0]], [[3.0]]]]), np.array([[-1.0, 3.0]]))
    assert ratio["mean_denominator"] == 1.0

    # Finite inputs can overflow to nonfinite output without rejection.
    ratio = stats.ratio_matrix_delta(
        np.ones((1, 2, 1, 1)), np.full((1, 2), 1e-320))
    assert math.isinf(float(ratio["ratio"][0, 0]))
    assert math.isnan(float(ratio["standard_error"][0, 0]))
    print("PINNED STATISTICS COUNTEREXAMPLES CONFIRMED")


if __name__ == "__main__":
    main()
