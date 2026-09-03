#!/usr/bin/env python3
"""Stratified C10 D4 importance calibration driver.

This is fail-closed discovery infrastructure.  It estimates normalized D4
correlation matrices but cannot certify a sieve quotient.  Production mode
requires a separate byte-pinned authorization artifact; no such artifact is
shipped with the prelaunch gate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import resource
import stat
import time
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path

import numpy as np

from importance_conditional import (
    conditional_metropolis_step,
    point_stratum,
    randomized_interior_start,
)
from importance_density import C10ImportanceDensity
from importance_envelope import bounded_outer_entry, j_envelope_point
from importance_oracle import load_exact_expectation_oracle, principal_indices
from importance_statistics import (
    batch_means_ess,
    largest_generalized_root,
    ratio_matrix_delta,
    simultaneous_coverage,
    split_rhat,
)
from importance_stratum_weights import load_stratum_weights


HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[3]
DIMENSION = 96
CHANNEL_COUNT = 6
STRATA = tuple(range(16))
FLOAT_ENCODING = "python-float-hex"

REQUIRED_SOURCE_PATHS = (
    "agents/structural-basis/code/importance_point_eval.py",
    "agents/structural-basis/code/importance_sampler.py",
    "agents/structural-basis/code/importance_oracle.py",
    "agents/structural-basis/code/importance_density.py",
    "agents/structural-basis/code/importance_stratum_weights.py",
    "agents/structural-basis/code/importance_envelope.py",
    "agents/structural-basis/code/importance_conditional.py",
    "agents/structural-basis/code/importance_statistics.py",
    "agents/structural-basis/code/importance_d4_calibration.py",
    "agents/structural-basis/tests/test_importance_point_eval.py",
    "agents/structural-basis/tests/test_importance_sampler.py",
    "agents/structural-basis/tests/test_importance_oracle.py",
    "agents/structural-basis/tests/test_importance_density.py",
    "agents/structural-basis/tests/test_importance_stratum_weights.py",
    "agents/structural-basis/tests/test_importance_envelope.py",
    "agents/structural-basis/tests/test_importance_conditional.py",
    "agents/structural-basis/tests/test_importance_statistics.py",
    "agents/structural-basis/tests/test_importance_hostile_crosscheck.py",
    "agents/structural-basis/tests/test_importance_d4_calibration.py",
    "agents/structural-basis/IMPORTANCE-D4-CALIBRATION-SPEC.md",
    "agents/structural-basis/IMPORTANCE-DISCOVERY-AUDIT.md",
    "agents/structural-basis/IMPORTANCE-STRATIFICATION.md",
    "agents/small-delta-frontier/audit_importance_conditional_statistics.py",
    "agents/small-delta-frontier/IMPORTANCE-CONDITIONAL-STATISTICS-REAUDIT.md",
)

REQUIRED_DATA_PATHS = (
    "agents/exact-integrator/results/c10_stratum_quadratic_cappedopt_D4_exact.json",
    "agents/exact-integrator/results/c10_capped_D4_decimal55_vector_input.json",
    "agents/exact-integrator/results/c10_stratum_linear_D4_decimal160_cut10.json",
)


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    return sha256_bytes(Path(path).read_bytes())


def read_file_snapshot(path, *, maximum_bytes=256_000_000):
    """Read one regular-file inode once and return bytes plus its binding."""
    path = Path(path)
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    try:
        before = os.fstat(descriptor)
        if (not stat.S_ISREG(before.st_mode) or before.st_size < 0 or
                before.st_size > maximum_bytes):
            raise ValueError("bound input is not a bounded regular file")
        chunks = []
        remaining = maximum_bytes + 1
        while remaining:
            block = os.read(descriptor, min(1024 * 1024, remaining))
            if not block:
                break
            chunks.append(block)
            remaining -= len(block)
        data = b"".join(chunks)
        after = os.fstat(descriptor)
        if (len(data) > maximum_bytes or
                (before.st_dev, before.st_ino, before.st_size,
                 before.st_mtime_ns, before.st_ctime_ns) !=
                (after.st_dev, after.st_ino, after.st_size,
                 after.st_mtime_ns, after.st_ctime_ns) or
                len(data) != after.st_size):
            raise ArithmeticError("bound input changed during its single read")
        return {
            "path": str(path.resolve()), "data": data,
            "sha256": sha256_bytes(data), "device": int(after.st_dev),
            "inode": int(after.st_ino),
        }
    finally:
        os.close(descriptor)


def public_binding(snapshot):
    return {key: snapshot[key]
            for key in ("path", "sha256", "device", "inode")}


def inode_binding(snapshot):
    return {key: snapshot[key] for key in ("sha256", "device", "inode")}


def read_directory_binding(path):
    """Bind one existing real directory by canonical path and inode."""
    resolved = str(Path(path).resolve())
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(resolved, flags)
    try:
        observed = os.fstat(descriptor)
        if not stat.S_ISDIR(observed.st_mode):
            raise ValueError("checkpoint directory is not a real directory")
        return {"path": resolved, "device": int(observed.st_dev),
                "inode": int(observed.st_ino)}
    finally:
        os.close(descriptor)


def directory_inode_binding(snapshot):
    if not isinstance(snapshot, dict) or not {
            "path", "device", "inode"} <= set(snapshot):
        raise ValueError("malformed directory binding")
    return {"kind": "directory", "device": snapshot["device"],
            "inode": snapshot["inode"]}


def validate_directory_binding(value, path, *, name="directory binding"):
    if not isinstance(value, dict) or set(value) != {
            "path", "device", "inode"}:
        raise ValueError(f"{name} has an unexpected schema")
    if (not isinstance(value["path"], str) or
            str(Path(value["path"]).resolve()) != value["path"] or
            any(isinstance(value[key], bool) or not isinstance(value[key], int)
                or value[key] < 0 for key in ("device", "inode"))):
        raise ValueError(f"{name} is malformed")
    observed = read_directory_binding(path)
    if observed != value:
        raise ValueError(f"{name} does not bind the supplied directory")
    return observed


def open_bound_directory(binding):
    """Hold an authorized directory inode for all later *at operations."""
    if not isinstance(binding, dict) or set(binding) != {
            "path", "device", "inode"}:
        raise ValueError("cannot open malformed directory binding")
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(binding["path"], flags)
    observed = os.fstat(descriptor)
    if (not stat.S_ISDIR(observed.st_mode) or
            (int(observed.st_dev), int(observed.st_ino)) !=
            (binding["device"], binding["inode"])):
        os.close(descriptor)
        raise ValueError("opened directory differs from authorized inode")
    handle = {**binding, "descriptor": descriptor}
    validate_open_directory(handle)
    return handle


def close_bound_directory(handle):
    descriptor = handle.get("descriptor") if isinstance(handle, dict) else None
    if isinstance(descriptor, int) and not isinstance(descriptor, bool):
        os.close(descriptor)
        handle["descriptor"] = None


def validate_open_directory(handle):
    """Require both held descriptor and canonical pathname to bind one inode."""
    if not isinstance(handle, dict) or set(handle) != {
            "path", "device", "inode", "descriptor"}:
        raise ValueError("malformed open directory handle")
    descriptor = handle["descriptor"]
    if isinstance(descriptor, bool) or not isinstance(descriptor, int):
        raise ValueError("directory descriptor is not open")
    held = os.fstat(descriptor)
    if (not stat.S_ISDIR(held.st_mode) or
            (int(held.st_dev), int(held.st_ino)) !=
            (handle["device"], handle["inode"])):
        raise ValueError("held directory inode changed")
    current = read_directory_binding(handle["path"])
    if current != {key: handle[key]
                   for key in ("path", "device", "inode")}:
        raise ValueError("authorized directory pathname was replaced")
    return True


def _directory_leaf(name):
    if (not isinstance(name, str) or not name or name in (".", "..") or
            Path(name).name != name or "/" in name or "\x00" in name):
        raise ValueError("checkpoint name is not one safe directory leaf")
    return name


def directory_entry_exists(handle, name):
    validate_open_directory(handle)
    name = _directory_leaf(name)
    try:
        os.stat(name, dir_fd=handle["descriptor"], follow_symlinks=False)
    except FileNotFoundError:
        return False
    return True


def read_file_snapshot_at(handle, name, *, maximum_bytes=256_000_000):
    """Read one checkpoint relative to the held authorized directory."""
    validate_open_directory(handle)
    name = _directory_leaf(name)
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(name, flags, dir_fd=handle["descriptor"])
    try:
        before = os.fstat(descriptor)
        if (not stat.S_ISREG(before.st_mode) or before.st_size < 0 or
                before.st_size > maximum_bytes):
            raise ValueError("bound checkpoint is not a bounded regular file")
        chunks = []
        remaining = maximum_bytes + 1
        while remaining:
            block = os.read(descriptor, min(1024 * 1024, remaining))
            if not block:
                break
            chunks.append(block)
            remaining -= len(block)
        data = b"".join(chunks)
        after = os.fstat(descriptor)
        if (len(data) > maximum_bytes or
                (before.st_dev, before.st_ino, before.st_size,
                 before.st_mtime_ns, before.st_ctime_ns) !=
                (after.st_dev, after.st_ino, after.st_size,
                 after.st_mtime_ns, after.st_ctime_ns) or
                len(data) != after.st_size):
            raise ArithmeticError(
                "bound checkpoint changed during its single read")
        validate_open_directory(handle)
        return {
            "path": str(Path(handle["path"]) / name), "data": data,
            "sha256": sha256_bytes(data), "device": int(after.st_dev),
            "inode": int(after.st_ino),
        }
    finally:
        os.close(descriptor)


def validate_public_binding(value, *, expected_sha256=None, name="binding"):
    if not isinstance(value, dict) or set(value) != {
            "path", "sha256", "device", "inode"}:
        raise ValueError(f"{name} has an unexpected schema")
    if (not isinstance(value["path"], str) or
            str(Path(value["path"]).resolve()) != value["path"] or
            not isinstance(value["sha256"], str) or
            len(value["sha256"]) != 64 or any(
                c not in "0123456789abcdef" for c in value["sha256"]) or
            any(isinstance(value[key], bool) or not isinstance(value[key], int)
                or value[key] < 0 for key in ("device", "inode"))):
        raise ValueError(f"{name} is malformed")
    if expected_sha256 is not None and value["sha256"] != expected_sha256:
        raise ValueError(f"{name} SHA-256 mismatch")
    return True


def _reject_json_float(_token):
    raise ValueError("JSON floats are forbidden; use exact strings")


def _reject_json_constant(_token):
    raise ValueError("nonfinite JSON token")


def strict_json_bytes(data, what="JSON artifact"):
    if not isinstance(data, bytes) or len(data) > 256_000_000:
        raise ValueError(f"{what} must be bounded bytes")

    def pairs_hook(pairs):
        answer = {}
        for key, value in pairs:
            if not isinstance(key, str) or key in answer:
                raise ValueError(f"{what} has a duplicate/non-string key")
            answer[key] = value
        return answer

    return json.loads(
        data.decode("utf-8"), object_pairs_hook=pairs_hook,
        parse_float=_reject_json_float, parse_constant=_reject_json_constant)


def float_hex(value):
    value = float(value)
    if not math.isfinite(value):
        raise ArithmeticError("cannot serialize a nonfinite float")
    return value.hex()


def parse_float_hex(value, name="float"):
    if not isinstance(value, str):
        raise ValueError(f"{name} must use {FLOAT_ENCODING}")
    try:
        parsed = float.fromhex(value)
    except ValueError as error:
        raise ValueError(f"malformed {name}") from error
    if not math.isfinite(parsed) or parsed.hex() != value:
        raise ValueError(f"noncanonical or nonfinite {name}")
    return parsed


def validate_run_metrics(wall_seconds, peak_rss_kib):
    wall = parse_float_hex(wall_seconds, "wall seconds")
    if (wall <= 0 or isinstance(peak_rss_kib, bool) or
            not isinstance(peak_rss_kib, int) or peak_rss_kib <= 0):
        raise ValueError("run resource metrics are invalid")
    return wall, peak_rss_kib


def encode_random_state(state):
    if isinstance(state, tuple):
        return [encode_random_state(value) for value in state]
    if state is None or isinstance(state, int):
        return state
    if isinstance(state, float):
        return {"float_hex": float_hex(state)}
    raise TypeError("unexpected PRNG-state scalar")


def decode_random_state(state):
    if isinstance(state, list):
        return tuple(decode_random_state(value) for value in state)
    if state is None or isinstance(state, int) and not isinstance(state, bool):
        return state
    if isinstance(state, dict) and set(state) == {"float_hex"}:
        return parse_float_hex(state["float_hex"], "PRNG float")
    raise ValueError("malformed serialized PRNG state")


def expected_chain_table():
    chains = []
    base = 2_364_800_000
    for target_index, target in enumerate(("I", "J")):
        for stratum in STRATA:
            for replicate in range(4):
                offset = target_index * 1_000_000 + stratum * 1000 + \
                    replicate * 2
                chains.append({
                    "target": target,
                    "stratum": stratum,
                    "replicate": replicate,
                    "initial_seed": base + offset,
                    "transition_seed": base + offset + 1,
                })
    return chains


def expected_schedule():
    return {
        "targets": ["I", "J"],
        "strata": list(STRATA),
        "replicates_per_target_stratum": 4,
        "chains_total": 128,
        "chains": expected_chain_table(),
        "slack_move_probability": "1/2",
        "tempering_powers": ["0", "1/4", "1/2", "3/4", "1"],
        "steps_per_tempering_power": 250,
        "power_one_burn_in_steps": 1000,
        "retained_samples": 4000,
        "proposal_steps_per_sample": 2,
        "batches_per_chain": 20,
        "samples_per_batch": 200,
        "extension_samples_per_chain": 12000,
        "extension_total_samples_per_chain": 16000,
        "extension_total_batches_per_chain": 80,
    }


def validate_schedule(schedule, *, production=True):
    """Reject booleans, nonintegral counts, and internally inconsistent grids."""
    expected = expected_schedule() if production else tiny_smoke_schedule()
    if schedule != expected:
        raise ValueError("schedule differs from its frozen mode")
    integer_fields = (
        "replicates_per_target_stratum", "chains_total",
        "steps_per_tempering_power", "power_one_burn_in_steps",
        "retained_samples", "proposal_steps_per_sample",
        "batches_per_chain", "samples_per_batch",
        "extension_samples_per_chain", "extension_total_samples_per_chain",
        "extension_total_batches_per_chain",
    )
    for key in integer_fields:
        value = schedule[key]
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"schedule field {key} must be a positive integer")
    if schedule["retained_samples"] != (
            schedule["batches_per_chain"] * schedule["samples_per_batch"]):
        raise ValueError("retained samples do not equal batch product")
    if production:
        if schedule["chains_total"] != len(expected_chain_table()):
            raise ValueError("chain count is inconsistent")
        if schedule["extension_total_samples_per_chain"] != (
                schedule["retained_samples"] +
                schedule["extension_samples_per_chain"]):
            raise ValueError("extension sample counts are inconsistent")
        if schedule["extension_total_samples_per_chain"] != (
                schedule["extension_total_batches_per_chain"] *
                schedule["samples_per_batch"]):
            raise ValueError("extension batch counts are inconsistent")
    return True


def expected_thresholds():
    return {
        "simultaneous_multiplier": "6",
        "maximum_split_rhat": "1.05",
        "minimum_batch_means_ess": "200",
        "minimum_move_acceptance_per_chain": "positive",
        "minimum_aggregate_acceptance_by_move": "1/100",
        "minimum_z_six_se_lower": "0",
        "maximum_z_relative_se": "1/50",
        "root_relative_discrepancy": "1/200",
        "root_jackknife_multiplier": "6",
        "extension_max_standardized_discrepancy": "12",
        "relative_rank_tolerance": "1/1000000000000",
    }


def exact_c10_common_branch_presence():
    """Prove branch presence from one exact interior witness per common R."""
    alpha = Fraction(79247, 300000)
    eta = Fraction(76247, 300000)
    delta = Fraction(1, 100)

    def beta(r):
        return Fraction(3, 20) if r in (1, 2) else Fraction(97, 625)

    answer = []
    for r in STRATA:
        if r == 0:
            large_sum = Fraction(0)
        else:
            reserve = min(beta(r) - r * delta, eta - r * delta)
            if reserve <= 0:
                raise AssertionError("C10 common stratum has no exact witness")
            large_sum = r * delta + reserve / 4
        common_total = large_sum  # remaining common coordinates are zero
        small_upper = min(delta, eta - common_total)
        small_present = ((r == 0 or large_sum <= beta(r)) and
                         small_upper > 0)
        large_upper = min(eta - common_total, beta(r + 1) - large_sum)
        large_present = large_upper > delta
        answer.append({"stratum": r, "small": small_present,
                       "large": large_present,
                       "witness_large_sum": str(large_sum),
                       "small_upper": str(small_upper),
                       "large_upper": str(large_upper)})
    if ([row["small"] for row in answer] != [True] * 16 or
            [row["large"] for row in answer] != [True] * 15 + [False]):
        raise AssertionError("unexpected C10 common-branch pattern")
    if not (16 * delta > beta(16) and 15 * delta < beta(15) and
            eta < alpha):
        raise AssertionError("C10 endpoint inequalities changed")
    return answer


def expected_conventions():
    return {
        "k": 48,
        "support_parameters": {
            "alpha": "79247/300000", "delta": "1/100",
            "eta": "76247/300000", "beta1": "3/20",
            "beta2": "3/20", "beta3plus": "97/625"},
        "strata": list(STRATA),
        "channels_per_stratum": CHANNEL_COUNT,
        "basis_dimension": DIMENSION,
        "feature_normalization": "(L/alpha)^a*(Z/alpha)^b",
        "channel_powers": [[0, 0], [1, 0], [0, 1],
                           [2, 0], [1, 1], [0, 2]],
        "j_envelope": "g=sum_i(m_i^2); y_ij=m_i*m_j/g; z=m0^2/g",
        "j_stratum_artifact_scale_to_48J_numerator": 1,
        "structural_upper_counts": {"I": 336, "J": 876},
        "active_dimensions": {"degree_0": 16, "degree_1": 47,
                              "degree_2": 93},
        "j_common_branch_presence": exact_c10_common_branch_presence(),
    }


def _exact_keys(value, keys, name):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValueError(f"{name} has an unexpected schema")


def load_and_validate_gate(path):
    snapshot = read_file_snapshot(path)
    path = Path(snapshot["path"])
    data = snapshot["data"]
    digest = snapshot["sha256"]
    gate = strict_json_bytes(data, "D4 calibration gate")
    _exact_keys(gate, {
        "status", "rigorous", "production_launch_authorized",
        "supersedes_invalid_gate_sha256s",
        "float_encoding", "source_hashes", "data_hashes", "schedule",
        "thresholds", "conventions", "extension_rule"},
                "D4 calibration gate")
    if (gate["status"] != "frozen-d4-stratified-calibration-prelaunch-v5" or
            gate["rigorous"] is not False or
            gate["production_launch_authorized"] is not False or
            gate["supersedes_invalid_gate_sha256s"] != [
                "fcce4e339c9b7d23eb39bf74fe88f82592ea101fd0be1fea3c9691f760ed237c",
                "0d52e2d0c730f01d459c20a3091f312edfec3ea86a253775b452de26fa5dcb03",
                "2e2417e30ded2520a16a5778cb9d56833b17524fe92b51add5418bf1ae27e282",
                "a2ca98514d0aa31463aaeca2d46baec400e8d4d54f9fc54e068b8684d235f8f6",
            ] or
            gate["float_encoding"] != FLOAT_ENCODING):
        raise ValueError("D4 calibration gate status flags are invalid")
    if gate["schedule"] != expected_schedule():
        raise ValueError("calibration schedule differs from frozen specification")
    validate_schedule(gate["schedule"], production=True)
    if gate["thresholds"] != expected_thresholds():
        raise ValueError("calibration thresholds differ from frozen specification")
    if gate["conventions"] != expected_conventions():
        raise ValueError("calibration conventions differ from frozen specification")
    expected_extension = {
        "allowed_failure_classes": [
            "split_rhat", "batch_means_ess", "z_precision",
            "simultaneous_coverage"],
        "forbidden_after_any_algebraic_failure": True,
        "requires_max_standardized_discrepancy_at_most": "12",
        "continues_serialized_prng_states": True,
        "post_extension_samples_per_chain": 16000,
        "post_extension_batches_per_chain": 80,
    }
    if gate["extension_rule"] != expected_extension:
        raise ValueError("extension rule differs from frozen specification")

    for field, expected_paths in (
            ("source_hashes", REQUIRED_SOURCE_PATHS),
            ("data_hashes", REQUIRED_DATA_PATHS)):
        table = gate[field]
        if not isinstance(table, dict) or set(table) != set(expected_paths):
            raise ValueError(f"{field} has missing or extra paths")
        for relative, wanted in table.items():
            if (not isinstance(wanted, str) or len(wanted) != 64 or
                    any(c not in "0123456789abcdef" for c in wanted)):
                raise ValueError(f"malformed SHA-256 for {relative}")
            resolved = (REPO_ROOT / relative).resolve()
            try:
                resolved.relative_to(REPO_ROOT.resolve())
            except ValueError as error:
                raise ValueError("gate path escapes repository") from error
            if sha256_file(resolved) != wanted:
                raise ValueError(f"gate hash mismatch for {relative}")
    return {**public_binding(snapshot), "gate": gate}


def validate_authorization(path, gate_sha256, driver_sha256, record_dir):
    snapshot = read_file_snapshot(path)
    data = snapshot["data"]
    raw = strict_json_bytes(data, "production authorization")
    _exact_keys(raw, {"status", "authorized", "gate_sha256",
                      "driver_sha256", "mode", "record_directory_binding"},
                "production authorization")
    if (raw["status"] != "root-authorized-d4-calibration" or
            raw["authorized"] is not True or raw["mode"] != "production" or
            raw["gate_sha256"] != gate_sha256 or
            raw["driver_sha256"] != driver_sha256):
        raise ValueError("production authorization does not bind this run")
    validate_directory_binding(
        raw["record_directory_binding"], record_dir,
        name="authorized production record directory")
    return {"raw": raw, **public_binding(snapshot)}


def validate_extension_authorization(path, gate_sha256, driver_sha256,
                                     parent_result_sha256,
                                     extension_record_dir):
    snapshot = read_file_snapshot(path)
    data = snapshot["data"]
    raw = strict_json_bytes(data, "extension authorization")
    _exact_keys(raw, {"status", "authorized", "gate_sha256",
                      "driver_sha256", "mode", "parent_result_sha256",
                      "extension_record_directory_binding"},
                "extension authorization")
    if (raw["status"] != "root-authorized-d4-calibration-extension" or
            raw["authorized"] is not True or raw["mode"] != "extension" or
            raw["gate_sha256"] != gate_sha256 or
            raw["driver_sha256"] != driver_sha256 or
            raw["parent_result_sha256"] != parent_result_sha256):
        raise ValueError("extension authorization does not bind this run")
    validate_directory_binding(
        raw["extension_record_directory_binding"], extension_record_dir,
        name="authorized extension record directory")
    return {"raw": raw, **public_binding(snapshot)}


def upper_pairs(dimension):
    return tuple((i, j) for i in range(dimension)
                 for j in range(i, dimension))


def local_indices(target, stratum):
    if target == "I":
        return tuple(range(CHANNEL_COUNT * stratum,
                           CHANNEL_COUNT * (stratum + 1)))
    if target == "J":
        answer = list(range(CHANNEL_COUNT * stratum,
                            CHANNEL_COUNT * (stratum + 1)))
        if stratum + 1 < len(STRATA):
            answer.extend(range(CHANNEL_COUNT * (stratum + 1),
                                CHANNEL_COUNT * (stratum + 2)))
        return tuple(answer)
    raise ValueError("target must be I or J")


def structural_masks():
    i_mask = np.zeros((DIMENSION, DIMENSION), dtype=bool)
    j_mask = np.zeros((DIMENSION, DIMENSION), dtype=bool)
    for r in STRATA:
        block = range(CHANNEL_COUNT * r, CHANNEL_COUNT * (r + 1))
        for i in block:
            for j in range(i, CHANNEL_COUNT * (r + 1)):
                i_mask[i, j] = True
                j_mask[i, j] = True
        if r + 1 < len(STRATA):
            next_block = range(CHANNEL_COUNT * (r + 1),
                               CHANNEL_COUNT * (r + 2))
            for i in block:
                for j in next_block:
                    j_mask[i, j] = True
    if int(i_mask.sum()) != 336 or int(j_mask.sum()) != 876:
        raise AssertionError("internal structural-count error")
    return i_mask, j_mask


def _new_acceptance():
    return {
        stage: {move: {key: 0 for key in (
            "attempted", "accepted", "support_rejected")}
                for move in ("physical-physical", "physical-slack")}
        for stage in ("tempering", "burn_in", "retained")
    }


def _record_step(acceptance, stage, step):
    counts = acceptance[stage][step.move_type]
    counts["attempted"] += 1
    counts["accepted"] += int(step.result.accepted)
    counts["support_rejected"] += int(step.result.support_rejected)


def _advance(adapter, target, stratum, state, rng, steps, power,
             acceptance, stage, slack_probability):
    for _ in range(steps):
        step = conditional_metropolis_step(
            adapter, target, stratum, state, rng,
            density_power=power, slack_probability=slack_probability)
        state = step.result.state
        _record_step(acceptance, stage, step)
        if point_stratum(adapter, state) != stratum:
            raise ArithmeticError("chain escaped its fixed stratum")
    return state


def _observation(adapter, target, stratum, state):
    indices = local_indices(target, stratum)
    if point_stratum(adapter, state) != stratum:
        raise ArithmeticError("observation state escaped its named stratum")
    if target == "I":
        full = adapter.i_features(state)
        if len(full) != DIMENSION or any(
                value != 0 for index, value in enumerate(full)
                if index not in indices):
            raise ArithmeticError("I feature leaked outside its fixed stratum")
        local = np.asarray([full[index] for index in indices], dtype=float)
        z = None
    else:
        envelope = j_envelope_point(adapter, state)
        if envelope is None:
            raise ArithmeticError("retained J state has zero envelope density")
        if len(envelope.unit_marginals) != DIMENSION or any(
                value != 0 for index, value in
                enumerate(envelope.unit_marginals) if index not in indices):
            raise ArithmeticError(
                "J marginal leaked outside its common-stratum blocks")
        local = np.asarray(
            [envelope.unit_marginals[index] for index in indices], dtype=float)
        z = float(envelope.z)
    if not np.all(np.isfinite(local)):
        raise ArithmeticError("retained feature is nonfinite")
    outer = local[:, None] * local[None, :]
    if not np.array_equal(outer, outer.T):
        raise ArithmeticError("single-sample outer product is asymmetric")
    if target == "J":
        tolerance = 16 * np.finfo(float).eps
        for i, j in upper_pairs(len(indices)):
            bounded_outer_entry(envelope, indices[i], indices[j])
            bound = 1.0 if i == j else 0.5
            if abs(outer[i, j]) > bound + tolerance:
                raise ArithmeticError("J envelope observation exceeds bound")
        if not 0 <= z <= 2 + 64 * np.finfo(float).eps:
            raise ArithmeticError("J envelope z is outside [0,2]")
    return outer, z


def _record_identity(chain):
    return (chain["target"], chain["stratum"], chain["replicate"])


def run_one_chain(adapter, chain_spec, schedule, *, progress=False):
    """Run one frozen chain and return only sufficient statistics/batches."""
    _exact_keys(chain_spec, {"target", "stratum", "replicate",
                             "initial_seed", "transition_seed"}, "chain spec")
    target = chain_spec["target"]
    stratum = chain_spec["stratum"]
    initial = randomized_interior_start(
        adapter, target, stratum, chain_spec["initial_seed"])
    state = initial
    rng = random.Random(chain_spec["transition_seed"])
    acceptance = _new_acceptance()
    slack_probability = float(Fraction(schedule["slack_move_probability"]))
    powers = [float(Fraction(value)) for value in schedule["tempering_powers"]]
    for power in powers:
        state = _advance(
            adapter, target, stratum, state, rng,
            schedule["steps_per_tempering_power"], power,
            acceptance, "tempering", slack_probability)
    state = _advance(
        adapter, target, stratum, state, rng,
        schedule["power_one_burn_in_steps"], 1.0,
        acceptance, "burn_in", slack_probability)

    indices = local_indices(target, stratum)
    pairs = upper_pairs(len(indices))
    batches = []
    second_batches = []
    z_batches = []
    z_second_batches = []
    raw_sum = np.zeros(len(pairs) + (1 if target == "J" else 0))
    raw_second = np.zeros_like(raw_sum)
    raw_antisymmetry = 0.0
    for batch in range(schedule["batches_per_chain"]):
        batch_sum = np.zeros(len(pairs))
        batch_second_sum = np.zeros(len(pairs))
        z_sum = 0.0
        z_second_sum = 0.0
        for _ in range(schedule["samples_per_batch"]):
            state = _advance(
                adapter, target, stratum, state, rng,
                schedule["proposal_steps_per_sample"], 1.0,
                acceptance, "retained", slack_probability)
            outer, z = _observation(adapter, target, stratum, state)
            raw_antisymmetry = max(
                raw_antisymmetry,
                float(np.max(np.abs(outer - outer.T), initial=0.0)))
            vector = np.asarray([outer[i, j] for i, j in pairs])
            batch_sum += vector
            batch_second_sum += vector * vector
            raw_sum[:len(pairs)] += vector
            raw_second[:len(pairs)] += vector * vector
            if target == "J":
                z_sum += z
                z_second_sum += z * z
                raw_sum[-1] += z
                raw_second[-1] += z * z
        batches.append(batch_sum / schedule["samples_per_batch"])
        second_batches.append(
            batch_second_sum / schedule["samples_per_batch"])
        if target == "J":
            z_batches.append(z_sum / schedule["samples_per_batch"])
            z_second_batches.append(
                z_second_sum / schedule["samples_per_batch"])
        if progress:
            print(f"{target} r={stratum} rep={chain_spec['replicate']} "
                  f"batch={batch + 1}/{schedule['batches_per_chain']}",
                  flush=True)
    sample_count = (schedule["batches_per_chain"] *
                    schedule["samples_per_batch"])
    if sample_count != schedule["retained_samples"]:
        raise AssertionError("retained sample schedule mismatch")
    if raw_antisymmetry != 0:
        raise ArithmeticError("outer-product antisymmetry is not bitwise zero")
    return {
        **chain_spec,
        "local_indices": list(indices),
        "upper_pairs": [list(pair) for pair in pairs],
        "initial_state": [float_hex(x) for x in initial],
        "final_state": [float_hex(x) for x in state],
        "prng_state": encode_random_state(rng.getstate()),
        "sample_count": sample_count,
        "batch_count": schedule["batches_per_chain"],
        "samples_per_batch": schedule["samples_per_batch"],
        "batch_upper_means": [[float_hex(x) for x in row] for row in batches],
        "batch_upper_second_means": [
            [float_hex(x) for x in row] for row in second_batches],
        "batch_z_means": [float_hex(x) for x in z_batches],
        "batch_z_second_means": [float_hex(x) for x in z_second_batches],
        "raw_sum": [float_hex(x) for x in raw_sum],
        "raw_second_sum": [float_hex(x) for x in raw_second],
        "raw_antisymmetry": float_hex(raw_antisymmetry),
        "acceptance": acceptance,
    }


def extended_schedule(schedule):
    required = {
        "retained_samples", "batches_per_chain", "samples_per_batch",
        "extension_samples_per_chain", "extension_total_samples_per_chain",
        "extension_total_batches_per_chain"}
    if not isinstance(schedule, dict) or not required <= set(schedule):
        raise ValueError("extension schedule is incomplete")
    if schedule["extension_total_samples_per_chain"] != (
            schedule["retained_samples"] +
            schedule["extension_samples_per_chain"]):
        raise ValueError("extension sample arithmetic is inconsistent")
    if schedule["extension_total_samples_per_chain"] != (
            schedule["extension_total_batches_per_chain"] *
            schedule["samples_per_batch"]):
        raise ValueError("extension batch arithmetic is inconsistent")
    answer = dict(schedule)
    answer["retained_samples"] = schedule[
        "extension_total_samples_per_chain"]
    answer["batches_per_chain"] = schedule[
        "extension_total_batches_per_chain"]
    return answer


def extend_one_chain(adapter, record, chain_spec, schedule, *, progress=False):
    """Append the single predeclared 12,000-sample continuation."""
    validate_chain_record(record, chain_spec, schedule, adapter=adapter)
    combined_schedule = extended_schedule(schedule)
    extra_batches = (combined_schedule["batches_per_chain"] -
                     record["batch_count"])
    if extra_batches <= 0 or extra_batches * schedule[
            "samples_per_batch"] != schedule["extension_samples_per_chain"]:
        raise AssertionError("frozen extension batch arithmetic changed")
    state = tuple(parse_float_hex(x, "continuation state")
                  for x in record["final_state"])
    rng = random.Random()
    rng.setstate(decode_random_state(record["prng_state"]))
    acceptance = json.loads(json.dumps(record["acceptance"]))
    indices = local_indices(record["target"], record["stratum"])
    pairs = upper_pairs(len(indices))
    batches = [list(row) for row in record["batch_upper_means"]]
    second_batches = [list(row)
                      for row in record["batch_upper_second_means"]]
    z_batches = list(record["batch_z_means"])
    z_second_batches = list(record["batch_z_second_means"])
    raw_sum = np.asarray([parse_float_hex(x, "raw sum")
                          for x in record["raw_sum"]])
    raw_second = np.asarray([parse_float_hex(x, "raw second sum")
                             for x in record["raw_second_sum"]])
    slack_probability = float(Fraction(schedule["slack_move_probability"]))
    for extra_batch in range(extra_batches):
        batch_sum = np.zeros(len(pairs))
        batch_second_sum = np.zeros(len(pairs))
        z_sum = 0.0
        z_second_sum = 0.0
        for _ in range(schedule["samples_per_batch"]):
            state = _advance(
                adapter, record["target"], record["stratum"], state, rng,
                schedule["proposal_steps_per_sample"], 1.0,
                acceptance, "retained", slack_probability)
            outer, z = _observation(
                adapter, record["target"], record["stratum"], state)
            vector = np.asarray([outer[i, j] for i, j in pairs])
            batch_sum += vector
            batch_second_sum += vector * vector
            raw_sum[:len(pairs)] += vector
            raw_second[:len(pairs)] += vector * vector
            if record["target"] == "J":
                z_sum += z
                z_second_sum += z * z
                raw_sum[-1] += z
                raw_second[-1] += z * z
        batches.append([float_hex(x) for x in (
            batch_sum / schedule["samples_per_batch"])])
        second_batches.append([float_hex(x) for x in (
            batch_second_sum / schedule["samples_per_batch"])])
        if record["target"] == "J":
            z_batches.append(float_hex(
                z_sum / schedule["samples_per_batch"]))
            z_second_batches.append(float_hex(
                z_second_sum / schedule["samples_per_batch"]))
        if progress:
            print(f"extend {record['target']} r={record['stratum']} "
                  f"rep={record['replicate']} batch="
                  f"{record['batch_count'] + extra_batch + 1}/"
                  f"{combined_schedule['batches_per_chain']}", flush=True)
    extended = {
        **{key: record[key] for key in (
            "target", "stratum", "replicate", "initial_seed",
            "transition_seed", "local_indices", "upper_pairs",
            "initial_state", "raw_antisymmetry")},
        "final_state": [float_hex(x) for x in state],
        "prng_state": encode_random_state(rng.getstate()),
        "sample_count": combined_schedule["retained_samples"],
        "batch_count": combined_schedule["batches_per_chain"],
        "samples_per_batch": combined_schedule["samples_per_batch"],
        "batch_upper_means": batches,
        "batch_upper_second_means": second_batches,
        "batch_z_means": z_batches,
        "batch_z_second_means": z_second_batches,
        "raw_sum": [float_hex(x) for x in raw_sum],
        "raw_second_sum": [float_hex(x) for x in raw_second],
        "acceptance": acceptance,
    }
    validate_chain_record(
        extended, chain_spec, combined_schedule, adapter=adapter)
    return extended


def _same_floats(left, right):
    return len(left) == len(right) and all(
        float(a).hex() == float(b).hex() for a, b in zip(left, right))


def validate_chain_record(record, chain_spec, schedule, *, adapter=None):
    required = {
        "target", "stratum", "replicate", "initial_seed", "transition_seed",
        "local_indices", "upper_pairs", "initial_state", "final_state",
        "prng_state", "sample_count", "batch_count", "samples_per_batch",
        "batch_upper_means", "batch_upper_second_means",
        "batch_z_means", "batch_z_second_means", "raw_sum",
        "raw_second_sum", "raw_antisymmetry", "acceptance"}
    _exact_keys(record, required, "chain record")
    for key in ("target", "stratum", "replicate", "initial_seed",
                "transition_seed"):
        if record[key] != chain_spec[key]:
            raise ValueError("chain identity/seed mismatch")
    target, stratum = record["target"], record["stratum"]
    indices = local_indices(target, stratum)
    pairs = upper_pairs(len(indices))
    if record["local_indices"] != list(indices) or \
            record["upper_pairs"] != [list(pair) for pair in pairs]:
        raise ValueError("chain local-coordinate map mismatch")
    expected_samples = (schedule["batches_per_chain"] *
                        schedule["samples_per_batch"])
    if (record["sample_count"] != expected_samples or
            record["batch_count"] != schedule["batches_per_chain"] or
            record["samples_per_batch"] != schedule["samples_per_batch"]):
        raise ValueError("chain sample/batch schedule mismatch")
    dimension = 48 if target == "I" else 47
    if len(record["initial_state"]) != dimension or \
            len(record["final_state"]) != dimension:
        raise ValueError("chain state dimension mismatch")
    for value in record["initial_state"] + record["final_state"]:
        parse_float_hex(value, "chain coordinate")
    initial_state = tuple(parse_float_hex(x, "initial coordinate")
                          for x in record["initial_state"])
    final_state = tuple(parse_float_hex(x, "final coordinate")
                        for x in record["final_state"])
    if adapter is not None:
        deterministic_initial = randomized_interior_start(
            adapter, target, stratum, chain_spec["initial_seed"])
        if not _same_floats(initial_state, deterministic_initial):
            raise ValueError("serialized initial state is not seed-determined")
        support = adapter.i_support if target == "I" else adapter.j_support
        for name, state_value in (("initial", initial_state),
                                  ("final", final_state)):
            if target == "I":
                density_value = adapter.i_log_density(state_value)
            else:
                envelope_value = j_envelope_point(adapter, state_value)
                density_value = (-math.inf if envelope_value is None else
                                 envelope_value.log_g)
            if (not support(state_value) or
                    point_stratum(adapter, state_value) != stratum or
                    not math.isfinite(float(density_value))):
                raise ArithmeticError(
                    f"serialized {name} state is outside positive target")
    rng = random.Random()
    rng.setstate(decode_random_state(record["prng_state"]))
    batch_width = len(pairs)
    if (not isinstance(record["batch_upper_means"], list) or
            len(record["batch_upper_means"]) != record["batch_count"] or
            any(not isinstance(row, list) or len(row) != batch_width
                for row in record["batch_upper_means"])):
        raise ValueError("chain upper-batch shape mismatch")
    parsed_upper = []
    for row in record["batch_upper_means"]:
        parsed_row = [parse_float_hex(value, "batch mean") for value in row]
        parsed_upper.append(parsed_row)
    if (not isinstance(record["batch_upper_second_means"], list) or
            len(record["batch_upper_second_means"]) !=
            record["batch_count"] or
            any(not isinstance(row, list) or len(row) != batch_width
                for row in record["batch_upper_second_means"])):
        raise ValueError("chain upper-second-batch shape mismatch")
    parsed_upper_second = [
        [parse_float_hex(value, "batch second mean") for value in row]
        for row in record["batch_upper_second_means"]]
    expected_z = record["batch_count"] if target == "J" else 0
    if (not isinstance(record["batch_z_means"], list) or
            len(record["batch_z_means"]) != expected_z or
            not isinstance(record["batch_z_second_means"], list) or
            len(record["batch_z_second_means"]) != expected_z):
        raise ValueError("chain z-batch shape mismatch")
    parsed_z = []
    for value in record["batch_z_means"]:
        z = parse_float_hex(value, "z batch")
        if not 0 <= z <= 2 + 64 * np.finfo(float).eps:
            raise ArithmeticError("serialized z batch is outside [0,2]")
        parsed_z.append(z)
    parsed_z_second = []
    for value in record["batch_z_second_means"]:
        z_second = parse_float_hex(value, "z second batch")
        if not 0 <= z_second <= 4 + 256 * np.finfo(float).eps:
            raise ArithmeticError(
                "serialized z second batch is outside [0,4]")
        parsed_z_second.append(z_second)
    expected_raw = batch_width + (1 if target == "J" else 0)
    if len(record["raw_sum"]) != expected_raw or \
            len(record["raw_second_sum"]) != expected_raw:
        raise ValueError("chain raw-moment shape mismatch")
    raw_sum = np.asarray([parse_float_hex(value, "raw sum")
                          for value in record["raw_sum"]])
    raw_second = np.asarray([parse_float_hex(value, "raw second moment")
                             for value in record["raw_second_sum"]])
    if np.any(raw_second < 0):
        raise ArithmeticError("serialized raw second moment is negative")
    batch_vectors = np.asarray(parsed_upper, dtype=float)
    batch_second_vectors = np.asarray(parsed_upper_second, dtype=float)
    if target == "J":
        batch_vectors = np.concatenate(
            (batch_vectors, np.asarray(parsed_z)[:, None]), axis=1)
        batch_second_vectors = np.concatenate(
            (batch_second_vectors,
             np.asarray(parsed_z_second)[:, None]), axis=1)
    if batch_second_vectors.shape != batch_vectors.shape or np.any(
            batch_second_vectors < 0):
        raise ArithmeticError("serialized batch second moment is invalid")
    raw_mean = raw_sum / expected_samples
    batch_mean = np.mean(batch_vectors, axis=0)
    if not np.allclose(raw_mean, batch_mean, rtol=128 * np.finfo(float).eps,
                       atol=128 * np.finfo(float).eps):
        raise ArithmeticError("raw sums disagree with serialized batch means")
    raw_second_mean = raw_second / expected_samples
    tolerance = 256 * np.finfo(float).eps * np.maximum(
        1.0, np.maximum(np.abs(raw_second_mean), raw_mean * raw_mean))
    serialized_second_mean = np.mean(batch_second_vectors, axis=0)
    if not np.allclose(
            raw_second_mean, serialized_second_mean,
            rtol=256 * np.finfo(float).eps,
            atol=256 * np.finfo(float).eps):
        raise ArithmeticError(
            "raw second sums disagree with serialized batch second means")
    if np.any(raw_second_mean < raw_mean * raw_mean - tolerance):
        raise ArithmeticError("raw second moments violate Jensen")
    batch_square_mean = np.mean(batch_vectors * batch_vectors, axis=0)
    if np.any(raw_second_mean < batch_square_mean - tolerance):
        raise ArithmeticError("raw moments violate batch-level Jensen")
    if target == "I":
        if np.any(batch_vectors < 0) or np.any(batch_vectors > 1):
            raise ArithmeticError("I batch moment is outside [0,1]")
        second_bounds = np.ones_like(raw_second_mean)
    else:
        local_dimension = len(indices)
        local_batches = _upper_to_matrix(
            np.asarray(parsed_upper), local_dimension)
        diagonal = np.diagonal(local_batches, axis1=-2, axis2=-1)
        off_diagonal = local_batches.copy()
        diagonal_indices = np.arange(local_dimension)
        off_diagonal[..., diagonal_indices, diagonal_indices] = 0
        envelope_tolerance = 64 * np.finfo(float).eps
        if (np.any(diagonal < 0) or
                np.any(diagonal > 1 + envelope_tolerance) or
                np.any(np.abs(off_diagonal) > 0.5 + envelope_tolerance)):
            raise ArithmeticError("J batch moment violates envelope bounds")
        second_bounds = np.asarray([
            1.0 if i == j else 0.25
            for i, j in upper_pairs(local_dimension)] + [4.0])
    second_tolerance = 256 * np.finfo(float).eps * np.maximum(
        1.0, second_bounds)
    if np.any(batch_second_vectors > second_bounds + second_tolerance):
        raise ArithmeticError(
            "serialized batch second moment exceeds pointwise bound")
    batch_jensen_tolerance = 256 * np.finfo(float).eps * np.maximum(
        1.0, np.maximum(batch_second_vectors, batch_vectors * batch_vectors))
    if np.any(batch_second_vectors <
              batch_vectors * batch_vectors - batch_jensen_tolerance):
        raise ArithmeticError("batch second moments violate Jensen")
    if np.any(raw_second_mean > second_bounds +
              second_tolerance):
        raise ArithmeticError("raw second moment exceeds pointwise bound")
    if parse_float_hex(record["raw_antisymmetry"], "raw antisymmetry") != 0:
        raise ArithmeticError("serialized outer product was asymmetric")
    expected_acceptance_keys = {"tempering", "burn_in", "retained"}
    if not isinstance(record["acceptance"], dict) or \
            set(record["acceptance"]) != expected_acceptance_keys:
        raise ValueError("acceptance-stage schema mismatch")
    for stage in expected_acceptance_keys:
        moves = record["acceptance"][stage]
        if not isinstance(moves, dict) or set(moves) != {
                "physical-physical", "physical-slack"}:
            raise ValueError("acceptance move schema mismatch")
        for counts in moves.values():
            if not isinstance(counts, dict) or set(counts) != {
                    "attempted", "accepted", "support_rejected"}:
                raise ValueError("acceptance count schema mismatch")
            if any(isinstance(value, bool) or not isinstance(value, int) or
                   value < 0 for value in counts.values()):
                raise ValueError("acceptance count is not nonnegative integer")
            if (counts["accepted"] > counts["attempted"] or
                    counts["support_rejected"] > counts["attempted"] or
                    counts["accepted"] + counts["support_rejected"] >
                    counts["attempted"]):
                raise ValueError("acceptance counts are inconsistent")
    expected_stage_attempts = {
        "tempering": (len(schedule["tempering_powers"]) *
                       schedule["steps_per_tempering_power"]),
        "burn_in": schedule["power_one_burn_in_steps"],
        "retained": (schedule["retained_samples"] *
                     schedule["proposal_steps_per_sample"]),
    }
    for stage, expected_attempts in expected_stage_attempts.items():
        observed = sum(item["attempted"]
                       for item in record["acceptance"][stage].values())
        if observed != expected_attempts:
            raise ValueError(f"{stage} attempt count differs from schedule")
    return True


def _record_arrays(record):
    upper = np.asarray([[parse_float_hex(x) for x in row]
                        for row in record["batch_upper_means"]])
    z = np.asarray([parse_float_hex(x) for x in record["batch_z_means"]])
    raw_sum = np.asarray([parse_float_hex(x) for x in record["raw_sum"]])
    raw_second = np.asarray(
        [parse_float_hex(x) for x in record["raw_second_sum"]])
    return upper, z, raw_sum, raw_second


def _upper_to_matrix(values, dimension):
    values = np.asarray(values, dtype=float)
    pairs = upper_pairs(dimension)
    if values.shape[-1] != len(pairs):
        raise ValueError("upper-vector dimension mismatch")
    answer = np.zeros(values.shape[:-1] + (dimension, dimension))
    for column, (i, j) in enumerate(pairs):
        answer[..., i, j] = values[..., column]
        answer[..., j, i] = values[..., column]
    return answer


def _group_records(records):
    groups = {(target, r): [] for target in ("I", "J") for r in STRATA}
    for record in records:
        key = (record["target"], record["stratum"])
        if key not in groups:
            raise ValueError("record outside expected target/stratum")
        groups[key].append(record)
    for key, group in groups.items():
        group.sort(key=lambda record: record["replicate"])
        if [record["replicate"] for record in group] != list(range(4)):
            raise ValueError(f"missing/duplicate chain in group {key}")
    return groups


def _matrix_add_local(target, matrix, local, indices, weight=1.0):
    if local.shape != (len(indices), len(indices)):
        raise ValueError("local matrix shape mismatch")
    for i, global_i in enumerate(indices):
        for j, global_j in enumerate(indices):
            matrix[global_i, global_j] += weight * local[i, j]


def analytic_local_zero_se_entries(target, stratum):
    """Only pointwise-proved deterministic conditional matrix entries.

    I's tagged constant is identically one within every fixed stratum.  At
    common J stratum 15 the large distinguished branch would create 16 large
    coordinates, but ``16*delta > beta(16)`` at C10.  Consequently only the
    tagged stratum-15 constant contributes to m0 and ``y_00 == z`` pointwise,
    so its local ratio is identically one.  This is deliberately a *local*
    whitelist: global J(90,90) also receives the independently sampled
    common-r=14 contribution and is never exempted below.
    """
    if target == "I" and stratum in STRATA:
        return frozenset({(0, 0)})
    if target == "J" and stratum == 15:
        return frozenset({(0, 0)})
    if target in ("I", "J") and stratum in STRATA:
        return frozenset()
    raise ValueError("zero-SE whitelist target/stratum is invalid")


def exact_local_active_pairs(target, stratum):
    """Pointwise-active local products, fixed by the exact witness audit."""
    if target not in ("I", "J") or stratum not in STRATA:
        raise ValueError("local active mask target/stratum is invalid")
    if target == "I":
        active_channels = (0, 2, 5) if stratum == 0 else tuple(range(6))
    elif stratum == 0:
        active_channels = (0, 2, 5, 6, 7, 8, 9, 10, 11)
    elif stratum == 15:
        active_channels = tuple(range(6))
    else:
        active_channels = tuple(range(12))
    return frozenset((i, j) for position, i in enumerate(active_channels)
                     for j in active_channels[position:])


def diagnostic_moment_indices(target, stratum):
    dimension = len(local_indices(target, stratum))
    pairs = upper_pairs(dimension)
    active = exact_local_active_pairs(target, stratum)
    analytic = analytic_local_zero_se_entries(target, stratum)
    answer = [position for position, pair in enumerate(pairs)
              if pair in active and pair not in analytic]
    if target == "J":
        answer.append(len(pairs))  # bounded envelope denominator z
    return tuple(answer)


def validate_analytic_zero_se_proofs(oracle):
    expected_parameters = {
        key: Fraction(value) for key, value in
        expected_conventions()["support_parameters"].items()}
    if oracle["parameters"] != expected_parameters:
        raise ValueError("zero-SE proof is not bound to the C10 parameters")
    branch_rows = exact_c10_common_branch_presence()
    absent = [(row["stratum"], name) for row in branch_rows
              for name in ("small", "large") if not row[name]]
    if absent != [(15, "large")]:
        raise ArithmeticError("analytic J whitelist branch proof changed")
    for r in STRATA:
        index = CHANNEL_COUNT * r
        if oracle["E_I"][index][index] <= 0:
            raise ArithmeticError("whitelisted I constant has zero oracle mass")
    final_constant = CHANNEL_COUNT * 15
    if oracle["E_J"][final_constant][final_constant] <= 0:
        raise ArithmeticError("whitelisted J constant has zero oracle mass")
    return True


def validate_adapter_provenance(adapter, gate):
    parameter_path, vector_path = REQUIRED_DATA_PATHS[:2]
    if (adapter.vector_sha256 != gate["data_hashes"][vector_path] or
            adapter.parameter_sha256 != gate["data_hashes"][parameter_path]):
        raise ValueError("adapter parsed bytes differ from gate-bound bytes")
    if (adapter.k != 48 or adapter.dimension != DIMENSION or
            tuple(adapter.strata) != STRATA):
        raise ValueError("adapter dimension/strata differ from C10 gate")
    exact = expected_conventions()["support_parameters"]
    observed = {
        "alpha": str(adapter.alpha_exact), "delta": str(adapter.delta_exact),
        "eta": str(adapter.eta_exact), "beta1": str(adapter.beta1_exact),
        "beta2": str(adapter.beta2_exact),
        "beta3plus": str(adapter.beta3_exact),
    }
    if observed != exact:
        raise ValueError("adapter exact support parameters differ from gate")
    return True


def validate_weight_provenance(weights, oracle, gate):
    expected_path = REQUIRED_DATA_PATHS[2]
    if (weights["sha256"] != gate["data_hashes"][expected_path] or
            weights["prefix"] != "baseline_" or
            weights["j_scale_to_numerator"] != 1):
        raise ValueError("stratum weights do not use the pinned 48J convention")
    with localcontext() as context:
        context.prec = 240

        def decimal_fraction(value):
            return Decimal(value.numerator) / Decimal(value.denominator)

        tolerance = Decimal("1e-110")
        comparisons = (
            (weights["denominator"], decimal_fraction(oracle["I0"]),
             "I0 normalizer"),
            (weights["numerator"], decimal_fraction(oracle["B0"]),
             "48J0 normalizer"),
            (weights["base_quotient"],
             decimal_fraction(oracle["base_quotient"]), "base quotient"),
        )
        for observed, exact, name in comparisons:
            if abs(observed / exact - 1) > tolerance:
                raise ArithmeticError(f"pinned {name} differs from exact oracle")
        for r in STRATA:
            exact_weight = decimal_fraction(
                oracle["E_I"][CHANNEL_COUNT * r][CHANNEL_COUNT * r])
            if abs(weights["i_weights"][r] / exact_weight - 1) > tolerance:
                raise ArithmeticError(
                    f"pinned I stratum weight {r} differs from exact oracle")
        if (abs(sum(weights["i_weights"]) - 1) > Decimal("1e-180") or
                abs(sum(weights["j_weights"]) - 1) > Decimal("1e-180") or
                any(value <= 0 for value in
                    weights["i_weights"] + weights["j_weights"])):
            raise ArithmeticError("normalized stratum weights are invalid")
    return True


def local_zero_se_failures(target, stratum, local, standard_error):
    local = np.asarray(local, dtype=float)
    standard_error = np.asarray(standard_error, dtype=float)
    if (local.ndim != 2 or local.shape[0] != local.shape[1] or
            standard_error.shape != local.shape):
        raise ValueError("local zero-SE matrices have incompatible shape")
    allowed = analytic_local_zero_se_entries(target, stratum)
    active = exact_local_active_pairs(target, stratum)
    failures = []
    for i, j in upper_pairs(local.shape[0]):
        if ((i, j) in active and standard_error[i, j] == 0 and
                (i, j) not in allowed):
            failures.append((i, j))
    return failures


def global_zero_se_failures(exact, standard_error, mask, *, allowed=()):
    exact = np.asarray(exact, dtype=float)
    standard_error = np.asarray(standard_error, dtype=float)
    mask = np.asarray(mask, dtype=bool)
    if not (exact.shape == standard_error.shape == mask.shape and
            exact.ndim == 2 and exact.shape[0] == exact.shape[1]):
        raise ValueError("global zero-SE matrices have incompatible shape")
    allowed = set(allowed)
    failures = []
    for i, j in upper_pairs(exact.shape[0]):
        if (mask[i, j] and exact[i, j] != 0 and
                standard_error[i, j] == 0 and (i, j) not in allowed):
            failures.append((i, j))
    return failures


def reconstruct_matrices(records, oracle, weights, schedule,
                         *, excluded_identity=None, diagnostics=True):
    groups = _group_records(records)
    a_matrix = np.zeros((DIMENSION, DIMENSION))
    b_matrix = np.zeros((DIMENSION, DIMENSION))
    a_variance = np.zeros_like(a_matrix)
    b_variance = np.zeros_like(b_matrix)
    conditional = []
    min_ess = math.inf
    max_rhat = 0.0
    min_z = math.inf
    z_gates = []
    local_zero_se = []
    local_cache = {}
    batch_size = schedule["samples_per_batch"]

    for target in ("I", "J"):
        for r in STRATA:
            selected = [record for record in groups[(target, r)]
                        if _record_identity(record) != excluded_identity]
            expected_count = 3 if excluded_identity is not None and \
                excluded_identity[:2] == (target, r) else 4
            if len(selected) != expected_count:
                raise ValueError("chain deletion removed wrong group/count")
            parsed = [_record_arrays(record) for record in selected]
            batch_upper = np.stack([item[0] for item in parsed])
            raw_sum = sum((item[2] for item in parsed),
                          np.zeros_like(parsed[0][2]))
            raw_second = sum((item[3] for item in parsed),
                             np.zeros_like(parsed[0][3]))
            samples = sum(record["sample_count"] for record in selected)
            raw_mean = raw_sum / samples
            raw_second_mean = raw_second / samples
            indices = local_indices(target, r)
            local_dimension = len(indices)
            batch_matrices = _upper_to_matrix(batch_upper, local_dimension)
            if target == "I":
                local = np.mean(batch_matrices, axis=(0, 1))
                flattened = batch_matrices.reshape((-1, local_dimension,
                                                    local_dimension))
                se = np.std(flattened, axis=0, ddof=1) / math.sqrt(
                    len(flattened))
                weight = float(weights["i_weights"][r])
                _matrix_add_local(target, a_matrix, local, indices, weight)
                _matrix_add_local(target, a_variance, se * se, indices,
                                  weight * weight)
                diagnostic_batches = batch_upper
                # Constant*constant is analytically fixed.  Exact-zero I
                # entries are not stochastic retained moments.
                moment_mask = list(diagnostic_moment_indices(target, r))
                z_summary = None
            else:
                batch_z = np.stack([item[1] for item in parsed])
                ratio = ratio_matrix_delta(batch_matrices, batch_z)
                local = ratio["ratio"]
                se = ratio["standard_error"]
                weight = float(weights["j_weights"][r])
                _matrix_add_local(target, b_matrix, local, indices, weight)
                _matrix_add_local(target, b_variance, se * se, indices,
                                  weight * weight)
                diagnostic_batches = np.concatenate(
                    (batch_upper, batch_z[..., None]), axis=2)
                moment_mask = list(diagnostic_moment_indices(target, r))
                z_flat = batch_z.reshape(-1)
                z_se = float(np.std(z_flat, ddof=1) / math.sqrt(len(z_flat)))
                z_mean = float(ratio["mean_denominator"])
                z_relative = z_se / z_mean
                z_pass = z_mean - 6 * z_se > 0 and z_relative <= 0.02
                min_z = min(min_z, z_mean)
                z_gates.append(z_pass)
                z_summary = {
                    "mean": z_mean, "standard_error": z_se,
                    "relative_standard_error": z_relative,
                    "six_se_lower": z_mean - 6 * z_se, "pass": z_pass}
            for i, j in local_zero_se_failures(target, r, local, se):
                local_zero_se.append({
                    "target": target, "stratum": r,
                    "local_entry": [i, j],
                    "global_entry": [indices[i], indices[j]],
                })
            local_cache[(target, r, excluded_identity)] = local

            if diagnostics and moment_mask:
                selected_batches = diagnostic_batches[..., moment_mask]
                selected_mean = raw_mean[moment_mask]
                selected_second = raw_second_mean[moment_mask]
                rhat = np.asarray(split_rhat(selected_batches))
                ess = np.asarray(batch_means_ess(
                    selected_mean, selected_second, selected_batches,
                    batch_size))
                # +infinity is the deliberate fail value for a split-R-hat
                # with zero within-chain and positive between-chain variance;
                # it is a predeclared statistical failure eligible for the
                # one extension, not an algebraic exception.  NaN and every
                # nonfinite ESS remain implementation failures.
                if np.any(np.isnan(rhat)) or not np.all(np.isfinite(ess)):
                    raise ArithmeticError("invalid conditional diagnostic")
                max_rhat = max(max_rhat, float(np.max(rhat, initial=0)))
                min_ess = min(min_ess, float(np.min(ess, initial=math.inf)))
                conditional.append({
                    "target": target, "stratum": r,
                    "moments_checked": len(moment_mask),
                    "maximum_split_rhat": float(np.max(rhat)),
                    "minimum_batch_means_ess": float(np.min(ess)),
                    "z": z_summary,
                })
            elif diagnostics:
                conditional.append({
                    "target": target, "stratum": r,
                    "moments_checked": 0,
                    "maximum_split_rhat": 1.0,
                    "minimum_batch_means_ess": float(samples),
                    "z": z_summary,
                })

    a_se = np.sqrt(a_variance)
    b_se = np.sqrt(b_variance)
    return {
        "A": a_matrix,
        "B": b_matrix,
        "A_standard_error": a_se,
        "B_standard_error": b_se,
        "conditional": conditional,
        "maximum_split_rhat": max_rhat,
        "minimum_batch_means_ess": min_ess,
        "minimum_mean_z": min_z,
        "all_z_precision_pass": all(z_gates),
        "local_zero_se_failures": local_zero_se,
        "local_cache": local_cache,
    }


def _acceptance_gates(records):
    chain_positive = True
    group_rates = []
    summaries = []
    for record in records:
        totals = {move: {"attempted": 0, "accepted": 0,
                         "support_rejected": 0}
                  for move in ("physical-physical", "physical-slack")}
        for stage in record["acceptance"].values():
            for move, counts in stage.items():
                for key in totals[move]:
                    totals[move][key] += counts[key]
        chain_positive &= all(counts["accepted"] > 0
                              for counts in totals.values())
        summaries.append({**{key: record[key] for key in
                             ("target", "stratum", "replicate")},
                          "moves": totals})
    groups = _group_records(records)
    aggregate_pass = True
    for (target, r), group in groups.items():
        for move in ("physical-physical", "physical-slack"):
            attempted = accepted = 0
            for record in group:
                for stage in record["acceptance"].values():
                    attempted += stage[move]["attempted"]
                    accepted += stage[move]["accepted"]
            rate = accepted / attempted if attempted else 0.0
            aggregate_pass &= rate >= 0.01
            group_rates.append({"target": target, "stratum": r,
                                "move_type": move, "attempted": attempted,
                                "accepted": accepted, "rate": rate})
    return {"chain_move_positive": chain_positive,
            "aggregate_move_rate_pass": aggregate_pass,
            "chains": summaries, "group_rates": group_rates}


def _exact_and_estimated_roots(reconstruction, oracle):
    answer = {}
    exact_a = np.asarray([[float(x) for x in row] for row in oracle["E_I"]])
    exact_b = np.asarray([[float(x) for x in row] for row in oracle["E_J"]])
    for degree, expected_active in ((0, 16), (1, 47), (2, 93)):
        principal = tuple(principal_indices(STRATA, degree))
        active = [position for position, global_index in enumerate(principal)
                  if oracle["E_I"][global_index][global_index] > 0]
        if len(active) != expected_active:
            raise ArithmeticError("oracle active-coordinate count mismatch")
        estimated = largest_generalized_root(
            reconstruction["A"][np.ix_(principal, principal)],
            reconstruction["B"][np.ix_(principal, principal)],
            base_quotient=float(oracle["base_quotient"]),
            relative_rank_tolerance=1e-12,
            active_indices=active)
        exact = largest_generalized_root(
            exact_a[np.ix_(principal, principal)],
            exact_b[np.ix_(principal, principal)],
            base_quotient=float(oracle["base_quotient"]),
            relative_rank_tolerance=1e-12,
            active_indices=active)
        answer[degree] = {"principal": principal, "active": active,
                          "estimated": estimated, "exact": exact}
    return answer


def _root_values(reconstruction, oracle):
    return {degree: data["estimated"]["root"]
            for degree, data in _exact_and_estimated_roots(
                reconstruction, oracle).items()}


def _jackknife_roots(records, full_reconstruction, oracle, weights, schedule):
    full_roots = _root_values(full_reconstruction, oracle)
    deletions = {degree: [] for degree in full_roots}
    grouped = {(target, r): {degree: [] for degree in full_roots}
               for target in ("I", "J") for r in STRATA}
    for record in records:
        identity = _record_identity(record)
        reconstruction = reconstruct_matrices(
            records, oracle, weights, schedule,
            excluded_identity=identity, diagnostics=False)
        roots = _root_values(reconstruction, oracle)
        for degree, root in roots.items():
            item = {"target": identity[0], "stratum": identity[1],
                    "replicate": identity[2], "root": root}
            deletions[degree].append(item)
            grouped[(identity[0], identity[1])][degree].append(root)
    answer = {}
    exact_roots = {degree: data["exact"]["root"]
                   for degree, data in _exact_and_estimated_roots(
                       full_reconstruction, oracle).items()}
    for degree, full in full_roots.items():
        variance = 0.0
        for key in grouped:
            values = np.asarray(grouped[key][degree])
            if len(values) != 4:
                raise ArithmeticError("jackknife group does not have four deletions")
            variance += 3 / 4 * float(np.sum((values - np.mean(values)) ** 2))
        standard_error = math.sqrt(max(0.0, variance))
        exact = exact_roots[degree]
        discrepancy = abs(full - exact) / abs(exact)
        interval_pass = abs(full - exact) <= 6 * standard_error
        answer[degree] = {
            "full": full, "exact": exact,
            "jackknife_standard_error": standard_error,
            "six_se_lower": full - 6 * standard_error,
            "six_se_upper": full + 6 * standard_error,
            "exact_in_interval": interval_pass,
            "relative_discrepancy": discrepancy,
            "relative_discrepancy_pass": discrepancy <= 0.005,
            "maximum_delete_shift": max(
                abs(item["root"] - full) for item in deletions[degree]),
            "deletions": deletions[degree],
        }
    return answer


def analyze_records(records, oracle, weights, schedule, *, adapter=None,
                    do_jackknife=True):
    validate_analytic_zero_se_proofs(oracle)
    chain_specs = schedule["chains"]
    if len(records) != len(chain_specs):
        raise ValueError("production result must contain exactly 128 chains")
    by_identity = {_record_identity(record): record for record in records}
    if len(by_identity) != len(records):
        raise ValueError("duplicate chain identity")
    ordered = []
    for spec in chain_specs:
        identity = (spec["target"], spec["stratum"], spec["replicate"])
        if identity not in by_identity:
            raise ValueError("missing frozen chain")
        record = by_identity[identity]
        validate_chain_record(record, spec, schedule, adapter=adapter)
        ordered.append(record)
    records = ordered
    reconstruction = reconstruct_matrices(records, oracle, weights, schedule)
    i_mask, j_mask = structural_masks()
    exact_a = np.asarray([[float(x) for x in row] for row in oracle["E_I"]])
    exact_b = np.asarray([[float(x) for x in row] for row in oracle["E_J"]])
    if (np.any(reconstruction["A"][~(i_mask | i_mask.T)] != 0) or
            np.any(reconstruction["B"][~(j_mask | j_mask.T)] != 0)):
        raise ArithmeticError("nonstructural matrix entry is not exactly zero")
    coverage_i = simultaneous_coverage(
        reconstruction["A"], reconstruction["A_standard_error"], exact_a,
        i_mask, 6)
    coverage_j = simultaneous_coverage(
        reconstruction["B"], reconstruction["B_standard_error"], exact_b,
        j_mask, 6)
    if coverage_i["checked_entries"] != 336 or \
            coverage_j["checked_entries"] != 876:
        raise AssertionError("coverage structural counts changed")

    # Global I constants are weighted analytic identities.  There is no
    # global J exemption: in particular B[90,90] retains the independently
    # sampled common-r=14 contribution even though common-r=15 y_00/z is an
    # analytic local identity.
    analytic_i_global = {
        (CHANNEL_COUNT * r, CHANNEL_COUNT * r) for r in STRATA}
    bad_zero_se_i = global_zero_se_failures(
        exact_a, reconstruction["A_standard_error"], i_mask,
        allowed=analytic_i_global)
    bad_zero_se_j = global_zero_se_failures(
        exact_b, reconstruction["B_standard_error"], j_mask)

    constants = [CHANNEL_COUNT * r for r in STRATA]
    constant_a = float(np.sum(reconstruction["A"][np.ix_(constants, constants)]))
    constant_b = float(np.sum(reconstruction["B"][np.ix_(constants, constants)]))
    constant_tolerance = 256 * np.finfo(float).eps
    constant_pass = (abs(constant_a - 1) <= constant_tolerance and
                     abs(constant_b - 1) <= constant_tolerance)
    acceptance = _acceptance_gates(records)
    roots = _exact_and_estimated_roots(reconstruction, oracle)
    jackknife = (_jackknife_roots(records, reconstruction, oracle, weights,
                                  schedule) if do_jackknife else {})

    hard_gates = {
        "all_128_chains_present": True,
        "structural_counts_336_876": True,
        "nonstructural_entries_exact_zero": True,
        "raw_antisymmetry_bitwise_zero": all(
            parse_float_hex(record["raw_antisymmetry"]) == 0
            for record in records),
        "no_nontrivial_exact_nonzero_zero_se": (
            len(reconstruction["local_zero_se_failures"]) == 0 and
            len(bad_zero_se_i) == 0 and len(bad_zero_se_j) == 0),
        "constant_coordinate_sums_one": constant_pass,
        "positive_acceptance_each_move_each_chain":
            acceptance["chain_move_positive"],
        "aggregate_acceptance_at_least_one_percent":
            acceptance["aggregate_move_rate_pass"],
        "active_counts_and_full_rank": all(
            data["estimated"]["rank"] == expected
            for (degree, expected), data in zip(
                ((0, 16), (1, 47), (2, 93)),
                (roots[0], roots[1], roots[2]))),
        "roots_finite": all(math.isfinite(data["estimated"]["root"])
                            for data in roots.values()),
        "root_deletion_stability": (not do_jackknife or all(
            item["exact_in_interval"] and
            item["relative_discrepancy_pass"]
            for item in jackknife.values())),
    }
    statistical_gates = {
        "split_rhat": reconstruction["maximum_split_rhat"] <= 1.05,
        "batch_means_ess": reconstruction["minimum_batch_means_ess"] >= 200,
        "z_precision": reconstruction["all_z_precision_pass"],
        "simultaneous_coverage": coverage_i["pass"] and coverage_j["pass"],
    }
    max_standardized = max(
        coverage_i["max_standardized_discrepancy"],
        coverage_j["max_standardized_discrepancy"])
    failed_statistical = [key for key, value in statistical_gates.items()
                          if not value]
    extension_authorized = (
        all(hard_gates.values()) and bool(failed_statistical) and
        max_standardized <= 12 and
        set(failed_statistical) <= {
            "split_rhat", "batch_means_ess", "z_precision",
            "simultaneous_coverage"})
    gates_passed = all(hard_gates.values()) and all(statistical_gates.values())
    return {
        "records": records,
        "reconstruction": reconstruction,
        "coverage_i": coverage_i,
        "coverage_j": coverage_j,
        "constant_sum_i": constant_a,
        "constant_sum_j": constant_b,
        "bad_local_zero_se": reconstruction["local_zero_se_failures"],
        "bad_zero_se_i": [list(map(int, row)) for row in bad_zero_se_i],
        "bad_zero_se_j": [list(map(int, row)) for row in bad_zero_se_j],
        "acceptance": acceptance,
        "roots": roots,
        "jackknife": jackknife,
        "hard_gates": hard_gates,
        "statistical_gates": statistical_gates,
        "maximum_standardized_oracle_discrepancy": max_standardized,
        "gates_passed": gates_passed,
        "extension_authorized": extension_authorized,
    }


def capture_analysis(records, oracle, weights, schedule, *, adapter):
    """Turn algebra/statistics rejection into a durable fail-closed result."""
    try:
        return (analyze_records(
            records, oracle, weights, schedule, adapter=adapter,
            do_jackknife=True), None)
    except (ArithmeticError, ValueError, AssertionError) as error:
        return (None, {"exception_type": type(error).__name__,
                       "message": str(error)})


def _json_safe(value):
    if isinstance(value, np.ndarray):
        return _json_safe(value.tolist())
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, (np.floating, float)):
        if not math.isfinite(float(value)):
            if math.isnan(float(value)):
                label = "nan"
            elif float(value) > 0:
                label = "positive-infinity"
            else:
                label = "negative-infinity"
            return {"nonfinite_float": label}
        return {"float_hex": float_hex(value)}
    if isinstance(value, Fraction):
        return str(value)
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()
                if key != "local_cache"}
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise TypeError(f"cannot serialize value of type {type(value).__name__}")


def _dependency_snapshot(gate):
    answer = {}
    for table in (gate["source_hashes"], gate["data_hashes"]):
        for relative, expected in table.items():
            observed = sha256_file(REPO_ROOT / relative)
            if observed != expected:
                raise ValueError(f"dependency changed during run: {relative}")
            answer[relative] = observed
    return answer


def _extra_snapshot(extra_hashes):
    extra_hashes = {} if extra_hashes is None else extra_hashes
    if not isinstance(extra_hashes, dict):
        raise TypeError("extra hash bindings must be a path-to-SHA mapping")
    answer = {}
    for raw_path, expected_raw in extra_hashes.items():
        if isinstance(expected_raw, str):
            expected = {"sha256": expected_raw}
        elif isinstance(expected_raw, dict) and set(expected_raw) == {
                "sha256", "device", "inode"}:
            expected = expected_raw
        elif isinstance(expected_raw, dict) and set(expected_raw) == {
                "kind", "device", "inode"} and \
                expected_raw["kind"] == "directory":
            expected = expected_raw
        else:
            raise ValueError("malformed extra hash binding")
        digest = expected.get("sha256")
        if (not isinstance(raw_path, str) or
                (digest is not None and (
                    not isinstance(digest, str) or len(digest) != 64 or
                    any(c not in "0123456789abcdef" for c in digest)))):
            raise ValueError("malformed extra hash binding")
        for key in ("device", "inode"):
            if key in expected and (isinstance(expected[key], bool) or
                                    not isinstance(expected[key], int) or
                                    expected[key] < 0):
                raise ValueError("malformed extra inode binding")
        resolved = str(Path(raw_path).resolve())
        if expected.get("kind") == "directory":
            normalized = {"kind": "directory", "device": expected["device"],
                          "inode": expected["inode"]}
        else:
            normalized = {"sha256": digest}
        if "device" in expected and "device" not in normalized:
            normalized.update(device=expected["device"], inode=expected["inode"])
        if resolved in answer and answer[resolved] != normalized:
            raise ValueError("one extra path has conflicting hashes")
        if expected.get("kind") == "directory":
            observed = read_directory_binding(resolved)
            if ((observed["device"], observed["inode"]) !=
                    (expected["device"], expected["inode"])):
                raise ValueError(
                    f"dynamic dependency directory changed: {resolved}")
        else:
            observed = read_file_snapshot(resolved)
            if observed["sha256"] != digest:
                raise ValueError(f"dynamic dependency changed: {resolved}")
            if ("device" in expected and
                    (observed["device"], observed["inode"]) !=
                    (expected["device"], expected["inode"])):
                raise ValueError(
                    f"dynamic dependency inode changed: {resolved}")
        answer[resolved] = normalized
    return answer


def canonical_object_sha256(value):
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"),
                         allow_nan=False).encode()
    return sha256_bytes(encoded)


def chain_checkpoint_path(directory, chain_spec, *, extension=False):
    suffix = "extended" if extension else "initial"
    return Path(directory) / (
        f"{chain_spec['target']}_r{chain_spec['stratum']:02d}_"
        f"rep{chain_spec['replicate']}_{suffix}.json")


def validate_fresh_checkpoint_directory(handle, chains, *, extension=False):
    """Bind the authorized directory and prove every scheduled path absent."""
    validate_open_directory(handle)
    paths = [chain_checkpoint_path(handle["path"], spec, extension=extension)
             for spec in chains]
    resolved = [str(path.resolve()) for path in paths]
    if len(paths) != 128 or len(set(resolved)) != 128:
        raise ValueError("fresh checkpoint schedule is not 128 unique paths")
    preexisting = [str(path) for path in paths
                   if directory_entry_exists(handle, path.name)]
    if preexisting:
        raise FileExistsError(
            "fresh-only calibration rejects preexisting checkpoint: " +
            preexisting[0])
    # Rebind after the complete absence scan.  O_EXCL publication below
    # closes a create-after-scan race for every individual checkpoint.
    validate_open_directory(handle)
    return handle


def chain_checkpoint_payload(record, chain_spec, gate_sha256, driver_sha256,
                             authorization_sha256, schedule, *, extension=False,
                             parent_checkpoint_sha256=None):
    return {
        "status": ("complete-d4-extended-chain-record" if extension else
                   "complete-d4-initial-chain-record"),
        "rigorous": False,
        "gate_sha256": gate_sha256,
        "driver_sha256": driver_sha256,
        "authorization_sha256": authorization_sha256,
        "schedule_sha256": canonical_object_sha256(schedule),
        "extension": extension,
        "parent_checkpoint_sha256": parent_checkpoint_sha256,
        "chain_spec": chain_spec,
        "record": record,
    }


def load_chain_checkpoint(path, chain_spec, gate_sha256, driver_sha256,
                          authorization_sha256, schedule, *, adapter=None,
                          extension=False,
                          parent_checkpoint_sha256=None,
                          directory_handle=None):
    path = Path(path)
    if directory_handle is None:
        snapshot = read_file_snapshot(path)
    else:
        validate_open_directory(directory_handle)
        if (str(path.parent.resolve()) != directory_handle["path"] or
                path.name != _directory_leaf(path.name)):
            raise ValueError("checkpoint path differs from held directory")
        snapshot = read_file_snapshot_at(directory_handle, path.name)
    data = snapshot["data"]
    raw = strict_json_bytes(data, "chain checkpoint")
    _exact_keys(raw, {
        "status", "rigorous", "gate_sha256", "driver_sha256",
        "authorization_sha256",
        "schedule_sha256", "extension", "parent_checkpoint_sha256",
        "chain_spec", "record"}, "chain checkpoint")
    expected_status = ("complete-d4-extended-chain-record" if extension else
                       "complete-d4-initial-chain-record")
    if (raw["status"] != expected_status or raw["rigorous"] is not False or
            raw["gate_sha256"] != gate_sha256 or
            raw["driver_sha256"] != driver_sha256 or
            raw["authorization_sha256"] != authorization_sha256 or
            raw["schedule_sha256"] != canonical_object_sha256(schedule) or
            raw["extension"] is not extension or
            raw["parent_checkpoint_sha256"] != parent_checkpoint_sha256 or
            raw["chain_spec"] != chain_spec):
        raise ValueError("chain checkpoint provenance mismatch")
    validate_chain_record(raw["record"], chain_spec, schedule,
                          adapter=adapter)
    return {"record": raw["record"], **public_binding(snapshot)}


def run_fresh_initial_chain(adapter, chain_spec, schedule, record_directory,
                            gate_sha256, driver_sha256, authorization,
                            gate_bound, *, progress):
    validate_open_directory(record_directory)
    path = chain_checkpoint_path(record_directory["path"], chain_spec)
    if directory_entry_exists(record_directory, path.name):
        raise FileExistsError(
            "fresh-only production refuses an existing checkpoint")
    record = run_one_chain(
        adapter, chain_spec, schedule, progress=progress)
    validate_chain_record(record, chain_spec, schedule, adapter=adapter)
    payload = chain_checkpoint_payload(
        record, chain_spec, gate_sha256, driver_sha256,
        authorization["sha256"], schedule)
    digest = write_new_result(
        path, payload, gate_bound["gate"], extra_hashes={
            gate_bound["path"]: inode_binding(gate_bound),
            authorization["path"]: inode_binding(authorization),
            record_directory["path"]:
                directory_inode_binding(record_directory),
        }, directory_handle=record_directory)
    # Reopen the exact published bytes rather than trusting the in-memory
    # record that was passed to the serializer.
    loaded = load_chain_checkpoint(
        path, chain_spec, gate_sha256, driver_sha256,
        authorization["sha256"], schedule, adapter=adapter,
        directory_handle=record_directory)
    if loaded["sha256"] != digest:
        raise ArithmeticError("checkpoint digest changed after publication")
    return loaded


def run_fresh_extended_chain(adapter, initial_checkpoint, chain_spec,
                             schedule, extension_record_directory, gate_sha256,
                             driver_sha256, authorization, parent_result,
                             gate_bound, *, progress):
    combined_schedule = extended_schedule(schedule)
    validate_open_directory(extension_record_directory)
    path = chain_checkpoint_path(
        extension_record_directory["path"], chain_spec, extension=True)
    parent_digest = initial_checkpoint["sha256"]
    if directory_entry_exists(extension_record_directory, path.name):
        raise FileExistsError(
            "fresh-only extension refuses an existing checkpoint")
    record = extend_one_chain(
        adapter, initial_checkpoint["record"], chain_spec, schedule,
        progress=progress)
    payload = chain_checkpoint_payload(
        record, chain_spec, gate_sha256, driver_sha256,
        authorization["sha256"], combined_schedule, extension=True,
        parent_checkpoint_sha256=parent_digest)
    digest = write_new_result(
        path, payload, gate_bound["gate"], extra_hashes={
            gate_bound["path"]: inode_binding(gate_bound),
            authorization["path"]: inode_binding(authorization),
            parent_result["path"]: inode_binding(parent_result),
            initial_checkpoint["path"]: inode_binding(initial_checkpoint),
            extension_record_directory["path"]:
                directory_inode_binding(extension_record_directory),
        }, directory_handle=extension_record_directory)
    loaded = load_chain_checkpoint(
        path, chain_spec, gate_sha256, driver_sha256,
        authorization["sha256"], combined_schedule, adapter=adapter,
        extension=True,
        parent_checkpoint_sha256=parent_digest,
        directory_handle=extension_record_directory)
    if loaded["sha256"] != digest:
        raise ArithmeticError(
            "extended checkpoint digest changed after publication")
    return loaded


def load_parent_result(path, gate_sha256, driver_sha256, schedule):
    snapshot = read_file_snapshot(path)
    data = snapshot["data"]
    raw = strict_json_bytes(data, "parent calibration result")
    _exact_keys(raw, {
        "status", "rigorous", "theorem_ready", "mode", "gate_path",
        "gate_sha256", "driver_sha256", "authorization_sha256",
        "parent_result_sha256", "gate_binding", "authorization_binding",
        "parent_result_binding", "float_encoding", "conventions", "schedule",
        "wall_seconds", "peak_rss_kib",
        "records", "record_checkpoints", "analysis",
        "analysis_failure", "fresh_exact_reconstruction_required"},
                "parent calibration result")
    validate_public_binding(
        raw["gate_binding"], expected_sha256=gate_sha256,
        name="parent gate binding")
    validate_public_binding(
        raw["authorization_binding"],
        expected_sha256=raw["authorization_sha256"],
        name="parent authorization binding")
    if raw["parent_result_binding"] is not None:
        raise ValueError("initial parent result cannot itself have a parent")
    if (raw["status"] != "d4-stratified-calibration-rejected" or
            raw["rigorous"] is not False or raw["theorem_ready"] is not False or
            raw["mode"] != "production" or
            raw["gate_sha256"] != gate_sha256 or
            raw["driver_sha256"] != driver_sha256 or
            not isinstance(raw["authorization_sha256"], str) or
            len(raw["authorization_sha256"]) != 64 or
            raw["parent_result_sha256"] is not None or
            raw["float_encoding"] != FLOAT_ENCODING or
            raw["conventions"] != expected_conventions() or
            raw["schedule"] != schedule or
            raw["analysis"] is None or raw["analysis_failure"] is not None or
            raw["fresh_exact_reconstruction_required"] is not True or
            not isinstance(raw["records"], list) or
            not isinstance(raw["record_checkpoints"], list)):
        raise ValueError("parent result is not an extendible rejected run")
    validate_run_metrics(raw["wall_seconds"], raw["peak_rss_kib"])
    return {"raw": raw, **public_binding(snapshot)}


def validate_parent_checkpoint_manifest(parent, record_dir, schedule):
    """Bind extension inputs to the already-authorized parent result."""
    bindings = parent["raw"]["record_checkpoints"]
    records = parent["raw"]["records"]
    chains = schedule["chains"]
    if (not isinstance(bindings, list) or len(bindings) != 128 or
            not isinstance(records, list) or len(records) != 128 or
            len(chains) != 128):
        raise ValueError("parent checkpoint manifest is not complete")
    seen = set()
    canonical_record_dir = str(Path(record_dir).resolve())
    for binding, record, spec in zip(bindings, records, chains):
        validate_public_binding(binding, name="parent checkpoint binding")
        expected_path = str(chain_checkpoint_path(
            canonical_record_dir, spec).resolve())
        if binding["path"] != expected_path or expected_path in seen:
            raise ValueError(
                "parent checkpoint manifest path/order mismatch")
        seen.add(expected_path)
        if any(record.get(key) != spec[key] for key in (
                "target", "stratum", "replicate", "initial_seed",
                "transition_seed")):
            raise ValueError("parent record identity/order mismatch")
    directory = open_bound_directory(
        read_directory_binding(canonical_record_dir))
    validate_open_directory(directory)
    return bindings, directory


def _hash_open_descriptor(descriptor):
    position = os.lseek(descriptor, 0, os.SEEK_CUR)
    os.lseek(descriptor, 0, os.SEEK_SET)
    digest = hashlib.sha256()
    while True:
        block = os.read(descriptor, 1024 * 1024)
        if not block:
            break
        digest.update(block)
    os.lseek(descriptor, position, os.SEEK_SET)
    return digest.hexdigest()


def _path_binds_descriptor(path, descriptor, expected_digest):
    owned = os.fstat(descriptor)
    if not stat.S_ISREG(owned.st_mode):
        return False
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        path_descriptor = os.open(path, flags)
    except (FileNotFoundError, OSError):
        return False
    try:
        observed = os.fstat(path_descriptor)
        return ((observed.st_dev, observed.st_ino) ==
                (owned.st_dev, owned.st_ino) and
                stat.S_ISREG(observed.st_mode) and
                _hash_open_descriptor(path_descriptor) == expected_digest)
    finally:
        os.close(path_descriptor)


def _directory_entry_binds_descriptor(handle, name, descriptor,
                                      expected_digest):
    validate_open_directory(handle)
    name = _directory_leaf(name)
    owned = os.fstat(descriptor)
    if not stat.S_ISREG(owned.st_mode):
        return False
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        path_descriptor = os.open(
            name, flags, dir_fd=handle["descriptor"])
    except (FileNotFoundError, OSError):
        return False
    try:
        observed = os.fstat(path_descriptor)
        return ((observed.st_dev, observed.st_ino) ==
                (owned.st_dev, owned.st_ino) and
                stat.S_ISREG(observed.st_mode) and
                _hash_open_descriptor(path_descriptor) == expected_digest)
    finally:
        os.close(path_descriptor)


def _write_new_result_bound(path, payload, gate, *, extra_hashes,
                            directory_handle):
    """Publish one leaf solely through an already-held parent dirfd."""
    path = Path(path)
    validate_open_directory(directory_handle)
    if (str(path.parent.resolve()) != directory_handle["path"] or
            path.name != _directory_leaf(path.name)):
        raise ValueError("relative output differs from held directory")
    path = Path(directory_handle["path"]) / path.name
    resolved_output = path.resolve()
    protected = {(REPO_ROOT / relative).resolve()
                 for relative in (*REQUIRED_SOURCE_PATHS,
                                   *REQUIRED_DATA_PATHS)}
    if resolved_output in protected:
        raise ValueError("output aliases a trusted input")
    normalized_extra = _extra_snapshot(extra_hashes)
    if str(resolved_output) in normalized_extra:
        raise ValueError("output aliases a dynamic trusted input")
    flags = os.O_RDWR | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(
        path.name, flags, 0o600, dir_fd=directory_handle["descriptor"])
    descriptor_open = True
    try:
        encoded = (json.dumps(_json_safe(payload), sort_keys=True,
                              separators=(",", ":"), allow_nan=False) +
                   "\n").encode()
        encoded_digest = sha256_bytes(encoded)
        _dependency_snapshot(gate)
        _extra_snapshot(normalized_extra)
        validate_open_directory(directory_handle)
        with os.fdopen(descriptor, "wb", closefd=False) as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        entry_binds = _directory_entry_binds_descriptor(
            directory_handle, path.name, descriptor, encoded_digest)
        if (_hash_open_descriptor(descriptor) != encoded_digest or
                not entry_binds):
            raise ArithmeticError("published result bytes/inode changed")
        _dependency_snapshot(gate)
        _extra_snapshot(normalized_extra)
        validate_open_directory(directory_handle)
        entry_binds = _directory_entry_binds_descriptor(
            directory_handle, path.name, descriptor, encoded_digest)
        if not entry_binds:
            raise ArithmeticError("published result path changed after rebind")
        os.close(descriptor)
        descriptor_open = False
        return encoded_digest
    except Exception:
        # Fail closed through the held descriptor; never rename/unlink a path
        # after a separate ownership check.
        try:
            rejection = b'{"status":"rejected-incomplete-calibration-output"}\n'
            os.lseek(descriptor, 0, os.SEEK_SET)
            os.ftruncate(descriptor, 0)
            os.write(descriptor, rejection)
            os.fsync(descriptor)
        finally:
            if descriptor_open:
                os.close(descriptor)
                descriptor_open = False
        raise


def write_new_result(path, payload, gate, *, extra_hashes=None,
                     directory_handle=None):
    """Create a new result through a held canonical output-parent dirfd.

    The caller-supplied spelling is resolved exactly once.  After that point
    every create, reopen, and inode check is relative to the held parent; a
    mutable ancestor symlink therefore cannot redirect a successful result.
    """
    owns_directory = directory_handle is None
    if owns_directory:
        raw_path = Path(path)
        name = _directory_leaf(raw_path.name)
        parent = read_directory_binding(raw_path.parent)
        directory_handle = open_bound_directory(parent)
        path = Path(directory_handle["path"]) / name
    try:
        return _write_new_result_bound(
            path, payload, gate, extra_hashes=extra_hashes,
            directory_handle=directory_handle)
    finally:
        if owns_directory:
            close_bound_directory(directory_handle)


def tiny_smoke_schedule():
    return {
        **expected_schedule(),
        "tempering_powers": ["0", "1"],
        "steps_per_tempering_power": 2,
        "power_one_burn_in_steps": 2,
        "retained_samples": 8,
        "proposal_steps_per_sample": 1,
        "batches_per_chain": 4,
        "samples_per_batch": 2,
        "extension_samples_per_chain": 8,
        "extension_total_samples_per_chain": 16,
        "extension_total_batches_per_chain": 8,
    }


def run_smoke(adapter):
    schedule = tiny_smoke_schedule()
    selected = [expected_chain_table()[0], expected_chain_table()[64]]
    records = [run_one_chain(adapter, spec, schedule) for spec in selected]
    for spec, record in zip(selected, records):
        validate_chain_record(record, spec, schedule, adapter=adapter)
    return records


def _main(open_directories):
    run_started = time.perf_counter()
    parser = argparse.ArgumentParser()
    parser.add_argument("--gate", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", choices=(
        "preflight", "smoke", "production", "extension"),
                        default="preflight")
    parser.add_argument("--authorization")
    parser.add_argument("--record-dir")
    parser.add_argument("--extension-record-dir")
    parser.add_argument("--parent-result")
    parser.add_argument("--progress", action="store_true")
    args = parser.parse_args()

    bound = load_and_validate_gate(args.gate)
    gate = bound["gate"]
    driver_relative = "agents/structural-basis/code/importance_d4_calibration.py"
    driver_sha = gate["source_hashes"][driver_relative]
    authorization_digest = None
    authorization_bound = None
    parent_result_digest = None
    record_directory = None
    initial_record_directory = None
    extension_record_directory = None
    if args.mode == "production":
        if not args.authorization:
            raise SystemExit("production mode requires a separate authorization")
        if not args.record_dir:
            raise SystemExit("production mode requires --record-dir")
        authorization_bound = validate_authorization(
            args.authorization, bound["sha256"], driver_sha,
            args.record_dir)
        authorization_digest = authorization_bound["sha256"]
        record_directory = open_bound_directory(
            authorization_bound["raw"]["record_directory_binding"])
        open_directories.append(record_directory)
        validate_fresh_checkpoint_directory(
            record_directory, gate["schedule"]["chains"])
        if args.extension_record_dir or args.parent_result:
            raise SystemExit("production mode rejects extension-only arguments")
    elif args.mode == "extension":
        if not (args.authorization and args.record_dir and
                args.extension_record_dir and args.parent_result):
            raise SystemExit(
                "extension mode requires authorization, both record dirs, "
                "and parent result")
    elif (args.authorization or args.record_dir or
          args.extension_record_dir or args.parent_result):
        raise SystemExit("record/authorization arguments require a run mode")

    oracle_path = REPO_ROOT / REQUIRED_DATA_PATHS[0]
    vector_path = REPO_ROOT / REQUIRED_DATA_PATHS[1]
    weights_path = REPO_ROOT / REQUIRED_DATA_PATHS[2]
    oracle = load_exact_expectation_oracle(oracle_path)
    validate_analytic_zero_se_proofs(oracle)
    adapter = C10ImportanceDensity(vector_path, oracle_path)
    validate_adapter_provenance(adapter, gate)
    weights = load_stratum_weights(
        weights_path, gate["data_hashes"][REQUIRED_DATA_PATHS[2]],
        prefix="baseline_", j_scale_to_numerator=1)
    validate_weight_provenance(weights, oracle, gate)
    if args.mode == "preflight":
        records = []
        checkpoints = []
        analysis = None
        analysis_failure = None
        final_extra_hashes = {bound["path"]: inode_binding(bound)}
        status = "d4-calibration-preflight-only"
    elif args.mode == "smoke":
        records = run_smoke(adapter)
        checkpoints = []
        analysis = None
        analysis_failure = None
        final_extra_hashes = {bound["path"]: inode_binding(bound)}
        status = "d4-calibration-tiny-smoke-only"
    elif args.mode == "production":
        loaded = [run_fresh_initial_chain(
            adapter, spec, gate["schedule"], record_directory,
            bound["sha256"], driver_sha, authorization_bound, bound,
            progress=args.progress)
                  for spec in gate["schedule"]["chains"]]
        records = [item["record"] for item in loaded]
        checkpoints = [public_binding(item) for item in loaded]
        analysis, analysis_failure = capture_analysis(
            records, oracle, weights, gate["schedule"], adapter=adapter)
        status = ("d4-stratified-calibration-pass" if
                  analysis is not None and analysis["gates_passed"]
                  else "d4-stratified-calibration-rejected")
        final_extra_hashes = {
            bound["path"]: inode_binding(bound),
            authorization_bound["path"]: inode_binding(authorization_bound),
            record_directory["path"]:
                directory_inode_binding(record_directory),
            **{item["path"]: inode_binding(item) for item in loaded},
        }
    else:
        parent = load_parent_result(
            args.parent_result, bound["sha256"], driver_sha,
            gate["schedule"])
        authorization_bound = validate_extension_authorization(
            args.authorization, bound["sha256"], driver_sha,
            parent["sha256"], args.extension_record_dir)
        authorization_digest = authorization_bound["sha256"]
        parent_result_digest = parent["sha256"]
        extension_record_directory = open_bound_directory(
            authorization_bound["raw"][
                "extension_record_directory_binding"])
        open_directories.append(extension_record_directory)
        validate_fresh_checkpoint_directory(
            extension_record_directory, gate["schedule"]["chains"],
            extension=True)
        _, initial_record_directory = validate_parent_checkpoint_manifest(
            parent, args.record_dir, gate["schedule"])
        open_directories.append(initial_record_directory)
        initial_loaded = [load_chain_checkpoint(
            chain_checkpoint_path(initial_record_directory["path"], spec), spec,
            bound["sha256"], driver_sha,
            parent["raw"]["authorization_sha256"], gate["schedule"],
            adapter=adapter, directory_handle=initial_record_directory)
                          for spec in gate["schedule"]["chains"]]
        initial_records = [item["record"] for item in initial_loaded]
        initial_checkpoints = [
            public_binding(item) for item in initial_loaded]
        if (parent["raw"]["records"] != initial_records or
                parent["raw"]["record_checkpoints"] != initial_checkpoints):
            raise ValueError(
                "parent result records do not equal reopened checkpoints")
        initial_analysis = analyze_records(
            initial_records, oracle, weights, gate["schedule"],
            adapter=adapter, do_jackknife=True)
        if not initial_analysis["extension_authorized"]:
            raise ValueError(
                "independent reconstruction does not authorize extension")
        extended_loaded = [run_fresh_extended_chain(
            adapter, initial, spec, gate["schedule"],
            extension_record_directory, bound["sha256"], driver_sha,
            authorization_bound, parent, bound,
            progress=args.progress)
                           for initial, spec in zip(
                               initial_loaded, gate["schedule"]["chains"])]
        records = [item["record"] for item in extended_loaded]
        checkpoints = [public_binding(item) for item in extended_loaded]
        analysis, analysis_failure = capture_analysis(
            records, oracle, weights, extended_schedule(gate["schedule"]),
            adapter=adapter)
        status = ("d4-stratified-calibration-extension-pass"
                  if analysis is not None and analysis["gates_passed"] else
                  "d4-stratified-calibration-extension-rejected")
        final_extra_hashes = {
            bound["path"]: inode_binding(bound),
            authorization_bound["path"]: inode_binding(authorization_bound),
            parent["path"]: inode_binding(parent),
            initial_record_directory["path"]:
                directory_inode_binding(initial_record_directory),
            extension_record_directory["path"]:
                directory_inode_binding(extension_record_directory),
            **{item["path"]: inode_binding(item) for item in initial_loaded},
            **{item["path"]: inode_binding(item) for item in extended_loaded},
        }
    wall_seconds = time.perf_counter() - run_started
    peak_rss_kib = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    validate_run_metrics(float_hex(wall_seconds), peak_rss_kib)
    payload = {
        "status": status,
        "rigorous": False,
        "theorem_ready": False,
        "mode": args.mode,
        "gate_path": str(Path(args.gate)),
        "gate_sha256": bound["sha256"],
        "driver_sha256": driver_sha,
        "authorization_sha256": authorization_digest,
        "parent_result_sha256": parent_result_digest,
        "gate_binding": public_binding(bound),
        "authorization_binding": (None if authorization_bound is None else
                                  public_binding(authorization_bound)),
        "parent_result_binding": (None if args.mode != "extension" else
                                  public_binding(parent)),
        "wall_seconds": float_hex(wall_seconds),
        "peak_rss_kib": peak_rss_kib,
        "float_encoding": FLOAT_ENCODING,
        "conventions": gate["conventions"],
        "schedule": (tiny_smoke_schedule() if args.mode == "smoke" else
                     extended_schedule(gate["schedule"])
                     if args.mode == "extension" else gate["schedule"]),
        "records": records,
        "record_checkpoints": checkpoints,
        "analysis": analysis,
        "analysis_failure": analysis_failure,
        "fresh_exact_reconstruction_required": True,
    }
    digest = write_new_result(
        args.output, payload, gate, extra_hashes=final_extra_hashes)
    print(json.dumps({"status": status, "output_sha256": digest,
                      "record_count": len(records)}, sort_keys=True))
    if args.mode in ("production", "extension") and (
            analysis is None or not analysis["gates_passed"]):
        raise SystemExit("D4 calibration failed one or more frozen gates")


def main():
    open_directories = []
    try:
        return _main(open_directories)
    finally:
        for directory in reversed(open_directories):
            close_bound_directory(directory)


if __name__ == "__main__":
    main()
