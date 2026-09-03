#!/usr/bin/env python3
"""Canonical entry point for the independent importance-gate v5 audit.

The underlying hostile suite retains its historical ``_v3`` filename because
that suite contains the executable v3 and v4 regression witnesses.
"""

from pathlib import Path
import runpy


runpy.run_path(
    str(Path(__file__).with_name("audit_importance_d4_calibration_v3.py")),
    run_name="__main__",
)
