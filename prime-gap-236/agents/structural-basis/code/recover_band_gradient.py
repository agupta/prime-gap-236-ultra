#!/usr/bin/env python3
"""Byte-pinned recovery of the completed C10 D12 Decimal gradient.

The production traversal correctly rejected its own output because nine
redundant ``gradient/2`` diagnostic entries rounded by one last-place Decimal
unit.  This wrapper does not alter or bless that raw artifact.  It independently
rechecks every substantive producer invariant, requires the raw bytes by SHA,
and reconstructs ``A theta`` and ``B theta`` exactly as Fraction(gradient, 2).

The output is still discovery-only and intentionally contains no optimized
trial or projected trial quotient.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXACT_AGENT = HERE.parents[1] / "exact-integrator"
sys.path[:0] = [str(HERE), str(EXACT_AGENT), str(EXACT_AGENT / "src")]

from band_operator import BandMap  # noqa: E402


RAW_SHA = "0ac99ee5a72a83576eaf92ad203280dd0359b290a5c1562652bf9be1259d644d"
BASELINE_SHA = "02e1a6676a68380592fd272845f7714d583574bd74f73b9a96727171751281d9"
PINNED = {
    "source": "719c656e6e45388273b4c27f51f7a18b33e9ed1abb5f883e6fcc5de5d6d64a87",
    "bands": "29d38a9e7ca7a352560c0a01813f2dfd2f477ec8cb829c433cce18d8229d31e9",
    "sparse": "e1545435f0c7ad22a17115ac46c291436c1ead5101fd3de6d2a80ab65bc9c257",
    "band": "e4fbf7a97d061d362c32b54bf0d49a89c4195b965e96d7ab89a2581bc907c073",
    "grouped": "47167e92a0f346e969706dc282ccb2dfd4ac31a0a75b654938ffbe8423cf4a4a",
    "integrator": "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52",
}
PARAMETERS = {
    "alpha": Fraction(79247, 300000), "delta": Fraction(1, 100),
    "eta": Fraction(76247, 300000), "beta1": Fraction(3, 20),
    "beta2": Fraction(3, 20), "beta3plus": Fraction(97, 625),
}
EXPECTED_PRODUCER_GATES = {
    "decimal_dps_at_least_90", "source_sha_pinned", "bands_sha_pinned",
    "operator_unchanged_during_run", "band_dependency_sha_pinned_and_unchanged",
    "grouped_sha_pinned_and_unchanged", "integrator_sha_pinned_and_unchanged",
    "source_k48_dim272_banddim20", "parameters_exact_c10",
    "all_vectors_length20", "all_numbers_finite", "gradient_halves_match",
    "denominator_positive", "quotient_recomputed",
    "euler_relative_below_1e50", "complete_traversal_counts",
    "stratum_buckets_sum", "baseline_artifact_sha_pinned",
    "baseline_dependencies_match", "baseline_forms_50_digits",
}
EXPECTED_MISMATCHES = {
    "a_theta": {7, 12, 16, 17},
    "b_theta": {10, 16, 17, 18, 19},
}


def sha(data_or_path):
    if isinstance(data_or_path, (bytes, bytearray)):
        data = bytes(data_or_path)
    else:
        data = Path(data_or_path).read_bytes()
    return hashlib.sha256(data).hexdigest()


def dec(text):
    q = Fraction(text)
    return Decimal(q.numerator) / Decimal(q.denominator)


def dependency_paths():
    return {
        "sparse": HERE / "band_operator_sparse.py",
        "band": HERE / "band_operator.py",
        "grouped": EXACT_AGENT / "grouped_fixed_vector.py",
        "integrator": EXACT_AGENT / "src/exact_integrator.py",
    }


def trusted_input_paths(raw_path, source_path, bands_path):
    """Every path which must be impossible to overwrite as output."""
    baseline = EXACT_AGENT / "results" / \
        "c10_capped_fullD12_vector_grouped_mp100.json"
    return [Path(raw_path), Path(source_path), Path(bands_path), baseline,
            Path(__file__), *dependency_paths().values()]


def require_distinct_output(output_path, trusted_paths):
    output = Path(output_path).resolve()
    resolved_trusted = [Path(path).resolve() for path in trusted_paths]
    if len(set(resolved_trusted)) != len(resolved_trusted):
        raise ValueError("trusted recovery inputs unexpectedly alias")
    if output in set(resolved_trusted):
        raise ValueError("output aliases a trusted recovery input")


def atomic_write(path, rendered):
    """Write only after validation, then atomically replace the output path."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=target.parent,
                prefix=target.name + ".tmp.", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(rendered)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    except Exception:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise


def validate_rejected(raw_bytes, source_path, bands_path):
    """Return parsed raw data, exact recovered halves, and mismatch evidence."""
    errors = []

    def require(condition, message):
        if not condition:
            errors.append(message)

    require(sha(raw_bytes) == RAW_SHA, "raw artifact SHA")
    try:
        raw = json.loads(raw_bytes)
    except Exception as exc:
        raise ValueError(f"raw JSON parse: {exc}") from exc
    band_map = BandMap.from_source_and_bands(source_path, bands_path)
    source = json.loads(Path(source_path).read_bytes())
    require(raw.get("status") == "rejected-degree-band-gradient-discovery",
            "raw status")
    require(raw.get("implementation") == "sparse-structure-of-arrays" and
            raw.get("rigorous") is False and raw.get("complete") is True and
            raw.get("gates_passed") is False, "raw arithmetic/status")
    gates = raw.get("gates", {})
    require(set(gates) == EXPECTED_PRODUCER_GATES, "producer gate key set")
    require({key for key, value in gates.items() if not value} ==
            {"gradient_halves_match"}, "sole producer rejection reason")
    require(sha(source_path) == band_map.source_sha256 == PINNED["source"] and
            raw.get("source_sha256") == PINNED["source"], "source SHA")
    require(sha(bands_path) == band_map.bands_sha256 == PINNED["bands"] and
            raw.get("bands_sha256") == PINNED["bands"], "bands SHA")
    dependencies = dependency_paths()
    require(all(sha(path) == PINNED[key] for key, path in dependencies.items()),
            "current dependency SHAs")
    require(raw.get("operator_sha256") == PINNED["sparse"] and
            raw.get("band_operator_dependency_sha256") == PINNED["band"] and
            raw.get("grouped_evaluator_sha256") == PINNED["grouped"] and
            raw.get("integrator_sha256") == PINNED["integrator"],
            "serialized dependency SHAs")
    require(int(raw.get("decimal_dps", 0)) == 100 and raw.get("workers") == 2,
            "precision/workers")
    require(all(Fraction(raw.get("parameters", {}).get(key, "NaN")) == value
                for key, value in PARAMETERS.items()), "parameters")
    require(source.get("k") == 48 and len(source.get("basis", [])) == 272 and
            band_map.dimension == 20, "dimensions")
    vector_keys = ("theta", "a_theta", "b_theta", "grad_denominator",
                   "grad_numerator")
    require(all(len(raw.get(key, [])) == 20 for key in vector_keys),
            "vector lengths")

    recovered = {}
    mismatch_evidence = {}
    try:
        dps = int(raw["decimal_dps"])
        with localcontext() as ctx:
            ctx.prec = dps
            theta = [dec(x) for x in raw["theta"]]
            expected_theta = [dec(q) for q in band_map.theta0_q]
            denominator, numerator = dec(raw["denominator"]), dec(raw["numerator"])
            quotient = dec(raw["quotient"])
            grad_d = [dec(x) for x in raw["grad_denominator"]]
            grad_n = [dec(x) for x in raw["grad_numerator"]]
            raw_a = [dec(x) for x in raw["a_theta"]]
            raw_b = [dec(x) for x in raw["b_theta"]]
            euler_d = sum((x * y for x, y in zip(theta, grad_d)), Decimal(0)) - \
                Decimal(2) * denominator
            euler_n = sum((x * y for x, y in zip(theta, grad_n)), Decimal(0)) - \
                Decimal(2) * numerator
            serialized_euler_d = dec(raw["euler_denominator_error"])
            serialized_euler_n = dec(raw["euler_numerator_error"])
            recomputed_q = numerator / denominator
            i_sum = sum((dec(x) for x in raw["i_value_by_r"]), Decimal(0))
            n_sum = Decimal(48) * sum(
                (dec(x) for x in raw["j_value_by_r"]), Decimal(0))
        require(theta == expected_theta, "theta0")
        require(denominator > 0 and quotient == recomputed_q,
                "denominator/quotient")
        require(euler_d == serialized_euler_d and
                euler_n == serialized_euler_n,
                "Euler serialization")
        require(abs(euler_d) <= Decimal("1e-50") * abs(denominator) and
                abs(euler_n) <= Decimal("1e-50") * abs(numerator),
                "Euler tolerance")
        require(i_sum == denominator and n_sum == numerator, "by-r sums")
        all_numbers = theta + grad_d + grad_n + raw_a + raw_b + \
            [denominator, numerator, quotient, euler_d, euler_n]
        require(all(x.is_finite() for x in all_numbers), "finite values")

        for half_key, grad_key in (("a_theta", "grad_denominator"),
                                   ("b_theta", "grad_numerator")):
            evidence = []
            mismatches = set()
            exact_halves = []
            for index, (half_text, grad_text) in enumerate(
                    zip(raw[half_key], raw[grad_key])):
                half, gradient = Fraction(half_text), Fraction(grad_text)
                exact_halves.append(gradient / 2)
                difference = 2 * half - gradient
                if difference:
                    mismatches.add(index)
                    relative = abs(difference / gradient) if gradient else None
                    require(relative is not None and relative <= Fraction(1, 10**98),
                            f"{half_key}[{index}] mismatch magnitude")
                    evidence.append({
                        "index": index,
                        "twice_recorded_half_minus_gradient": str(difference),
                        "relative_to_gradient": str(relative),
                    })
            require(mismatches == EXPECTED_MISMATCHES[half_key],
                    f"{half_key} mismatch indices")
            recovered[half_key] = [str(x) for x in exact_halves]
            mismatch_evidence[half_key] = evidence
    except Exception as exc:
        errors.append(f"numeric reconstruction: {exc}")

    require((raw.get("i_orbit_groups"), raw.get("i_faces"),
             raw.get("marginal_components"), raw.get("j_branch_integrals")) ==
            (1575, 312, 695, 1200), "traversal counts")
    require(len(raw.get("i_value_by_r", [])) == 16 and
            len(raw.get("j_value_by_r", [])) == 16, "bucket lengths")
    try:
        baseline_path = EXACT_AGENT / "results" / \
            "c10_capped_fullD12_vector_grouped_mp100.json"
        baseline_bytes = baseline_path.read_bytes()
        baseline = json.loads(baseline_bytes)
        require(sha(baseline_bytes) == raw.get("baseline_sha256") == BASELINE_SHA,
                "baseline SHA")
        require(baseline.get("input_sha256") == PINNED["source"] and
                baseline.get("script_sha256") == PINNED["grouped"] and
                baseline.get("integrator_sha256") == PINNED["integrator"] and
                all(Fraction(baseline.get("parameters", {}).get(key, "NaN")) == value
                    for key, value in PARAMETERS.items()), "baseline bindings")
        with localcontext() as ctx:
            ctx.prec = 100
            for key in ("denominator", "numerator", "quotient"):
                observed, reference = dec(raw[key]), dec(baseline[key])
                require(abs(observed - reference) <= Decimal("1e-50") *
                        abs(reference), f"baseline {key}")
    except Exception as exc:
        errors.append(f"baseline validation: {exc}")
    require(float(raw.get("total_seconds", -1)) > 0 and
            float(raw.get("i_seconds", -1)) > 0 and
            float(raw.get("j_seconds", -1)) > 0 and
            int(raw.get("peak_rss_kib", -1)) > 0 and
            int(raw.get("child_peak_rss_kib", -1)) > 0,
            "runtime/resource metadata")
    if errors:
        raise ValueError("; ".join(errors))
    return raw, recovered, mismatch_evidence


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True)
    ap.add_argument("--source", required=True)
    ap.add_argument("--bands", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    trusted = trusted_input_paths(args.raw, args.source, args.bands)
    try:
        require_distinct_output(args.output, trusted)
    except ValueError as exc:
        raise SystemExit(f"recovery output validation failed: {exc}") from exc
    raw_bytes = Path(args.raw).read_bytes()
    try:
        raw, recovered, evidence = validate_rejected(
            raw_bytes, args.source, args.bands)
    except Exception as exc:
        raise SystemExit(f"recovery validation failed: {exc}") from exc
    result = {
        "status": "byte-pinned-recovered-degree-band-gradient-discovery",
        "rigorous": False,
        "complete": True,
        "no_projected_trial_emitted": True,
        "raw_json": args.raw,
        "raw_sha256": RAW_SHA,
        "recovery_script_sha256": sha(__file__),
        "source_json": args.source,
        "source_sha256": PINNED["source"],
        "bands_json": args.bands,
        "bands_sha256": PINNED["bands"],
        "decimal_dps": raw["decimal_dps"],
        "parameters": raw["parameters"],
        "theta": raw["theta"],
        "denominator": raw["denominator"],
        "numerator": raw["numerator"],
        "grad_denominator": raw["grad_denominator"],
        "grad_numerator": raw["grad_numerator"],
        "a_theta_exact_fraction_half": recovered["a_theta"],
        "b_theta_exact_fraction_half": recovered["b_theta"],
        "recorded_half_mismatch_evidence": evidence,
        "recovery_statement": (
            "A_theta and B_theta are reconstructed solely as the exact rational "
            "halves of the serialized gradient channels; recorded half arrays "
            "remain diagnostics and are not consumed."),
        "validation_gates": {
            "raw_bytes_sha_pinned": True,
            "sole_raw_failure_is_redundant_halves": True,
            "substantive_producer_invariants_recomputed": True,
            "dependencies_and_parameters_pinned": True,
            "exact_half_mismatch_below_1e98_relative": True,
            "no_projected_trial_or_quotient_emitted": True,
        },
    }
    # Close the time-of-check/time-of-write window for every trusted byte input.
    expected_hashes = {
        Path(args.raw).resolve(): RAW_SHA,
        Path(args.source).resolve(): PINNED["source"],
        Path(args.bands).resolve(): PINNED["bands"],
        (EXACT_AGENT / "results" /
         "c10_capped_fullD12_vector_grouped_mp100.json").resolve(): BASELINE_SHA,
        Path(__file__).resolve(): result["recovery_script_sha256"],
        **{path.resolve(): PINNED[key]
           for key, path in dependency_paths().items()},
    }
    if any(sha(path) != expected for path, expected in expected_hashes.items()):
        raise SystemExit("trusted recovery input changed before output write")
    require_distinct_output(args.output, expected_hashes)
    atomic_write(args.output, json.dumps(result, indent=2) + "\n")
    print(json.dumps({
        "status": result["status"],
        "raw_sha256": result["raw_sha256"],
        "recovery_script_sha256": result["recovery_script_sha256"],
        "mismatch_counts": {key: len(value) for key, value in evidence.items()},
        "no_projected_trial_emitted": True,
    }, indent=2))


if __name__ == "__main__":
    main()
