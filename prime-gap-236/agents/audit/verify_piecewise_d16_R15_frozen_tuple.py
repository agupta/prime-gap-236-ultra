#!/usr/bin/env python3
"""Independent prelaunch audit of the frozen R15 selective tuple.

The specialized evaluator's branch reduction is checked exactly against the
unpruned evaluator in a fresh low-dimensional fixture.  The tuple verdict is
nevertheless FAIL because its frozen assembler accepts unauthenticated,
fabricated stage records and publishes through dangling symlinks.
"""

from __future__ import annotations

import argparse
from contextlib import redirect_stderr, redirect_stdout
from fractions import Fraction as Q
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import unittest


FILE = Path(__file__).resolve()
REPO = FILE.parents[2]
FILES = {
    "agents/small-delta-frontier/piecewise_d16_capped_target.py":
        "cb84d4eb6d24c7be2315b8195b8e0c1a6a9bc52e68e4e5f6a656ea41252e667c",
    "agents/small-delta-frontier/test_piecewise_d16_capped_target.py":
        "7fbbeb2b548f00189da774347052d1140392b59e64b50a71772a867b02a8c08e",
    "agents/small-delta-frontier/piecewise_d16_R15_specialized.py":
        "5086a4a381d301ae3a5b321f5e5afba685b677d6851694ef555f6ec76d7fdc58",
    "agents/small-delta-frontier/test_piecewise_d16_R15_specialized.py":
        "20caf2130d94a5380cba30e891cf94a4dcd3517f7bea4f940149f7b697d011ef",
    "agents/small-delta-frontier/assemble_piecewise_d16_R15.py":
        "290dc32bf233083ffa52162a4176e0618d6a1fb932d009ca73740d349fe3a363",
    "agents/small-delta-frontier/test_assemble_piecewise_d16_R15.py":
        "9e32d0b1c9cb5a3f5b018587c7620cef1099d2cfa68b9e9d0edb528f41e21ef6",
    "agents/audit/test_piecewise_d16_R15_frozen_assembler_forgery.py":
        "cafcf414804a136b85a79b54425a009b093e2dffcb3a9470ffcbf50610657947",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ArithmeticError(message)


def load(relative: str, name: str):
    path = REPO / relative
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None,
            f"cannot load {relative}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    require(Path(module.__file__).resolve() == path.resolve(),
            f"wrong module loaded for {relative}")
    return module


def tiny_kernel(base, k, labels, coefficients):
    payload = {
        "basis": [[a, list(lam)] for a, lam in labels],
        "basis_dimension": len(labels),
        "degree": max(a + sum(lam) for a, lam in labels),
        "k": k,
        "rational_vector": [str(Q(x)) for x in coefficients],
    }
    data = (json.dumps(payload, sort_keys=True, separators=(",", ":")) +
            "\n").encode("ascii")
    return base.kernel_core.compile_kernel_bytes(data)


def verify_exact_branch_reduction(module):
    base = module.M
    k = 3
    labels = tuple(base.ei.even_basis(4))
    inner = tuple(Q((-1) ** i * (3 * i + 2), 2 * i + 5)
                  for i in range(len(labels)))
    outer = tuple(Q((i % 4) - 2, i + 7) for i in range(len(labels)))
    kernels = {
        "inner": tiny_kernel(base, k, labels, inner),
        "outer": tiny_kernel(base, k, labels, outer),
    }
    delta, eta = Q(1, 10), Q(1, 4)
    supports = {
        "inner_eta2": base.ei.OneStratumSupport(
            k, Q(13, 50), delta, eta,
            Q(13, 50), Q(13, 50), Q(13, 50)),
        "high": base.ScheduledSupport.make(
            k, Q(7, 20), delta, eta,
            (Q(1, 5), Q(3, 10), Q(2, 5))),
        "low": base.ScheduledSupport.make(
            k, Q(13, 50), delta, eta,
            (Q(1, 5), Q(3, 10), Q(2, 5))),
    }
    catalog = (
        ("fh", "inner_eta2", "high"),
        ("fl", "inner_eta2", "low"),
        ("hh", "high", "high"),
        ("hl", "high", "low"),
        ("ll", "low", "low"),
    )
    target = 2
    checked = 0
    for common in (target - 1, target):
        filtered, _, filtered_faces = module.specialized_cross_r(
            supports, kernels, Q, catalog, common, target)
        full, _, full_faces = base.cross_bundle_r(
            supports, kernels, Q, catalog, common)
        require(filtered_faces == full_faces,
                "filtered/full face inventory differs")
        for tag, left_name, right_name in catalog:
            expected = sum((value for (left, right), value in
                            full[tag].items()
                            if ((left_name.startswith("inner") or
                                 left == target) and
                                (right_name.startswith("inner") or
                                 right == target))), Q(0))
            require(filtered[tag] == expected,
                    f"branch reduction differs at r={common}, tag={tag}")
            checked += 1
    require(module.outer_branches(15, 14) == ("Ltotal", "Lbig") and
            module.outer_branches(15, 15) == ("Sdelta", "Stotal") and
            not module.outer_branches(15, 13),
            "production target branch inventory differs")
    return checked


def run_counterexamples():
    module = load(
        "agents/audit/test_piecewise_d16_R15_frozen_assembler_forgery.py",
        "audit_R15_frozen_forgery_suite")
    suite = unittest.defaultTestLoader.loadTestsFromModule(module)
    stream = io.StringIO()
    with redirect_stdout(stream), redirect_stderr(stream):
        result = unittest.TextTestRunner(stream=stream, verbosity=0).run(suite)
    require(result.wasSuccessful() and result.testsRun == 2,
            "frozen assembler counterexamples did not reproduce")
    return result.testsRun


def build():
    for relative, expected in FILES.items():
        require(sha(REPO / relative) == expected,
                f"frozen R15 tuple changed: {relative}")
    module = load(
        "agents/small-delta-frontier/piecewise_d16_R15_specialized.py",
        "audit_R15_specialized_frozen")
    exact_checks = verify_exact_branch_reduction(module)
    hostile_checks = run_counterexamples()
    return {
        "status": "AUDIT FAIL",
        "scope": "frozen R15 selective prelaunch tuple",
        "checker_sha256": sha(FILE),
        "pinned": FILES,
        "specialized_evaluator": {
            "status": "branch-reduction PASS",
            "fresh_exact_low_dimensional_tag_checks": exact_checks,
            "production_common_count_14_branches": ["Ltotal", "Lbig"],
            "production_common_count_15_branches": [
                "Sdelta", "Stotal"],
            "factor_48_location": "assembler only",
            "single-coordinate_shell_polarization":
                "HH+LL-2HL is valid by bilinear symmetry",
        },
        "assembler": {
            "status": "FAIL",
            "counterexamples_reproduced": hostile_checks,
            "fabricated_stage_without_source_hashes_accepted": True,
            "fabricated_support_parameters_accepted": True,
            "arbitrary_numeric_bilinears_accepted": True,
            "dangling_output_symlink_followed": True,
            "cause": (
                "a manifest-provided digest pins only caller-chosen bytes; "
                "the assembler trusts spoofable script hash fields without "
                "validating full stage provenance/support schema, and uses "
                "exists()+write_bytes instead of exclusive publication"),
        },
        "decision": (
            "a cost-only run of the frozen specialized evaluator is safe, "
            "but no stage assembly or result consumption is authorized until "
            "a new fail-closed assembler is frozen and independently audited"),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = (json.dumps(build(), sort_keys=True, separators=(",", ":"),
                          allow_nan=False) + "\n").encode("ascii")
    if args.output is not None:
        target = args.output.resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    print(payload.decode("ascii"), end="")


if __name__ == "__main__":
    main()
