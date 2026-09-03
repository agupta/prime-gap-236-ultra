#!/usr/bin/env python3
"""Fail-closed orchestration skeleton for the final three independent checks.

This file is deliberately UNARMED.  Exact capped I/J/margin strings and the
final success text remain ``None`` until the capped calculation has completed
and been audited.  In its present state it exits before launching any child
process and has no code path that can print a final success claim.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from fractions import Fraction
from pathlib import Path
from typing import Sequence


ROOT = Path(__file__).resolve().parent

# These are intentionally absent.  Arming requires an audited code change,
# not a command-line flag or environment variable.
EXPECTED_EXACT_I: str | None = None
EXPECTED_EXACT_J: str | None = None
EXPECTED_EXACT_MARGIN: str | None = None
FINAL_SUCCESS_TEXT: str | None = None

ANALYTIC_SENTINEL = "C10 HOSTILE ANALYTIC EXACT PASS"
TUPLE_SHA256 = "adfe71549293c2ff0efda34397e46c72269b2895ae23fc2fdfc34ccacc579ba9"
ORDERED_VECTOR_PAYLOAD_SHA256 = "8ea54de0e3bb4d9f978fee80a6788c81d542a7d6839ed8c69e22a5374845fe4e"


class OrchestrationError(RuntimeError):
    pass


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    answer: dict[str, object] = {}
    for key, value in pairs:
        if key in answer:
            raise OrchestrationError(f"duplicate JSON key from child: {key!r}")
        answer[key] = value
    return answer


def _parse_json_object(text: str, stage: str) -> dict[str, object]:
    try:
        value = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=lambda token: (_ for _ in ()).throw(
                OrchestrationError(f"{stage} emitted non-finite JSON token {token}")
            ),
        )
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise OrchestrationError(f"{stage} did not emit one valid JSON value: {exc}") from exc
    if not isinstance(value, dict):
        raise OrchestrationError(f"{stage} JSON output is not an object")
    return value


def _canonical_fraction(value: str | None, name: str) -> Fraction:
    if value is None:
        raise OrchestrationError(f"orchestrator is unarmed: {name} is not pinned")
    try:
        parsed = Fraction(value)
    except (ValueError, ZeroDivisionError) as exc:
        raise OrchestrationError(f"invalid pinned {name}: {exc}") from exc
    if str(parsed) != value:
        raise OrchestrationError(f"pinned {name} is not a canonical fraction")
    return parsed


def _validated_expected_values() -> tuple[Fraction, Fraction, Fraction]:
    i_value = _canonical_fraction(EXPECTED_EXACT_I, "I")
    j_value = _canonical_fraction(EXPECTED_EXACT_J, "J")
    margin = _canonical_fraction(EXPECTED_EXACT_MARGIN, "margin")
    if i_value <= 0:
        raise OrchestrationError("pinned I is not positive")
    if margin <= 0:
        raise OrchestrationError("pinned capped margin is not positive")
    if 48 * j_value - i_value != margin:
        raise OrchestrationError("pinned I, J, and margin are inconsistent")
    if FINAL_SUCCESS_TEXT is None or not FINAL_SUCCESS_TEXT.strip():
        raise OrchestrationError("orchestrator is unarmed: final success text is absent")
    return i_value, j_value, margin


def _run_stage(name: str, command: Sequence[str], timeout_seconds: int) -> str:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONHASHSEED"] = "0"
    try:
        completed = subprocess.run(
            list(command),
            cwd=ROOT,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="strict",
            timeout=timeout_seconds,
            check=False,
        )
    except (OSError, subprocess.SubprocessError, UnicodeError) as exc:
        raise OrchestrationError(f"{name} could not complete: {exc}") from exc
    if completed.returncode != 0:
        detail = completed.stderr[-4000:] or completed.stdout[-4000:]
        raise OrchestrationError(f"{name} exited {completed.returncode}: {detail}")
    if completed.stderr:
        raise OrchestrationError(f"{name} emitted unexpected stderr: {completed.stderr[-4000:]}")
    if len(completed.stdout) > 5_000_000:
        raise OrchestrationError(f"{name} stdout exceeds 5 MB")
    return completed.stdout


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments:
        print(json.dumps({"verified": False, "error": "verify_all.py accepts no arguments"}), file=sys.stderr)
        return 2
    try:
        expected_i, expected_j, expected_margin = _validated_expected_values()

        analytic_output = _run_stage(
            "analytic checker",
            [sys.executable, "-I", str(ROOT / "agents/hostile-analytic-audit/c10_audit_exact.py")],
            300,
        )
        if analytic_output.splitlines()[-1:] != [ANALYTIC_SENTINEL]:
            raise OrchestrationError("analytic checker omitted its exact terminal sentinel")

        exact_output = _run_stage(
            "exact capped checker",
            [
                sys.executable,
                "-I",
                str(ROOT / "verify/exact_capped_certificate.py"),
                str(ROOT / "agents/exact-integrator/results/hb_c10_fullsimplex_noones_D12.json"),
                "--preset",
                "target-c10-d12",
                "--allow-d12",
            ],
            86_400,
        )
        exact = _parse_json_object(exact_output, "exact capped checker")
        expected_exact_fields = {
            "checker": "independent exact capped certificate v2 tagged-residual",
            "tagged_nonzero_source_terms": 272,
            "I": str(expected_i),
            "J": str(expected_j),
            "M2": str(48 * expected_j),
            "M2_minus_M1": str(expected_margin),
            "ordered_label_vector_provenance_sha256": ORDERED_VECTOR_PAYLOAD_SHA256,
            "certificate_passes": True,
            "cM1c_positive": True,
            "c_M2_minus_M1_c_positive": True,
            "streaming_order": "forward",
            "workers": 1,
        }
        for key, expected in expected_exact_fields.items():
            if exact.get(key) != expected:
                raise OrchestrationError(
                    f"exact capped checker field {key!r} differs: {exact.get(key)!r} != {expected!r}"
                )
        expected_support = {
            "k": 48,
            "degree": 12,
            "alpha": "79247/300000",
            "eta": "76247/300000",
            "delta": "1/100",
            "A": "77747/300000",
            "epsilon": "1/200",
            "beta1": "3/20",
            "beta2": "3/20",
            "beta3plus": "97/625",
            "c1": "0",
            "c2": "0",
        }
        if exact.get("support") != expected_support:
            raise OrchestrationError("exact capped checker returned the wrong support metadata")
        if exact.get("quotient") != str(48 * expected_j / expected_i):
            raise OrchestrationError("exact capped checker returned the wrong exact quotient")

        tuple_output = _run_stage(
            "independent tuple verifier",
            [sys.executable, "-I", str(ROOT / "verify/independent_tuple_verifier.py")],
            60,
        )
        tuple_result = _parse_json_object(tuple_output, "independent tuple verifier")
        if tuple_result.get("tuple_verified") is not True:
            raise OrchestrationError("tuple verifier did not return tuple_verified=true")
        if tuple_result.get("sha256") != TUPLE_SHA256:
            raise OrchestrationError("tuple verifier returned the wrong pinned SHA-256")
        expected_tuple_fields = {
            "size": 48,
            "minimum": 0,
            "maximum": 236,
            "diameter": 236,
        }
        for key, expected in expected_tuple_fields.items():
            if tuple_result.get(key) != expected:
                raise OrchestrationError(f"tuple verifier returned the wrong {key}")

        # This is unreachable while the four arming constants above are None.
        print(FINAL_SUCCESS_TEXT)
        return 0
    except (OrchestrationError, ValueError) as exc:
        print(json.dumps({"verified": False, "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
