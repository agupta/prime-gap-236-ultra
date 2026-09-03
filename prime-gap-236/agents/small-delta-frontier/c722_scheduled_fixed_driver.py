#!/usr/bin/env python3
"""Fail-closed one-worker C722 fixed-vector discovery driver.

The D4 mode reconstructs the exact C10 and scheduled-C722 scalar forms through
the support-independent kernel.  The target mode is Decimal100 discovery only,
requires a separately frozen gate and root authorization, publishes a fresh
I-stage, and can resume only from a caller-SHA-pinned stage.  It never turns a
Decimal sign into a sieve certificate.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import math
import os
import re
import resource
import stat
import sys
import time
from decimal import Decimal, getcontext
from fractions import Fraction
from pathlib import Path


FILE = Path(__file__).resolve()
HERE = FILE.parent
REPO_ROOT = FILE.parents[2]
EXACT_DIR = REPO_ROOT / "agents/exact-integrator"
STRUCTURAL_CODE = REPO_ROOT / "agents/structural-basis/code"

KERNEL_PATH = STRUCTURAL_CODE / "fixed_vector_support_kernel.py"
SCHEDULED_PATH = EXACT_DIR / "scheduled_fixed_vector.py"
GROUPED_PATH = EXACT_DIR / "grouped_fixed_vector.py"
INTEGRATOR_PATH = EXACT_DIR / "src/exact_integrator.py"
AMPLITUDE_PATH = EXACT_DIR / "stratum_amplitude.py"

D4_SOURCE = EXACT_DIR / "results/c10_fullsimplex_k48_noones_D4.json"
D12_SOURCE = EXACT_DIR / "results/hb_c10_fullsimplex_noones_D12.json"
C722_SCHEDULE = EXACT_DIR / "results/c722_prefix_beta_schedule.json"
C10_D4_REFERENCE = EXACT_DIR / \
    "results/c10_capped_fullD4_vector_grouped_exact.json"
C722_D4_REFERENCE = EXACT_DIR / \
    "results/c722_prefix_eps004_fullvector_D4_exact.json"
ANALYTIC_CHECKER = HERE / "verify_c722_all.py"
D4_REGRESSION_ARTIFACT = HERE / \
    "results/c722_support_port_d4_regression_v2.json"

PINNED_SHA256 = {
    str(KERNEL_PATH.relative_to(REPO_ROOT)):
        "774b8f3a09d77d79d6e4abe56cce4ed1eb82fc5f71ca08cb033bd383091073a3",
    str(SCHEDULED_PATH.relative_to(REPO_ROOT)):
        "a2127b5edb1fd4287f2e105884dee9db7fcd13a5fc36b7016f01680cbb381928",
    str(GROUPED_PATH.relative_to(REPO_ROOT)):
        "47167e92a0f346e969706dc282ccb2dfd4ac31a0a75b654938ffbe8423cf4a4a",
    str(INTEGRATOR_PATH.relative_to(REPO_ROOT)):
        "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52",
    str(AMPLITUDE_PATH.relative_to(REPO_ROOT)):
        "d23d42315d7b518ae5d3f200a6192f47f3500d6eebd3a73fb6aa4ce7a23c7887",
    str(D4_SOURCE.relative_to(REPO_ROOT)):
        "ac48820277b68dd5232fd2678a7980d60318b69e60d15d44d9c6eb006fa1ea0d",
    str(D12_SOURCE.relative_to(REPO_ROOT)):
        "719c656e6e45388273b4c27f51f7a18b33e9ed1abb5f883e6fcc5de5d6d64a87",
    str(C722_SCHEDULE.relative_to(REPO_ROOT)):
        "33baffcd08b5262cf75a2767bf49da198a29cd31ee8bc7c49dafae65a1e59e2a",
    str(C10_D4_REFERENCE.relative_to(REPO_ROOT)):
        "51b1e6b36e289a69f7d52401ed9db7714e014a0182826f0e2d20a1f04b494874",
    str(C722_D4_REFERENCE.relative_to(REPO_ROOT)):
        "9d56ba9cc82e2ab78b99516c458a2dbc29009ab407ffd1bb969464a10ad324d7",
    str(ANALYTIC_CHECKER.relative_to(REPO_ROOT)):
        "4fef5565cb3e0755169801646099e568b2c35896db749139b636980ecb60d701",
}

C722_PARAMETERS = {
    "k": 48,
    "alpha": "3169/12000",
    "delta": "361/50000",
    "eta": "3073/12000",
}
C10_PARAMETERS = {
    "k": 48,
    "alpha": "79247/300000",
    "delta": "1/100",
    "eta": "76247/300000",
}
C10_SCHEDULE = ("3/20", "3/20", "97/625")
C722_ANALYTIC_SCHEDULE_SHA256 = \
    "8c67d65544a8f6036bae6f868eb937cabe963eaec12ec59e3a9fb537a9695f17"
C722_EVALUATOR_SCHEDULE_SHA256 = \
    "b7b737745088b31f50c1c4fd32ac3179d07df5e0f5eeab3838edd70d37f50ced"
EXPECTED_D4_COUNTS = {
    "c10": {"i_orbit_groups": 20, "i_faces": 312,
            "marginal_components": 19, "j_branch_integrals": 1200},
    "c722": {"i_orbit_groups": 20, "i_faces": 625,
             "marginal_components": 19, "j_branch_integrals": 2468},
}
EXPECTED_TARGET_COUNTS = {
    "i_orbit_groups": 1575,
    "i_faces": 625,
    "marginal_components": 695,
    "j_branch_integrals": 2468,
}
EXPECTED_D12_KERNEL_SUMMARY = {
    "status": "support-independent-fixed-vector-kernel-summary",
    "rigorous": False,
    "theorem_ready": False,
    "k": 48,
    "degree": 12,
    "basis_dimension": 272,
    "source_sha256":
        "118f1a1b23cd9f60e6810ca9073225e503169ed429b0ece8342876154bae47ff",
    "orbit_product_pairs": 3003,
    "i_raw_terms": 7338,
    "marginal_raw_terms": 695,
}

RATIONAL_RE = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:/[1-9][0-9]*)?$")
DECIMAL_RE = re.compile(
    r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:E[+-][1-9][0-9]*)?$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_DEPENDENCIES = None


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def require_sha256(value, name):
    if not isinstance(value, str) or SHA_RE.fullmatch(value) is None:
        raise ValueError(f"{name} is not canonical SHA-256")
    return value


def exact_int(value, name, *, minimum=None):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} is not an exact integer")
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} is below its minimum")
    return value


def exact_keys(value, keys, name):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValueError(f"{name} has unexpected schema")


def strict_json_bytes(data, name, *, maximum=32_000_000):
    if not isinstance(data, bytes) or len(data) > maximum:
        raise ValueError(f"{name} is not bounded bytes")

    def pairs_hook(pairs):
        answer = {}
        for key, value in pairs:
            if not isinstance(key, str) or key in answer:
                raise ValueError(f"{name} has duplicate/non-string key")
            answer[key] = value
        return answer

    def reject_float(_token):
        raise ValueError(f"{name} contains a JSON float")

    def reject_constant(_token):
        raise ValueError(f"{name} contains a nonfinite token")

    return json.loads(
        data.decode("utf-8"), object_pairs_hook=pairs_hook,
        parse_float=reject_float, parse_constant=reject_constant)


def canonical_fraction(token, name):
    if not isinstance(token, str) or RATIONAL_RE.fullmatch(token) is None:
        raise ValueError(f"{name} is not a canonical rational string")
    value = Fraction(token)
    if str(value) != token:
        raise ValueError(f"{name} is not reduced/canonical")
    return value


def canonical_decimal(token, name):
    if not isinstance(token, str) or DECIMAL_RE.fullmatch(token) is None:
        raise ValueError(f"{name} is not canonical Decimal text")
    value = Decimal(token)
    if not value.is_finite() or str(value) != token:
        raise ValueError(f"{name} is nonfinite/noncanonical")
    return value


def canonical_json_bytes(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       allow_nan=False) + "\n").encode("utf-8")


def read_snapshot(path, name, *, expected_sha=None, maximum=32_000_000):
    path = Path(path).resolve()
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_size > maximum:
            raise ValueError(f"{name} is not a bounded regular file")
        chunks = []
        total = 0
        while True:
            block = os.read(descriptor, 1024 * 1024)
            if not block:
                break
            total += len(block)
            if total > maximum:
                raise ValueError(f"{name} exceeds byte bound")
            chunks.append(block)
        after = os.fstat(descriptor)
        identity = (before.st_dev, before.st_ino, before.st_size,
                    before.st_mtime_ns, before.st_ctime_ns)
        if identity != (after.st_dev, after.st_ino, after.st_size,
                        after.st_mtime_ns, after.st_ctime_ns):
            raise ArithmeticError(f"{name} changed while read")
        data = b"".join(chunks)
        digest = sha256_bytes(data)
        if expected_sha is not None and digest != require_sha256(
                expected_sha, f"{name} expected SHA"):
            raise ValueError(f"{name} SHA-256 mismatch")
        return {
            "path": str(path), "sha256": digest,
            "device": int(after.st_dev), "inode": int(after.st_ino),
            "data": data,
        }
    finally:
        os.close(descriptor)


def public_binding(snapshot):
    return {key: snapshot[key] for key in ("path", "sha256", "device", "inode")}


def verify_binding(binding, name):
    exact_keys(binding, {"path", "sha256", "device", "inode"}, name)
    require_sha256(binding["sha256"], f"{name} SHA")
    for key in ("device", "inode"):
        exact_int(binding[key], f"{name} {key}", minimum=0)
    observed = read_snapshot(binding["path"], name,
                             expected_sha=binding["sha256"])
    if public_binding(observed) != binding:
        raise ValueError(f"{name} inode/path binding changed")
    return observed


def pinned_snapshot(path, name):
    relative = str(Path(path).resolve().relative_to(REPO_ROOT.resolve()))
    if relative not in PINNED_SHA256:
        raise ValueError(f"{name} has no source pin")
    return read_snapshot(path, name, expected_sha=PINNED_SHA256[relative])


def current_dependency_snapshots():
    return {
        relative: pinned_snapshot(REPO_ROOT / relative, relative)
        for relative in PINNED_SHA256
    }


def load_dependencies():
    global _DEPENDENCIES
    if _DEPENDENCIES is not None:
        return _DEPENDENCIES
    names = ("exact_integrator", "grouped_fixed_vector",
             "scheduled_fixed_vector", "fixed_vector_support_kernel",
             "stratum_amplitude")
    occupied = [name for name in names if name in sys.modules]
    if occupied:
        raise ValueError("preloaded arithmetic modules are forbidden: " +
                         ",".join(occupied))
    for directory in (EXACT_DIR / "src", EXACT_DIR, STRUCTURAL_CODE):
        if str(directory) not in sys.path:
            sys.path.insert(0, str(directory))
    modules = tuple(importlib.import_module(name) for name in names)
    expected_paths = (INTEGRATOR_PATH, GROUPED_PATH, SCHEDULED_PATH,
                      KERNEL_PATH, AMPLITUDE_PATH)
    for module, expected in zip(modules, expected_paths):
        observed = Path(module.__file__).resolve()
        if observed != expected.resolve():
            raise ValueError(f"loaded arithmetic module path mismatch: {module.__name__}")
        pinned_snapshot(expected, f"loaded {module.__name__}")
    _DEPENDENCIES = modules
    return modules


def bucketed_evaluator_class(kernel_mod, amplitude_mod):
    """Combine audited stratum blocks with the support-independent kernel."""
    class BucketedEvaluator(amplitude_mod.StratumAmplitudeEvaluator,
                            kernel_mod.KernelEvaluator):
        pass

    expected = (BucketedEvaluator, amplitude_mod.StratumAmplitudeEvaluator,
                kernel_mod.KernelEvaluator)
    if BucketedEvaluator.__mro__[:3] != expected:
        raise TypeError("unexpected bucketed evaluator method order")
    return BucketedEvaluator


def load_schedule(snapshot, scheduled, k=48):
    raw = strict_json_bytes(snapshot["data"], "beta schedule")
    schedule = scheduled.parse_schedule_payload(raw, k)
    evaluator_sha = sha256_bytes(scheduled.canonical_schedule_bytes(schedule))
    analytic_bytes = ("\n".join(
        f"{value.numerator}/{value.denominator}" for value in schedule) +
        "\n").encode("ascii")
    analytic_sha = sha256_bytes(analytic_bytes)
    if (evaluator_sha != C722_EVALUATOR_SCHEDULE_SHA256 or
            analytic_sha != C722_ANALYTIC_SCHEDULE_SHA256):
        raise ValueError("C722 canonical schedule SHA mismatch")
    return schedule


def normalized_kernel_source_bytes(snapshot):
    """Extract only the exact finite basis/vector from a byte-pinned source.

    Historical source artifacts carry irrelevant floating discovery metadata.
    Their complete bytes are pinned above; no such field is permitted to enter
    the reusable kernel payload.
    """
    raw = json.loads(snapshot["data"])
    if not isinstance(raw, dict):
        raise ValueError("pinned vector source is not an object")
    required = ("k", "degree", "basis_dimension", "basis",
                "rational_vector")
    if any(key not in raw for key in required):
        raise ValueError("pinned vector source misses exact basis data")
    payload = {key: raw[key] for key in required}
    return canonical_json_bytes(payload)


def support_from_tokens(scheduled, parameters, schedule, scalar=Fraction):
    if parameters["k"] != 48:
        raise ValueError("support k must be 48")
    parse = (lambda token: scalar(Fraction(token).numerator) /
             scalar(Fraction(token).denominator))
    return scheduled.ScheduledSupport.from_schedule(
        48, parse(parameters["alpha"]), parse(parameters["delta"]),
        parse(parameters["eta"]), tuple(parse(str(value)) for value in schedule))


def exact_form_strings(forms):
    denominator = Fraction(forms["denominator"])
    j_value = Fraction(forms["j_value"])
    numerator = Fraction(forms["numerator"])
    if numerator != 48 * j_value:
        raise ArithmeticError("factor-48 numerator identity failed")
    if denominator <= 0:
        raise ArithmeticError("denominator is not positive")
    return {
        "denominator": str(denominator),
        "j_value": str(j_value),
        "numerator": str(numerator),
        "quotient": str(numerator / denominator),
        "margin": str(numerator - denominator),
        "i_orbit_groups": exact_int(
            forms["i_orbit_groups"], "i_orbit_groups", minimum=0),
        "i_faces": exact_int(forms["i_faces"], "i_faces", minimum=0),
        "marginal_components": exact_int(
            forms["marginal_components"], "marginal_components", minimum=0),
        "j_branch_integrals": exact_int(
            forms["j_branch_integrals"], "j_branch_integrals", minimum=0),
    }


def reference_form_strings(snapshot, name, source_sha, parameters, counts):
    # These historical exact files contain floating timing metadata, so their
    # whole bytes are hash-pinned before the ordinary JSON parse below.  Only
    # exact strings and exact integer/status fields enter the regression.
    raw = json.loads(snapshot["data"])
    if (raw.get("rigorous") is not True or raw.get("k") != 48 or
            raw.get("basis_dimension") != 12 or
            raw.get("input_sha256") != source_sha or
            raw.get("parameters") != parameters or any(
                raw.get(key) != value for key, value in counts.items())):
        raise ValueError(f"{name} identity/count mismatch")
    values = {}
    for key in ("denominator", "j_value", "numerator", "quotient", "margin"):
        values[key] = str(canonical_fraction(raw.get(key), f"{name} {key}"))
    if Fraction(values["numerator"]) != 48 * Fraction(values["j_value"]):
        raise ArithmeticError(f"{name} factor-48 identity failed")
    values.update({key: raw[key] for key in counts})
    return values


def run_d4_regression(output_path):
    dependencies = current_dependency_snapshots()
    ei, grouped, scheduled, kernel_mod, amplitude_mod = load_dependencies()
    source = dependencies[str(D4_SOURCE.relative_to(REPO_ROOT))]
    schedule_snapshot = dependencies[str(C722_SCHEDULE.relative_to(REPO_ROOT))]
    schedule = load_schedule(schedule_snapshot, scheduled)
    normalized_source = normalized_kernel_source_bytes(source)
    kernel = kernel_mod.compile_kernel_bytes(normalized_source)
    if (kernel.k, kernel.degree, len(kernel.labels)) != (48, 4, 12):
        raise ValueError("D4 source/kernel identity mismatch")
    cases = (
        ("c10", C10_PARAMETERS, tuple(map(Fraction, C10_SCHEDULE)),
         dependencies[str(C10_D4_REFERENCE.relative_to(REPO_ROOT))]),
        ("c722", C722_PARAMETERS, schedule,
         dependencies[str(C722_D4_REFERENCE.relative_to(REPO_ROOT))]),
    )
    reports = {}
    start_total = time.perf_counter()
    for name, parameters, beta, reference_snapshot in cases:
        support = support_from_tokens(scheduled, parameters, beta, Fraction)
        start = time.perf_counter()
        forms = kernel_mod.evaluate_kernel(support, kernel, Fraction, 1)
        seconds = time.perf_counter() - start
        observed = exact_form_strings(forms)
        reference_parameters = {
            key: parameters[key] for key in ("alpha", "delta", "eta")}
        if name == "c10":
            reference_parameters.update({
                "beta1": C10_SCHEDULE[0], "beta2": C10_SCHEDULE[1],
                "beta3plus": C10_SCHEDULE[2],
            })
        expected = reference_form_strings(
            reference_snapshot, name, source["sha256"],
            reference_parameters, EXPECTED_D4_COUNTS[name])
        for key in ("denominator", "j_value", "numerator", "quotient",
                    "margin", "i_orbit_groups", "i_faces",
                    "marginal_components", "j_branch_integrals"):
            if observed[key] != expected[key]:
                raise ArithmeticError(f"{name} D4 regression mismatch for {key}")
        reports[name] = {
            "exact_forms": observed,
            "reference_sha256": reference_snapshot["sha256"],
            "seconds_hex": seconds.hex(),
        }
    elapsed = time.perf_counter() - start_total
    report = {
        "status": "exact-c10-c722-d4-support-kernel-regression-pass",
        "rigorous": True,
        "theorem_ready": False,
        "driver_sha256": sha256_file(FILE),
        "source_binding": public_binding(source),
        "normalized_kernel_source_sha256": sha256_bytes(normalized_source),
        "schedule_binding": public_binding(schedule_snapshot),
        "analytic_schedule_sha256": C722_ANALYTIC_SCHEDULE_SHA256,
        "evaluator_schedule_sha256": C722_EVALUATOR_SCHEDULE_SHA256,
        "dependency_sha256s": {
            relative: snapshot["sha256"]
            for relative, snapshot in dependencies.items()},
        "kernel_summary": kernel_mod.kernel_summary(kernel),
        "workers": 1,
        "cases": reports,
        "total_seconds_hex": elapsed.hex(),
        "peak_rss_kib": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
        "child_peak_rss_kib": int(
            resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss),
        "never_implies": ["D12_quotient", "exact_D12_certificate",
                          "H1_at_most_236"],
    }
    bindings = {snapshot["path"]: public_binding(snapshot)
                for snapshot in dependencies.values()}
    bindings[str(FILE)] = public_binding(read_snapshot(FILE, "driver"))
    digest = publish_new_json(output_path, report, bindings)
    return digest, report


def parse_gate(snapshot):
    raw = strict_json_bytes(snapshot["data"], "C722 one-worker gate")
    exact_keys(raw, {
        "status", "rigorous", "theorem_ready", "driver_sha256",
        "dependency_sha256s", "d4_regression", "target",
        "resource_gate", "continuation_gate", "authorization_required",
    }, "C722 one-worker gate")
    if (raw["status"] != "frozen-c722-d12-one-worker-prelaunch-v1" or
            raw["rigorous"] is not False or raw["theorem_ready"] is not False or
            raw["driver_sha256"] != sha256_file(FILE) or
            raw["dependency_sha256s"] != PINNED_SHA256 or
            raw["authorization_required"] is not True):
        raise ValueError("C722 gate identity/source closure mismatch")
    exact_keys(raw["target"], {
        "source_path", "source_sha256", "schedule_path",
        "schedule_file_sha256", "analytic_schedule_sha256",
        "evaluator_schedule_sha256", "normalized_kernel_source_sha256",
        "kernel_summary", "parameters",
        "decimal_dps", "workers", "expected_counts",
    }, "C722 target")
    target = raw["target"]
    expected_target = {
        "source_path": str(D12_SOURCE.relative_to(REPO_ROOT)),
        "source_sha256": PINNED_SHA256[
            str(D12_SOURCE.relative_to(REPO_ROOT))],
        "schedule_path": str(C722_SCHEDULE.relative_to(REPO_ROOT)),
        "schedule_file_sha256": PINNED_SHA256[
            str(C722_SCHEDULE.relative_to(REPO_ROOT))],
        "analytic_schedule_sha256": C722_ANALYTIC_SCHEDULE_SHA256,
        "evaluator_schedule_sha256": C722_EVALUATOR_SCHEDULE_SHA256,
        "normalized_kernel_source_sha256":
            EXPECTED_D12_KERNEL_SUMMARY["source_sha256"],
        "kernel_summary": EXPECTED_D12_KERNEL_SUMMARY,
        "parameters": C722_PARAMETERS,
        "decimal_dps": 100,
        "workers": 1,
        "expected_counts": EXPECTED_TARGET_COUNTS,
    }
    if target != expected_target:
        raise ValueError("C722 target was changed")
    exact_keys(raw["resource_gate"], {
        "memory_readings_required", "memory_interval_seconds",
        "minimum_mem_available_kib", "maximum_swapout_page_growth",
        "maximum_peak_rss_kib", "maximum_i_seconds",
        "maximum_j_seconds", "maximum_total_seconds",
        "basis_for_limits",
    }, "C722 resource gate")
    resource_gate = raw["resource_gate"]
    for key in ("memory_readings_required", "memory_interval_seconds",
                "minimum_mem_available_kib", "maximum_swapout_page_growth",
                "maximum_peak_rss_kib", "maximum_i_seconds",
                "maximum_j_seconds", "maximum_total_seconds"):
        exact_int(resource_gate[key], f"resource gate {key}", minimum=0)
    if (resource_gate["memory_readings_required"] != 2 or
            resource_gate["memory_interval_seconds"] < 5 or
            resource_gate["minimum_mem_available_kib"] < 1_400_000 or
            resource_gate["maximum_swapout_page_growth"] != 0 or
            resource_gate["maximum_peak_rss_kib"] > 819_200 or
            resource_gate["maximum_total_seconds"] > 21_600 or
            resource_gate["maximum_i_seconds"] +
            resource_gate["maximum_j_seconds"] >
            resource_gate["maximum_total_seconds"] or
            not isinstance(resource_gate["basis_for_limits"], str) or
            not resource_gate["basis_for_limits"]):
        raise ValueError("one-worker resource limits were relaxed/malformed")
    exact_keys(raw["continuation_gate"], {
        "retire_at_or_below", "retain_family_below", "action_at_or_above",
        "display_above_one_requires_exact_reconstruction",
    }, "continuation gate")
    if raw["continuation_gate"] != {
        "retire_at_or_below": "39/40",
        "retain_family_below": "197/200",
        "action_at_or_above": "197/200",
        "display_above_one_requires_exact_reconstruction": True,
    }:
        raise ValueError("continuation thresholds changed")
    exact_keys(raw["d4_regression"], {
        "artifact_path", "artifact_sha256", "status", "workers",
        "c10_exact", "c722_exact", "peak_rss_kib",
        "total_seconds_hex",
    }, "D4 regression gate")
    d4_gate = raw["d4_regression"]
    require_sha256(d4_gate["artifact_sha256"],
                   "D4 regression artifact SHA")
    if d4_gate["artifact_path"] != str(
            D4_REGRESSION_ARTIFACT.relative_to(REPO_ROOT)):
        raise ValueError("D4 regression artifact path changed")
    d4_snapshot = read_snapshot(
        D4_REGRESSION_ARTIFACT, "D4 regression artifact",
        expected_sha=d4_gate["artifact_sha256"])
    d4_raw = strict_json_bytes(d4_snapshot["data"], "D4 regression artifact")
    exact_keys(d4_raw, {
        "status", "rigorous", "theorem_ready", "driver_sha256",
        "source_binding", "normalized_kernel_source_sha256",
        "schedule_binding", "analytic_schedule_sha256",
        "evaluator_schedule_sha256", "dependency_sha256s",
        "kernel_summary", "workers", "cases", "total_seconds_hex",
        "peak_rss_kib", "child_peak_rss_kib", "never_implies",
    }, "D4 regression artifact")
    if (d4_raw["status"] !=
            "exact-c10-c722-d4-support-kernel-regression-pass" or
            d4_raw["rigorous"] is not True or
            d4_raw["theorem_ready"] is not False or
            d4_raw["driver_sha256"] != sha256_file(FILE) or
            d4_raw["dependency_sha256s"] != PINNED_SHA256 or
            d4_raw["workers"] != 1 or
            set(d4_raw["cases"]) != {"c10", "c722"} or
            d4_raw["peak_rss_kib"] != d4_gate["peak_rss_kib"] or
            d4_raw["total_seconds_hex"] != d4_gate["total_seconds_hex"]):
        raise ValueError("D4 regression artifact identity/status mismatch")
    for name, counts in EXPECTED_D4_COUNTS.items():
        case = d4_raw["cases"][name]
        exact_keys(case, {"exact_forms", "reference_sha256", "seconds_hex"},
                   f"D4 {name} case")
        forms = case["exact_forms"]
        exact_keys(forms, {
            "denominator", "j_value", "numerator", "quotient", "margin",
            "i_orbit_groups", "i_faces", "marginal_components",
            "j_branch_integrals",
        }, f"D4 {name} forms")
        for key, value in counts.items():
            if forms[key] != value:
                raise ValueError(f"D4 {name} count mismatch: {key}")
        denominator = canonical_fraction(forms["denominator"],
                                         f"D4 {name} denominator")
        j_value = canonical_fraction(forms["j_value"], f"D4 {name} J")
        numerator = canonical_fraction(forms["numerator"],
                                       f"D4 {name} numerator")
        quotient = canonical_fraction(forms["quotient"],
                                      f"D4 {name} quotient")
        margin = canonical_fraction(forms["margin"], f"D4 {name} margin")
        if (denominator <= 0 or numerator != 48 * j_value or
                quotient != numerator / denominator or
                margin != numerator - denominator):
            raise ArithmeticError(f"D4 {name} form identity failed")
        seconds = float.fromhex(case["seconds_hex"])
        if (not math.isfinite(seconds) or seconds <= 0 or
                seconds.hex() != case["seconds_hex"]):
            raise ValueError(f"D4 {name} timing invalid")
    exact_int(d4_raw["peak_rss_kib"], "D4 peak RSS", minimum=1)
    total_seconds = float.fromhex(d4_raw["total_seconds_hex"])
    if (not math.isfinite(total_seconds) or total_seconds <= 0 or
            total_seconds.hex() != d4_raw["total_seconds_hex"]):
        raise ValueError("D4 total timing invalid")
    if (raw["d4_regression"]["status"] !=
            "exact-c10-c722-d4-support-kernel-regression-pass" or
            raw["d4_regression"]["workers"] != 1 or
            raw["d4_regression"]["c10_exact"] is not True or
            raw["d4_regression"]["c722_exact"] is not True):
        raise ValueError("D4 regression gate did not pass")
    return raw, d4_snapshot


def parse_authorization(snapshot, gate_snapshot, stage_path, output_path):
    raw = strict_json_bytes(snapshot["data"], "C722 target authorization")
    exact_keys(raw, {
        "status", "authorized", "mode", "gate_sha256", "driver_sha256",
        "source_sha256", "i_stage_path", "output_path",
    }, "C722 target authorization")
    if (raw["status"] != "root-authorized-c722-d12-one-worker-scalar" or
            raw["authorized"] is not True or raw["mode"] != "target" or
            raw["gate_sha256"] != gate_snapshot["sha256"] or
            raw["driver_sha256"] != sha256_file(FILE) or
            raw["source_sha256"] != PINNED_SHA256[
                str(D12_SOURCE.relative_to(REPO_ROOT))] or
            Path(raw["i_stage_path"]).resolve() != Path(stage_path).resolve() or
            Path(raw["output_path"]).resolve() != Path(output_path).resolve()):
        raise ValueError("target authorization is misbound")
    return raw


def read_memory_state():
    meminfo = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        fields = line.split()
        if len(fields) >= 2 and fields[0].endswith(":"):
            meminfo[fields[0][:-1]] = int(fields[1])
    vmstat = {}
    for line in Path("/proc/vmstat").read_text().splitlines():
        fields = line.split()
        if len(fields) == 2:
            vmstat[fields[0]] = int(fields[1])
    if "MemAvailable" not in meminfo or "pswpout" not in vmstat:
        raise ValueError("Linux memory/swap counters are unavailable")
    return {"mem_available_kib": meminfo["MemAvailable"],
            "pswpout_pages": vmstat["pswpout"]}


def validate_memory_readings(readings, gate):
    if not isinstance(readings, list) or len(readings) != \
            gate["memory_readings_required"]:
        raise ValueError("wrong number of memory readings")
    for reading in readings:
        exact_keys(reading, {"mem_available_kib", "pswpout_pages"},
                   "memory reading")
        exact_int(reading["mem_available_kib"], "MemAvailable", minimum=0)
        exact_int(reading["pswpout_pages"], "pswpout", minimum=0)
        if reading["mem_available_kib"] < gate["minimum_mem_available_kib"]:
            raise MemoryError("MemAvailable is below the frozen gate")
    if readings[-1]["pswpout_pages"] - readings[0]["pswpout_pages"] > \
            gate["maximum_swapout_page_growth"]:
        raise MemoryError("swap-out counter grew during launch gate")
    return True


def take_memory_readings(gate):
    readings = []
    for index in range(gate["memory_readings_required"]):
        readings.append(read_memory_state())
        if index + 1 < gate["memory_readings_required"]:
            time.sleep(gate["memory_interval_seconds"])
    validate_memory_readings(readings, gate)
    return readings


def validate_stage(raw, *, gate_snapshot, authorization_snapshot,
                   source_snapshot, schedule_snapshot, driver_sha):
    exact_keys(raw, {
        "status", "complete", "rigorous", "theorem_ready", "decimal_dps",
        "workers", "driver_sha256", "gate_binding", "authorization_binding",
        "source_binding", "schedule_binding", "analytic_schedule_sha256",
        "evaluator_schedule_sha256",
        "parameters", "basis_dimension", "kernel_summary", "i_orbit_groups",
        "i_faces", "i_seconds_hex", "peak_rss_kib", "denominator_positive",
        "denominator", "memory_readings", "dependency_sha256s",
    }, "C722 I-stage")
    if (raw["status"] != "c722-d12-decimal100-one-worker-I-stage" or
            raw["complete"] is not True or raw["rigorous"] is not False or
            raw["theorem_ready"] is not False or raw["decimal_dps"] != 100 or
            raw["workers"] != 1 or raw["driver_sha256"] != driver_sha or
            raw["gate_binding"] != public_binding(gate_snapshot) or
            raw["authorization_binding"] != public_binding(
                authorization_snapshot) or
            raw["source_binding"] != public_binding(source_snapshot) or
            raw["schedule_binding"] != public_binding(schedule_snapshot) or
            raw["analytic_schedule_sha256"] !=
            C722_ANALYTIC_SCHEDULE_SHA256 or
            raw["evaluator_schedule_sha256"] !=
            C722_EVALUATOR_SCHEDULE_SHA256 or
            raw["parameters"] != C722_PARAMETERS or
            raw["basis_dimension"] != 272 or
            raw["kernel_summary"] != EXPECTED_D12_KERNEL_SUMMARY or
            raw["i_orbit_groups"] !=
            EXPECTED_TARGET_COUNTS["i_orbit_groups"] or
            raw["i_faces"] != EXPECTED_TARGET_COUNTS["i_faces"] or
            raw["denominator_positive"] is not True or
            raw["dependency_sha256s"] != PINNED_SHA256):
        raise ValueError("C722 I-stage identity/status mismatch")
    exact_int(raw["i_orbit_groups"], "stage orbit groups", minimum=1)
    exact_int(raw["peak_rss_kib"], "stage peak RSS", minimum=1)
    canonical_decimal(raw["denominator"], "stage denominator")
    if canonical_decimal(raw["denominator"], "stage denominator") <= 0:
        raise ArithmeticError("stage denominator is not positive")
    if not isinstance(raw["i_seconds_hex"], str):
        raise ValueError("stage timing is not float-hex")
    seconds = float.fromhex(raw["i_seconds_hex"])
    if not math.isfinite(seconds) or seconds <= 0 or seconds.hex() != \
            raw["i_seconds_hex"]:
        raise ValueError("stage timing is invalid")
    return True


def validate_output_path(path, trusted_paths):
    path = Path(path)
    if not path.name or Path(path.name).name != path.name:
        raise ValueError("output must be one safe leaf")
    parent = path.parent.resolve()
    if not parent.is_dir():
        raise ValueError("output parent does not exist")
    candidate = parent / path.name
    if candidate in {Path(value).resolve() for value in trusted_paths}:
        raise ValueError("output aliases a trusted input")
    if os.path.lexists(candidate):
        raise FileExistsError("output path must be fresh")
    return candidate


def publish_new_json(path, payload, bindings):
    path = validate_output_path(path, bindings)
    for binding in bindings.values():
        verify_binding(binding, "publication dependency")
    parent_flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        parent_flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        parent_flags |= os.O_NOFOLLOW
    parent_fd = os.open(path.parent, parent_flags)
    output_fd = None
    try:
        parent_stat = os.fstat(parent_fd)
        flags = os.O_RDWR | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        output_fd = os.open(path.name, flags, 0o600, dir_fd=parent_fd)
        encoded = canonical_json_bytes(payload)
        digest = sha256_bytes(encoded)
        written = 0
        while written < len(encoded):
            count = os.write(output_fd, encoded[written:])
            if count <= 0:
                raise OSError("short output write")
            written += count
        os.fsync(output_fd)
        for binding in bindings.values():
            verify_binding(binding, "publication dependency")
        current_parent = os.stat(path.parent, follow_symlinks=False)
        if (current_parent.st_dev, current_parent.st_ino) != \
                (parent_stat.st_dev, parent_stat.st_ino):
            raise ArithmeticError("output parent changed")
        check_fd = os.open(path.name, os.O_RDONLY, dir_fd=parent_fd)
        try:
            check_stat = os.fstat(check_fd)
            chunks = []
            while True:
                block = os.read(check_fd, 1024 * 1024)
                if not block:
                    break
                chunks.append(block)
            if ((check_stat.st_dev, check_stat.st_ino) !=
                    (os.fstat(output_fd).st_dev, os.fstat(output_fd).st_ino) or
                    sha256_bytes(b"".join(chunks)) != digest):
                raise ArithmeticError("published output inode/hash changed")
        finally:
            os.close(check_fd)
        os.close(output_fd)
        output_fd = None
        return digest
    except Exception:
        if output_fd is not None:
            rejection = b'{"status":"rejected-incomplete-c722-output"}\n'
            os.lseek(output_fd, 0, os.SEEK_SET)
            os.ftruncate(output_fd, 0)
            os.write(output_fd, rejection)
            os.fsync(output_fd)
        raise
    finally:
        if output_fd is not None:
            os.close(output_fd)
        os.close(parent_fd)


def target_run(args):
    driver_sha = sha256_file(FILE)
    gate_snapshot = read_snapshot(
        args.gate, "one-worker gate", expected_sha=args.expected_gate_sha256)
    gate, d4_snapshot = parse_gate(gate_snapshot)
    stage_path = Path(args.i_stage).resolve()
    output_path = Path(args.output).resolve()
    authorization_snapshot = read_snapshot(
        args.authorization, "target authorization",
        expected_sha=args.expected_authorization_sha256)
    parse_authorization(authorization_snapshot, gate_snapshot,
                        stage_path, output_path)
    trusted = [FILE, args.gate, args.authorization, D12_SOURCE,
               C722_SCHEDULE, *[REPO_ROOT / key for key in PINNED_SHA256]]
    output_path = validate_output_path(output_path, trusted + [stage_path])
    resume = args.resume_i_stage_sha256 is not None
    if resume:
        stage_snapshot = read_snapshot(
            stage_path, "resumed I-stage",
            expected_sha=args.resume_i_stage_sha256)
    else:
        stage_path = validate_output_path(stage_path, trusted + [output_path])

    dependency_snapshots = current_dependency_snapshots()
    source_snapshot = dependency_snapshots[
        str(D12_SOURCE.relative_to(REPO_ROOT))]
    schedule_snapshot = dependency_snapshots[
        str(C722_SCHEDULE.relative_to(REPO_ROOT))]
    ei, grouped, scheduled, kernel_mod, amplitude_mod = load_dependencies()
    schedule = load_schedule(schedule_snapshot, scheduled)
    memory_readings = take_memory_readings(gate["resource_gate"])
    normalized_source = normalized_kernel_source_bytes(source_snapshot)
    kernel = kernel_mod.compile_kernel_bytes(normalized_source)
    if (kernel.k, kernel.degree, len(kernel.labels)) != (48, 12, 272):
        raise ValueError("D12 source/kernel identity mismatch")
    if kernel_mod.kernel_summary(kernel) != EXPECTED_D12_KERNEL_SUMMARY:
        raise ValueError("D12 support-independent kernel summary changed")
    orbit_table = dict(kernel.orbit_products)
    scalar = grouped.install_decimal(orbit_table, 100)
    getcontext().prec = 100
    support = support_from_tokens(scheduled, C722_PARAMETERS, schedule, scalar)
    evaluator = kernel_mod.KernelEvaluator(support, kernel, scalar)
    bindings = {snapshot["path"]: public_binding(snapshot)
                for snapshot in dependency_snapshots.values()}
    bindings[str(FILE)] = public_binding(read_snapshot(FILE, "driver"))
    bindings[gate_snapshot["path"]] = public_binding(gate_snapshot)
    bindings[d4_snapshot["path"]] = public_binding(d4_snapshot)
    bindings[authorization_snapshot["path"]] = public_binding(
        authorization_snapshot)

    if resume:
        stage_raw = strict_json_bytes(stage_snapshot["data"], "resumed I-stage")
        validate_stage(
            stage_raw, gate_snapshot=gate_snapshot,
            authorization_snapshot=authorization_snapshot,
            source_snapshot=source_snapshot, schedule_snapshot=schedule_snapshot,
            driver_sha=driver_sha)
        validate_memory_readings(stage_raw["memory_readings"],
                                 gate["resource_gate"])
        denominator = canonical_decimal(stage_raw["denominator"],
                                        "stage denominator")
        orbit_groups = stage_raw["i_orbit_groups"]
        i_faces = stage_raw["i_faces"]
        i_seconds = float.fromhex(stage_raw["i_seconds_hex"])
        bindings[stage_snapshot["path"]] = public_binding(stage_snapshot)
    else:
        i_start = time.perf_counter()
        denominator, orbit_groups, i_faces = evaluator.evaluate_i(
            args.progress, 1)
        i_seconds = time.perf_counter() - i_start
        stage_raw = {
            "status": "c722-d12-decimal100-one-worker-I-stage",
            "complete": True,
            "rigorous": False,
            "theorem_ready": False,
            "decimal_dps": 100,
            "workers": 1,
            "driver_sha256": driver_sha,
            "gate_binding": public_binding(gate_snapshot),
            "authorization_binding": public_binding(authorization_snapshot),
            "source_binding": public_binding(source_snapshot),
            "schedule_binding": public_binding(schedule_snapshot),
            "analytic_schedule_sha256": C722_ANALYTIC_SCHEDULE_SHA256,
            "evaluator_schedule_sha256": C722_EVALUATOR_SCHEDULE_SHA256,
            "parameters": C722_PARAMETERS,
            "basis_dimension": len(kernel.labels),
            "kernel_summary": kernel_mod.kernel_summary(kernel),
            "i_orbit_groups": orbit_groups,
            "i_faces": i_faces,
            "i_seconds_hex": i_seconds.hex(),
            "peak_rss_kib": int(resource.getrusage(
                resource.RUSAGE_SELF).ru_maxrss),
            "denominator_positive": denominator > 0,
            "denominator": str(denominator),
            "memory_readings": memory_readings,
            "dependency_sha256s": PINNED_SHA256,
        }
        validate_stage(
            stage_raw, gate_snapshot=gate_snapshot,
            authorization_snapshot=authorization_snapshot,
            source_snapshot=source_snapshot, schedule_snapshot=schedule_snapshot,
            driver_sha=driver_sha)
        stage_digest = publish_new_json(stage_path, stage_raw, bindings)
        stage_snapshot = read_snapshot(stage_path, "fresh I-stage",
                                       expected_sha=stage_digest)
        bindings[stage_snapshot["path"]] = public_binding(stage_snapshot)

    j_start = time.perf_counter()
    j_value, marginal_components, branch_integrals = evaluator.evaluate_j(
        args.progress, 1)
    j_seconds = time.perf_counter() - j_start
    numerator = scalar(48) * j_value
    margin = numerator - denominator
    quotient = numerator / denominator
    peak = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    total_seconds = i_seconds + j_seconds
    resource_pass = (
        i_seconds <= gate["resource_gate"]["maximum_i_seconds"] and
        j_seconds <= gate["resource_gate"]["maximum_j_seconds"] and
        total_seconds <= gate["resource_gate"]["maximum_total_seconds"] and
        peak <= gate["resource_gate"]["maximum_peak_rss_kib"])
    if (orbit_groups != EXPECTED_TARGET_COUNTS["i_orbit_groups"] or
            i_faces != EXPECTED_TARGET_COUNTS["i_faces"] or
            marginal_components !=
            EXPECTED_TARGET_COUNTS["marginal_components"] or
            branch_integrals !=
            EXPECTED_TARGET_COUNTS["j_branch_integrals"]):
        raise ArithmeticError("target traversal counts changed")
    result = {
        "status": ("c722-d12-decimal100-one-worker-complete" if resource_pass
                   else "c722-d12-decimal100-resource-gate-failed"),
        "complete": True,
        "rigorous": False,
        "theorem_ready": False,
        "driver_sha256": driver_sha,
        "gate_binding": public_binding(gate_snapshot),
        "authorization_binding": public_binding(authorization_snapshot),
        "source_binding": public_binding(source_snapshot),
        "schedule_binding": public_binding(schedule_snapshot),
        "i_stage_binding": public_binding(stage_snapshot),
        "parameters": C722_PARAMETERS,
        "decimal_dps": 100,
        "workers": 1,
        "basis_dimension": len(kernel.labels),
        "i_orbit_groups": orbit_groups,
        "i_faces": i_faces,
        "marginal_components": marginal_components,
        "j_branch_integrals": branch_integrals,
        "i_seconds_hex": i_seconds.hex(),
        "j_seconds_hex": j_seconds.hex(),
        "total_seconds_hex": total_seconds.hex(),
        "peak_rss_kib": peak,
        "memory_readings": memory_readings,
        "resource_gate_passed": resource_pass,
        "denominator_positive": denominator > 0,
        "factor_48_identity": numerator == scalar(48) * j_value,
        "denominator": str(denominator),
        "j_value": str(j_value),
        "numerator_48J": str(numerator),
        "margin_48J_minus_I": str(margin),
        "quotient_48J_over_I": str(quotient),
        "display_above_one": quotient > 1,
        "continuation_gate": gate["continuation_gate"],
        "fresh_exact_reconstruction_required": True,
        "never_implies": ["rigorous_error_bound", "exact_sieve_quotient",
                          "H1_at_most_236"],
    }
    digest = publish_new_json(output_path, result, bindings)
    return digest, result


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="mode", required=True)
    regression = subparsers.add_parser("d4-regression")
    regression.add_argument("--output", required=True)
    target = subparsers.add_parser("target")
    target.add_argument("--gate", required=True)
    target.add_argument("--expected-gate-sha256", required=True)
    target.add_argument("--authorization", required=True)
    target.add_argument("--expected-authorization-sha256", required=True)
    target.add_argument("--i-stage", required=True)
    target.add_argument("--resume-i-stage-sha256")
    target.add_argument("--output", required=True)
    target.add_argument("--progress", action="store_true")
    args = parser.parse_args()
    if args.mode == "d4-regression":
        digest, report = run_d4_regression(args.output)
        print(json.dumps({"output_sha256": digest,
                          "status": report["status"]}, sort_keys=True))
    else:
        digest, result = target_run(args)
        print(json.dumps({"output_sha256": digest,
                          "status": result["status"],
                          "quotient": result["quotient_48J_over_I"]},
                         sort_keys=True))


if __name__ == "__main__":
    main()
