#!/usr/bin/env python3
"""Materialize the already-emitted exactly-once D3 consumer stdout.

This does not call ``consume`` or either eigensolver.  It binds the closed
producer result and frozen consumer bytes, replays metadata only, and combines
the exact producer contraction strings with the captured numerical verdict.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import stat
from decimal import Decimal
from pathlib import Path


HERE = Path(__file__).resolve().parent
CONSUMER = HERE / "consume_stratum_moment_d4_degree3.py"
CONSUMER_SHA = \
    "fedf1970b197af825675fa62644aa227875487453d125ad454d213ebcdedfb7c"
RESULT_SHA = \
    "c9cce84c8a75f231738edabfb7c0ca17e48085b2f4e27f4305866103b8d4d0f5"
RESULT = HERE / "results/c10_D4_degree3_moment_exact.json"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load_consumer():
    raw = CONSUMER.read_bytes()
    require(sha(raw) == CONSUMER_SHA, "frozen consumer SHA")
    spec = importlib.util.spec_from_file_location("frozen_d3_consumer", CONSUMER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, raw


def captured_report(result, consumer):
    report = {
        "a_matrix_sha256":
            "5a412e448a8156d8b4f6d94d58a146b6c2b9e05a0dacd5c47b20720e2dad985e",
        "authorization_sha256": consumer.AUTHORIZATION_SHA,
        "b48_matrix_sha256":
            "58aa4b989641517597c85c0c3ad85d7a3bf96faed6665a3331ed3fa211a74252",
        "claim_scope": (
            "exact reconstruction from the pinned producer serialization, "
            "rank/D2 checks and, conditionally, one exact rational-vector "
            "contraction; no independent source integration and no rigorous "
            "eigenvalue bound"),
        "consumer_gate_sha256": consumer.CONSUMER_GATE_SHA,
        "consumer_gate_status":
            "frozen-c10-d4-degree3-moment-consumer-prelaunch",
        "consumer_sha256": CONSUMER_SHA,
        "degree2_principal_entries_equal": True,
        "degree2_reference_sha256": consumer.REFERENCE_SHA,
        "discarded_gram_coordinates": [
            [0, [1, 0]], [0, [2, 0]], [0, [1, 1]],
            [0, [3, 0]], [0, [2, 1]], [0, [1, 2]],
        ],
        "eigenvalue_discovery_rigorous": False,
        "embedded_degree2_denominator": result["particular_denominator"],
        "embedded_degree2_numerator": result["particular_numerator"],
        "exact_continuation_gate": False,
        "exact_gram_pivot_sha256":
            "465e53036085cbeb95a5550bb12e9db6630ef40bbe5a6b6faf9b642693e45dce",
        "exact_gram_rank": 154,
        "exact_matrix_reconstruction_from_pinned_rows": True,
        "matrix_source":
            "canonical dense I rows and inventory-bounded sparse J rows",
        "numerical_improvement_gate": False,
        "precision_runs": [
            {
                "eigenvalue": (
                    "0.965771840087705066168062245096739512875007039788566008141615541026623339835477352669322252000242905837266219756507103297"),
                "jacobi_rotations": 73233,
                "precision": 120,
                "rayleigh_quotient": (
                    "0.965771840087705066168062245096739512875007039788566008141615541026623339835477352669322252000242905837266219756505935644"),
                "relative_residual":
                    "2.8218140023815041231512883418E-113",
            },
            {
                "eigenvalue": (
                    "0.96577184008770506616806224509673951287500703978856600814161554102662333983547735266932225200024290583726621975650488081514883381166322058462304862211517719967184236411206587607324371745245368699707079"),
                "jacobi_rotations": 83514,
                "precision": 200,
                "rayleigh_quotient": (
                    "0.96577184008770506616806224509673951287500703978856600814161554102662333983547735266932225200024290583726621975650488081514883381166322058462304862211517719967184236411206587607324371745245368698711443"),
                "relative_residual":
                    "3.29180150950760746842745282011E-192",
            },
        ],
        "producer_gate_sha256": consumer.PRODUCER_GATE_SHA,
        "producer_result_sha256": RESULT_SHA,
        "rationalization_performed": False,
        "rationalized_particular": None,
        "relative_quotient_disagreement":
            "1.054828851166188336779415377E-114",
        "serialized_matrix_hash_role": "secondary equality check only",
        "source_integrals_independently_recomputed": False,
        "sparse_j_omission_semantics": (
            "omitted queried tags reconstruct as zero under pinned producer "
            "fused/unfused trust; rows alone do not prove source-integral zero"),
        "status": "c10-d4-degree3-consumer-no-exact-continuation",
        "theorem_ready": False,
    }
    require(all(Decimal(run["rayleigh_quotient"]) < 1
                for run in report["precision_runs"]),
            "captured quotients not below one")
    require(report["embedded_degree2_denominator"] ==
            result["particular_denominator"] and
            report["embedded_degree2_numerator"] ==
            result["particular_numerator"],
            "captured exact contraction binding")
    return report


def publish(path_text, payload, protected):
    path = Path(path_text).absolute()
    require(path not in protected, "report aliases pinned input")
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        require(stat.S_ISREG(os.fstat(descriptor).st_mode),
                "report output regular")
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            require(written > 0, "short report write")
            offset += written
        os.fsync(descriptor)
        require(path.read_bytes() == payload, "report publication bytes")
    finally:
        os.close(descriptor)
    return sha(payload)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    consumer, consumer_raw = load_consumer()
    result_snapshot = consumer.read_pinned(
        RESULT, RESULT_SHA, "closed D3 producer result", consumer.MAX_RESULT_BYTES)
    result = consumer.strict_json(
        result_snapshot.raw, "closed D3 producer result")
    producer_gate, producer_gate_snapshot = consumer.load_producer_gate()
    consumer.validate_result_metadata(result, producer_gate)
    _, authorization_snapshot = consumer.load_authorization()
    report = captured_report(result, consumer)
    payload = (json.dumps(report, sort_keys=True, separators=(",", ":")) +
               "\n").encode()
    protected = {
        RESULT.absolute(), CONSUMER.absolute(),
        producer_gate_snapshot.path.absolute(),
        authorization_snapshot.path.absolute(),
    }
    digest = publish(args.output, payload, protected)
    require(CONSUMER.read_bytes() == consumer_raw, "consumer closure")
    consumer.verify_snapshot(
        result_snapshot, "closed D3 producer result closure",
        consumer.MAX_RESULT_BYTES)
    consumer.verify_snapshot(
        authorization_snapshot, "authorization closure", 100_000)
    print(json.dumps({
        "status": report["status"], "report_sha256": digest,
        "report_bytes": len(payload),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
