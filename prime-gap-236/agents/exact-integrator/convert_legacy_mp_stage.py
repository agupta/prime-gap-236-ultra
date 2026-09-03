#!/usr/bin/env python3
"""One-off, fail-closed conversion of a legacy *non-rigorous* I stage.

Early discovery stages hashed the grouped driver but omitted the imported
``exact_integrator.py``.  This tool never converts an exact stage.  It preserves
the originating driver hash, verifies the input vector and current dependency,
and attaches an explicit conversion record so a later MP-only resume can name
the old driver hash with ``--accept-i-stage-script-sha``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
CURRENT_DRIVER = HERE / "grouped_fixed_vector.py"
CURRENT_INTEGRATOR = HERE / "src" / "exact_integrator.py"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("legacy_stage")
    parser.add_argument("output_stage")
    parser.add_argument("--expected-old-script-sha", required=True)
    parser.add_argument("--expected-new-script-sha", required=True)
    parser.add_argument("--expected-integrator-sha", required=True)
    args = parser.parse_args()

    old_path = Path(args.legacy_stage)
    old_bytes = old_path.read_bytes()
    stage = json.loads(old_bytes)
    if stage.get("rigorous") is not False or stage.get("decimal_dps") is None:
        raise SystemExit("refusing to convert anything except a Decimal discovery stage")
    if not stage.get("i_complete") or not stage.get("denominator_positive"):
        raise SystemExit("legacy I stage is incomplete or has nonpositive denominator")
    if stage.get("integrator_sha256") is not None:
        raise SystemExit("stage already has an integrator hash; conversion is unnecessary")
    if stage.get("script_sha256") != args.expected_old_script_sha:
        raise SystemExit("legacy grouped-driver hash mismatch")
    new_hash = sha(CURRENT_DRIVER)
    integrator_hash = sha(CURRENT_INTEGRATOR)
    if new_hash != args.expected_new_script_sha:
        raise SystemExit(f"current grouped-driver hash mismatch: {new_hash}")
    if integrator_hash != args.expected_integrator_sha:
        raise SystemExit(f"current integrator hash mismatch: {integrator_hash}")

    input_path = HERE / stage["input_json"]
    if sha(input_path) != stage.get("input_sha256"):
        raise SystemExit("input vector hash mismatch")

    stage["integrator_sha256"] = integrator_hash
    stage["legacy_nonrigorous_conversion"] = {
        "source_stage_sha256": hashlib.sha256(old_bytes).hexdigest(),
        "origin_script_sha256": args.expected_old_script_sha,
        "resume_script_sha256": new_hash,
        "attached_integrator_sha256": integrator_hash,
        "conversion_script_sha256": sha(Path(__file__)),
        "scope": "non-rigorous Decimal discovery only",
    }
    Path(args.output_stage).write_text(json.dumps(stage, indent=2) + "\n",
                                       encoding="utf-8")
    print("LEGACY MP I-STAGE CONVERSION PASS")
    print(f"source_stage_sha256={stage['legacy_nonrigorous_conversion']['source_stage_sha256']}")
    print(f"origin_script_sha256={args.expected_old_script_sha}")
    print(f"resume_script_sha256={new_hash}")
    print(f"integrator_sha256={integrator_hash}")


if __name__ == "__main__":
    main()
