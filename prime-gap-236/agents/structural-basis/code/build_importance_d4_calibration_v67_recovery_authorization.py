#!/usr/bin/env python3
"""Build the explicit authority for a v6.6 records-only v6.7 recovery.

The default output is deliberately unauthorized.  ``--authorize`` is an
external root action: it binds the exact recovery source closure, all 128
already validated checkpoint inodes/hashes, the original v6.6 authority and
rejection sentinel, and one fresh output leaf/parent inode.  It never runs a
chain or computes the calibration analysis.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys


FILE = Path(__file__).resolve()
RECOVERY_PATH = FILE.with_name("importance_d4_calibration_v67_recover.py")
_spec = importlib.util.spec_from_file_location(
    "importance_v67_recovery_authority_dependency", RECOVERY_PATH)
R = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = R
_spec.loader.exec_module(R)
V5 = R.V5


def build_authorization(output_target, authorized):
    context = R.open_completed_v66_inputs()
    try:
        loaded, _, _, _ = R.load_completed_checkpoints(context)
        source_hashes = {
            relative: R.sha256_file(R.REPO / relative)
            for relative in R.RECOVERY_SOURCE_RELATIVES
        }
        output_target = Path(output_target)
        parent = V5.read_directory_binding(output_target.parent)
        payload = {
            "status": ("root-authorized-v6.7-records-only-recovery"
                       if authorized else
                       "v6.7-records-only-recovery-authorization-template"),
            "authorized": bool(authorized),
            "mode": "records-only-no-chain-execution",
            "recovery_driver_sha256": R.sha256_file(R.FILE),
            "recovery_source_hashes": source_hashes,
            "v66_gate_binding": V5.public_binding(context["bound"]),
            "v66_authorization_binding":
                V5.public_binding(context["authorization"]),
            "v66_rejected_output_binding":
                V5.public_binding(context["rejected"]),
            "record_directory_binding": {
                "path": context["directory"]["path"],
                "device": context["directory"]["device"],
                "inode": context["directory"]["inode"],
            },
            "checkpoint_bindings": [V5.public_binding(item)
                                    for item in loaded],
            "output_parent_binding": parent,
            "output_leaf": output_target.name,
        }
        return payload, context, loaded
    except Exception:
        V5.close_bound_directory(context["directory"])
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-target", required=True)
    parser.add_argument("--authorization-output", required=True)
    parser.add_argument("--authorize", action="store_true")
    args = parser.parse_args()
    R.validate_recovery_paths(
        args.output_target, args.authorization_output)
    payload, context, loaded = build_authorization(
        args.output_target, args.authorize)
    try:
        extra = {
            context["bound"]["path"]: V5.inode_binding(context["bound"]),
            context["authorization"]["path"]:
                V5.inode_binding(context["authorization"]),
            context["rejected"]["path"]:
                V5.inode_binding(context["rejected"]),
            context["directory"]["path"]:
                V5.directory_inode_binding(context["directory"]),
            **{item["path"]: V5.inode_binding(item) for item in loaded},
        }
        for relative in R.RECOVERY_SOURCE_RELATIVES:
            snapshot = V5.read_file_snapshot(R.REPO / relative)
            extra[snapshot["path"]] = V5.inode_binding(snapshot)
        digest = V5.write_new_result(
            Path(args.authorization_output).resolve(), payload,
            context["gate"],
            extra_hashes=extra)
    finally:
        V5.close_bound_directory(context["directory"])
    print(json.dumps({"authorized": args.authorize,
                      "authorization_sha256": digest,
                      "checkpoint_count": len(loaded)}, sort_keys=True))


if __name__ == "__main__":
    main()
