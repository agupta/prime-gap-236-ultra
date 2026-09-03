#!/usr/bin/env python3
"""Emit one explicit canonical 272-label H6-line vector, without integration.

The caller must supply a reduced canonical rational line coordinate.  This
emitter is deliberately separate from discovery: it never selects ``s`` and
never reads a form result.  Publication uses a held O_EXCL inode and rebinds
every input byte before returning.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path


MANIFEST_SHA = "5ab604c0b0c262da61b024bd28db672b31912f50c0c125988e4ad7fccc34cd6a"
DIRECTION_SHA = "a716e6a8da809c7363c6fc3773dd453db534a886742654541dc1b2a7c1940b81"
SOURCE_SHA = "719c656e6e45388273b4c27f51f7a18b33e9ed1abb5f883e6fcc5de5d6d64a87"
BANDS_SHA = "29d38a9e7ca7a352560c0a01813f2dfd2f477ec8cb829c433cce18d8229d31e9"
RECOVERY_SHA = "6411f11d218e66aa8c60d22daf0513e3e4840ebd74bd54c037761e3d7af56a43"
GENERATOR_SHA = "4222d304f72a89c3c37e1a4948c5164039e8050df3c6af93859a4288033fd196"


class EmitError(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise EmitError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def strict_json(raw, description):
    def pairs(items):
        result = {}
        for key, value in items:
            require(type(key) is str and key not in result,
                    f"{description}: duplicate/non-string key")
            result[key] = value
        return result

    def constant(value):
        raise EmitError(f"{description}: nonfinite {value}")

    try:
        result = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    except (json.JSONDecodeError, UnicodeError, ValueError) as exc:
        raise EmitError(f"{description}: malformed JSON: {exc}") from exc
    require(type(result) is dict, f"{description}: expected object")
    return result


def rational(value, description):
    require(type(value) is str and value and value == value.strip(),
            f"{description}: expected rational string")
    try:
        answer = Fraction(value)
    except Exception as exc:
        raise EmitError(f"{description}: malformed rational") from exc
    return answer


def canonical_s(value):
    require(type(value) is str and 0 < len(value) <= 1000,
            "s must be a bounded string")
    answer = rational(value, "line coordinate s")
    require(str(answer) == value, "s is not a canonical reduced rational")
    require(answer != 0, "s=0 is not a candidate displacement")
    require(answer.numerator.bit_length() <= 4096 and
            answer.denominator.bit_length() <= 4096,
            "s exceeds the 4096-bit bound")
    return answer


def label(value, description):
    require(type(value) is list and len(value) == 2 and
            type(value[0]) is int and value[0] >= 0 and
            type(value[1]) is list and
            all(type(x) is int and x >= 2 for x in value[1]) and
            tuple(value[1]) == tuple(sorted(value[1], reverse=True)) and
            value[0] + sum(value[1]) <= 12,
            f"{description}: noncanonical label")
    return value[0], tuple(value[1])


def decimal100(value):
    with localcontext() as context:
        context.prec = 100
        rounded = Decimal(value.numerator) / Decimal(value.denominator)
    return Fraction(str(rounded))


def read_pinned(path, expected_sha, description):
    path = Path(path).resolve()
    raw = path.read_bytes()
    require(len(raw) <= 20_000_000, f"{description}: exceeds 20 MB")
    require(sha(raw) == expected_sha, f"{description}: SHA mismatch")
    return path, raw, strict_json(raw, description)


def build_vector(manifest, direction, source, bands, recovery, s, self_sha):
    require(manifest.get("status") == "h6-sparse-scalar-line-package" and
            manifest.get("rigorous") is False and
            manifest.get("finite_form_value_claimed") is False and
            manifest.get("k") == 48, "manifest status")
    provenance = manifest.get("provenance")
    require(type(provenance) is dict and
            provenance.get("source_sha256") == SOURCE_SHA and
            provenance.get("bands_sha256") == BANDS_SHA and
            provenance.get("recovery_sha256") == RECOVERY_SHA and
            provenance.get("generator_sha256") == GENERATOR_SHA,
            "manifest provenance")
    entries = [x for x in manifest.get("artifacts", [])
               if type(x) is dict and x.get("sha256") == DIRECTION_SHA and
               x.get("kind") == "h6-sparse-self-form-direction"]
    require(len(entries) == 1, "manifest direction binding")

    require(source.get("k") == 48 and source.get("degree") == 12 and
            source.get("basis_dimension") == 272, "source dimensions")
    labels = [label(x, f"source basis[{i}]")
              for i, x in enumerate(source.get("basis", []))]
    source_vector = [rational(x, f"source vector[{i}]")
                     for i, x in enumerate(source.get("rational_vector", []))]
    require(len(labels) == len(source_vector) == len(set(labels)) == 272,
            "source basis/vector")
    require(bands.get("source_sha256") == SOURCE_SHA and
            bands.get("compressed_basis_dimension") == 20 and
            bands.get("expanded_term_count") == 272, "bands metadata")

    blocks, theta_source = [], []
    for i, item in enumerate(bands.get("core", [])):
        item_label = label(item.get("label"), f"core[{i}]")
        blocks.append({item_label: Fraction(1)})
        theta_source.append(rational(item.get("coefficient"),
                                     f"core[{i}] coefficient"))
    require(type(bands.get("bands")) is dict and
            set(bands["bands"]) == {str(x) for x in range(5, 13)},
            "band degree set")
    for degree in range(5, 13):
        block = {}
        for i, item in enumerate(bands["bands"][str(degree)]):
            item_label = label(item.get("label"), f"H{degree}[{i}]")
            require(item_label not in block, f"duplicate H{degree} label")
            block[item_label] = rational(item.get("coefficient"),
                                         f"H{degree}[{i}] coefficient")
        blocks.append(block)
        theta_source.append(Fraction(1))
    require(len(blocks) == 20, "compressed dimension")
    owner, weight = {}, {}
    for coordinate, block in enumerate(blocks):
        for item_label, item_weight in block.items():
            require(item_label not in owner, "multiple compressed owners")
            owner[item_label], weight[item_label] = coordinate, item_weight
    require(set(owner) == set(labels), "band partition")
    require([weight[x]*theta_source[owner[x]] for x in labels] == source_vector,
            "unrounded source reconstruction")

    require(recovery.get("status") ==
            "byte-pinned-recovered-degree-band-gradient-discovery" and
            recovery.get("rigorous") is False and recovery.get("complete") is True and
            recovery.get("source_sha256") == SOURCE_SHA and
            recovery.get("bands_sha256") == BANDS_SHA and
            recovery.get("decimal_dps") == 100, "recovery status")
    theta = [rational(x, f"theta[{i}]")
             for i, x in enumerate(recovery.get("theta", []))]
    require(theta == [decimal100(x) for x in theta_source],
            "serialized Decimal100 base")

    require(direction.get("status") == "h6-sparse-self-form-direction" and
            direction.get("rigorous") is False and direction.get("k") == 48 and
            direction.get("basis_dimension") == 11 and
            direction.get("provenance", {}).get("generator_sha256") ==
            GENERATOR_SHA, "direction status/provenance")
    h6_labels = list(blocks[13])
    h6_weights = [blocks[13][x] for x in h6_labels]
    observed_labels = [label(x, f"direction basis[{i}]")
                       for i, x in enumerate(direction.get("basis", []))]
    observed_weights = [rational(x, f"direction vector[{i}]")
                        for i, x in enumerate(direction.get("rational_vector", []))]
    require(observed_labels == h6_labels and observed_weights == h6_weights,
            "direction is not literal H6")

    base = [weight[x]*theta[owner[x]] for x in labels]
    displacement = [weight[x] if owner[x] == 13 else Fraction(0) for x in labels]
    vector = [x+s*y for x, y in zip(base, displacement)]
    require(any(vector) and len(vector) == 272, "emitted vector")
    changed = [i for i, x in enumerate(displacement) if x]
    require(len(changed) == 11 and all((vector[i]-base[i])/base[i] == s
                                      for i in changed),
            "H6 displacement identity")
    require(all(vector[i] == base[i] for i in range(272) if i not in changed),
            "off-H6 coefficient changed")

    return {
        "status": "h6-line-explicit-fixed-vector-candidate",
        "rigorous": False,
        "theorem_ready": False,
        "fresh_exact_dyadic_evaluation_required": True,
        "finite_form_value_claimed": False,
        "k": 48,
        "degree": 12,
        "basis_dimension": 272,
        "basis": [[a, list(parts)] for a, parts in labels],
        "rational_vector": [str(x) for x in vector],
        "line": {
            "coordinate_s": str(s),
            "base": "serialized Decimal100 action base theta",
            "direction": "literal +H6=e_13 compressed band",
            "H12_gauge_coordinate": "1",
            "changed_expanded_coordinate_count": 11,
            "max_expanded_relative_change": str(abs(s)),
        },
        "provenance": {
            "manifest_sha256": MANIFEST_SHA,
            "direction_sha256": DIRECTION_SHA,
            "source_sha256": SOURCE_SHA,
            "bands_sha256": BANDS_SHA,
            "recovery_sha256": RECOVERY_SHA,
            "generator_sha256": GENERATOR_SHA,
            "emitter_sha256": self_sha,
        },
        "checker_compatibility": {
            "driver": "verify/check_c10_d12_fixed_vector_dyadic.py",
            "complete_no_ones_D12_basis": True,
            "coefficient_format": "canonical Fraction strings",
        },
    }


def publish_owned(path, payload, trusted, test_hook=None):
    """Publish via one held O_EXCL inode; never rename/unlink a pathname."""
    path = Path(path).resolve()
    require(path not in trusted, "output aliases a trusted input")
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_CREAT | os.O_EXCL | os.O_RDWR
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        require(stat.S_ISREG(os.fstat(descriptor).st_mode), "output is not regular")
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            require(written > 0, "short output write")
            offset += written
        os.fsync(descriptor)
        if test_hook is not None:
            test_hook(path, descriptor)
        fd_stat = os.fstat(descriptor)
        path_stat = os.stat(path, follow_symlinks=False)
        require((fd_stat.st_dev, fd_stat.st_ino) ==
                (path_stat.st_dev, path_stat.st_ino), "output inode ownership changed")
        os.lseek(descriptor, 0, os.SEEK_SET)
        observed = b""
        while True:
            block = os.read(descriptor, 1 << 20)
            if not block:
                break
            observed += block
        require(observed == payload == path.read_bytes(), "output bytes changed")
        for trusted_path, raw in trusted.items():
            require(trusted_path.read_bytes() == raw,
                    f"trusted byte changed: {trusted_path}")
    except Exception as exc:
        rejection = (json.dumps({"status": "REJECTED", "error": str(exc)},
                                sort_keys=True) + "\n").encode()
        # Only the still-held owned descriptor is modified.  A foreign inode
        # installed at the pathname by a race is never renamed or unlinked.
        try:
            os.ftruncate(descriptor, 0)
            os.lseek(descriptor, 0, os.SEEK_SET)
            os.write(descriptor, rejection)
            os.fsync(descriptor)
        except Exception:
            pass
        raise
    finally:
        os.close(descriptor)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--direction", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--bands", required=True)
    parser.add_argument("--recovery", required=True)
    parser.add_argument("--s", required=True,
                        help="canonical reduced rational, e.g. 7/100")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    specs = {
        "manifest": (args.manifest, MANIFEST_SHA),
        "direction": (args.direction, DIRECTION_SHA),
        "source": (args.source, SOURCE_SHA),
        "bands": (args.bands, BANDS_SHA),
        "recovery": (args.recovery, RECOVERY_SHA),
    }
    loaded, trusted = {}, {}
    for name, (path_text, expected) in specs.items():
        path, raw, parsed = read_pinned(path_text, expected, name)
        require(path not in trusted, "trusted input path alias")
        trusted[path] = raw
        loaded[name] = parsed
    self_path = Path(__file__).resolve()
    self_raw = self_path.read_bytes()
    trusted[self_path] = self_raw
    s = canonical_s(args.s)
    candidate = build_vector(
        loaded["manifest"], loaded["direction"], loaded["source"],
        loaded["bands"], loaded["recovery"], s, sha(self_raw))
    payload = (json.dumps(candidate, indent=2) + "\n").encode()
    publish_owned(args.output, payload, trusted)
    print(json.dumps({
        "status": candidate["status"], "line_coordinate_s": str(s),
        "output_sha256": sha(payload), "theorem_ready": False,
    }, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (EmitError, OSError, ValueError, ZeroDivisionError) as exc:
        raise SystemExit(f"EMIT FAILED: {exc}")
