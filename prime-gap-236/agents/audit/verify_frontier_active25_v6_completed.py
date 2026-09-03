#!/usr/bin/env python3
"""Fresh exact reconstruction of the completed active25 D16 v6 pencil.

This is deliberately not a consumer of the v6 producer or assembler Python
APIs.  In one isolated process it pins the completed leaf set, reconstructs
all 26 inner/shell crosses from the frozen low-level exact core, independently
reconstructs the four ordered shell tables, and contracts the candidate's
particular rational vector against the fresh forms.

The only production entry is an isolated command-line capability closed over
an unexported token.  Importing this file exposes pure validation helpers for
hostile tests, but cannot invoke the long reconstruction.
"""

from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation, localcontext
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys


if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

RAW_FILE = Path(__file__).absolute()
FILE = RAW_FILE.resolve(strict=True)
REPO = FILE.parents[2]
FRONTIER = REPO / "agents/small-delta-frontier"
CORE = FRONTIER / "frontier_active25_inner_d16_tagged_shell.py"
SHELL = FRONTIER / "wide_shell_stratum_diagnostic.py"
OUTER = FRONTIER / "two_band_full_outer_constant.py"
CERTIFICATE = FRONTIER / "bv_aquarter_B16_vector_exact.json"
RADIAL = FRONTIER / "bv_D16_radial_two_amplitudes_exact.json"
ANALYTIC = REPO / (
    "agents/audit/results/"
    "wide_c722_nonuniform_active25_tail_analytic_audit.json")
EXACT_INTEGRATOR = REPO / "agents/exact-integrator/src/exact_integrator.py"
STRATUM_INTEGRATOR = REPO / "agents/exact-integrator/src/stratum_integrator.py"
GROUPED = REPO / "agents/exact-integrator/grouped_fixed_vector.py"
VOLUME_ANALYTIC = REPO / (
    "agents/audit/results/wide_c722_volume_ramp_analytic_audit.json")
DESIGN = REPO / (
    "agents/audit/"
    "FRONTIER-ACTIVE25-INDEPENDENT-ARITHMETIC-RECONSTRUCTION-DESIGN.md")
PRODUCER = FRONTIER / "frontier_active25_inner_d16_staged_v6.py"
ASSEMBLER = FRONTIER / "assemble_frontier_active25_inner_d16_v6.py"
PRODUCER_TESTS = FRONTIER / "test_frontier_active25_inner_d16_staged_v6.py"
ASSEMBLER_TESTS = FRONTIER / "test_assemble_frontier_active25_inner_d16_v6.py"
GATE = FRONTIER / (
    "results/frontier_active25_innerD16_tagged_shell_authorized_gate_v6.json")
V6_SPEC = FRONTIER / "FRONTIER-ACTIVE25-INNER-D16-STAGED-V6-PRELAUNCH.md"
UNGROUPED_ORACLE = FRONTIER / (
    "results/"
    "frontier_active25_innerD16_shell_cross_r10_h10_ungrouped_oracle.json")
DIRECT_ORACLE = FRONTIER / (
    "results/frontier_active25_innerD16_shell_cross_r10_h10_direct_v2.json")
GROUPED_AUDITOR = REPO / "agents/audit/verify_frontier_active25_grouped_prelaunch.py"
GROUPED_AUDIT_RESULT = REPO / (
    "agents/audit/results/frontier_active25_grouped_prelaunch_v2_audit.json")
V6_PRELAUNCH_REPORT = REPO / (
    "agents/audit/FRONTIER-ACTIVE25-STAGED-V6-PRELAUNCH-AUDIT.md")

STATIC_PINS = {
    CORE: "1393a2dd29e5660f10e632b19b6b5eeafe9363bf79b2cd4a8254049d1f9c669a",
    SHELL: "dbbf990caf2c1e6bc418d525d4becdaedc82af54eec457e8eb5578da29555cc5",
    OUTER: "75637298284a40be523621ebe1fcdc85bda59dcac42514fb8b50ffd8b460259d",
    CERTIFICATE: "59715ddffa483c696c035634a81c3cc8ffe882e9d6eaceec74bea23996b72d62",
    RADIAL: "33fe5d555e736fe5ea3826d569477414fadd2d8a9defc2eaa35718a4f06f82ca",
    ANALYTIC: "111a48a23dbf8bf3fdb058f30e6bc412d2eb3cd605557772d6f34056974b2bda",
    EXACT_INTEGRATOR: "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52",
    STRATUM_INTEGRATOR: "0566f77860b0b61ce0ed342b5bb3a4743990725099d8b0cd6e685efad3c7394f",
    GROUPED: "47167e92a0f346e969706dc282ccb2dfd4ac31a0a75b654938ffbe8423cf4a4a",
    VOLUME_ANALYTIC: "88b6e1aeb04bd2e7d8600e5f4a7bcca8726b5307b95e5a4e9337a20c8f7afa96",
    DESIGN: "976d7f43d52d45be33def40f376ebfe657af0fe3aba880f5c4de807a46b2693e",
    PRODUCER: "cfc4c3803312d5e41d87c27a753cd843da9534e85ea5e73d77079bf9ce8e284e",
    ASSEMBLER: "4b834f1a87b995a73a86d4e02505ddea599191467eccd69d43eed1d8f85b1356",
    PRODUCER_TESTS: "c5e45fe4a929fba55f29ae96f6e127bd8a680d8fa0ca01ca17dfa70f2b56d6ff",
    ASSEMBLER_TESTS: "e6ad2423ce9545e7a3f890b30f4e230bc49f4a15bfea04ed6f8d4340cdeb80ff",
    GATE: "7b37c89dd84b03301e3937c981b7c67ea6ce17e21bfd07a76199430bcfb16b80",
    V6_SPEC: "ed9fd5aacc27308f3dd2827d6517044be18057e937cdb99942420c3a3a1e308a",
    UNGROUPED_ORACLE: "f97e16231e47d028406a88702631457fb110fe1cf00fcb9a2a4ba71557dbc21c",
    DIRECT_ORACLE: "37b0d249a0fd17e823f154277bfabe162c3b80c72c344c97686312c7fac7e393",
    GROUPED_AUDITOR: "dba6064473a56cb16c99c4423efb0852b3990d0a7f39d027c1b5c1bdc0f4c622",
    GROUPED_AUDIT_RESULT: "bd93b52f3556b9d35edb2568b61c74362e4e156f5b607e6755f2ac7203a3c9a2",
    V6_PRELAUNCH_REPORT: "fa3d66547bc150df93150a0171da9835551aa9d725039c11eb8fabbf5326cbdb",
}

K = 48
ACTIVE = tuple(range(26))
LEDGER_LEAF = "ledger.json"
STAGE_LEAVES = tuple(f"common_r_{r:02d}.json" for r in ACTIVE)
MANIFEST_LEAF = "manifest.json"
ALLOWED_LEAVES = (LEDGER_LEAF, *STAGE_LEAVES, MANIFEST_LEAF)
PRODUCER_SHA256 = STATIC_PINS[PRODUCER]
ASSEMBLER_SHA256 = STATIC_PINS[ASSEMBLER]
GATE_SHA256 = STATIC_PINS[GATE]
CORE_SHA256 = STATIC_PINS[CORE]
MAX_CLOCK = 2**63 - 1
SHA_PATTERN = re.compile(r"^[0-9a-f]{64}$")
BOOT_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
    r"[0-9a-f]{4}-[0-9a-f]{12}$")
REJECTION_SENTINEL = b'{"status":"REJECTED"}\n'
PARAMETERS = {
    "A": ["-3/400", "1/4", "3121/12000"],
    "alpha": ["103/400", "3211/12000"],
    "delta": "361/50000",
    "epsilon": "3/400",
    "eta": ["97/400", "3031/12000"],
    "k": 48,
    "outer_schedule": [
        "597/5000", "633/5000", "669/5000", "141/1000",
        "737/5000", "773/5000", "1553/10000", "809/5000",
        "81/500", "3329/20000", "169/1000", "339/2000",
        "859/5000", "1737/10000", "219/1250", "881/5000",
        "441/2500", "887/5000", "891/5000", "179/1000",
        "449/2500", "1801/10000", "903/5000", "1811/10000",
        "363/2000", "363/2000",
    ],
}
EXPECTED_PRODUCER_DEPENDENCY = {
    "agents/audit/FRONTIER-ACTIVE25-GROUPED-PRELAUNCH-V2-AUDIT.md":
        "0c37f563d99191f0fbb4abc1c0ea5700ed6288ed9011d5edc691c91394cdc6a9",
    "agents/audit/FRONTIER-ACTIVE25-INDEPENDENT-ARITHMETIC-RECONSTRUCTION-DESIGN.md":
        "976d7f43d52d45be33def40f376ebfe657af0fe3aba880f5c4de807a46b2693e",
    "agents/audit/FRONTIER-ACTIVE25-STAGED-V3-DELTA-AUDIT.md":
        "a384a19332f87c7f8adbc17c7514ea2dc070514b5b477bd6d95d256203b40d14",
    "agents/audit/FRONTIER-ACTIVE25-STAGED-V4-PRELAUNCH-AUDIT.md":
        "11fe3b77f4d795b51d2042eef3f7254662bcf2c06f2cbc6668b8657ca06d328f",
    "agents/audit/FRONTIER-ACTIVE25-STAGED-V5-PRELAUNCH-AUDIT.md":
        "c60934e5c88c7d13160b488042c1a5446808201b57b356c4dbd6cb6404d77b99",
    "agents/audit/results/frontier_active25_grouped_prelaunch_v2_audit.json":
        "bd93b52f3556b9d35edb2568b61c74362e4e156f5b607e6755f2ac7203a3c9a2",
    "agents/audit/results/frontier_active25_v4_prelaunch_fail.json":
        "f020711a107dd36f724561e00f7d2c3fb9e7eb801a4e4f24e6e547cba6d782f5",
    "agents/audit/results/frontier_active25_v5_prelaunch_fail.json":
        "a173658fa20ada39cf2ca78e98ea92601be6e3709db9674826512c9e3a76c875",
    "agents/audit/results/wide_c722_nonuniform_active25_tail_analytic_audit.json":
        "111a48a23dbf8bf3fdb058f30e6bc412d2eb3cd605557772d6f34056974b2bda",
    "agents/audit/results/wide_c722_volume_ramp_analytic_audit.json":
        "88b6e1aeb04bd2e7d8600e5f4a7bcca8726b5307b95e5a4e9337a20c8f7afa96",
    "agents/audit/test_frontier_active25_v3_resume_wall_bypass.py":
        "13c5a756ca7b12e718fbd9b731bf62fae48b556d895cfd5b2caf1b344d3a2b67",
    "agents/audit/verify_frontier_active25_grouped_prelaunch.py":
        "dba6064473a56cb16c99c4423efb0852b3990d0a7f39d027c1b5c1bdc0f4c622",
    "agents/audit/verify_frontier_active25_v4_prelaunch_fail.py":
        "b1da2c8bc980154751da868d67c543bf281d2892113e259c6bf67a9ed8217588",
    "agents/audit/verify_frontier_active25_v5_prelaunch_fail.py":
        "127024d7117a130b21e4a93cb5f99ddbf59273e756802270feb52f0494c881a8",
    "agents/exact-integrator/grouped_fixed_vector.py":
        "47167e92a0f346e969706dc282ccb2dfd4ac31a0a75b654938ffbe8423cf4a4a",
    "agents/exact-integrator/src/exact_integrator.py":
        "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52",
    "agents/exact-integrator/src/stratum_integrator.py":
        "0566f77860b0b61ce0ed342b5bb3a4743990725099d8b0cd6e685efad3c7394f",
    "agents/small-delta-frontier/FRONTIER-ACTIVE25-INNER-D16-STAGED-V3-PRELAUNCH.md":
        "9649807e7dfb9111a188ae87b52b59ef0b3d3dab7b7ed20a0492bf8c2082c754",
    "agents/small-delta-frontier/FRONTIER-ACTIVE25-INNER-D16-STAGED-V4-PRELAUNCH.md":
        "66b4b7de36aecd3a2b4ecbf2ea1cb5e6192c2590d24d8a61bb7bc76a327f2edb",
    "agents/small-delta-frontier/FRONTIER-ACTIVE25-INNER-D16-STAGED-V5-PRELAUNCH.md":
        "ef365ff9031b7166df50dba71d484996d075574bf668dccef207bf18238daf07",
    "agents/small-delta-frontier/FRONTIER-ACTIVE25-INNER-D16-TAGGED-SHELL-PRELAUNCH-V2.md":
        "1a39e72a2d69ab0e64570ed05a9b0ea762b7f4223a4d88205d7a1f525230c721",
    "agents/small-delta-frontier/assemble_frontier_active25_inner_d16_v3.py":
        "c48feddb0cfd1a70ab7140813f4cf0037ae6f21374c229a38089198404079788",
    "agents/small-delta-frontier/assemble_frontier_active25_inner_d16_v4.py":
        "0b60c03e3743fe8003c9571423e79922a3ded08594d30894bee2461e980d0d85",
    "agents/small-delta-frontier/assemble_frontier_active25_inner_d16_v5.py":
        "6163402f5333c73ae011acbe64191ebff7dfac043f43d8e11c2ce635019807e9",
    "agents/small-delta-frontier/bv_D16_radial_two_amplitudes_exact.json":
        "33fe5d555e736fe5ea3826d569477414fadd2d8a9defc2eaa35718a4f06f82ca",
    "agents/small-delta-frontier/bv_aquarter_B16_vector_exact.json":
        "59715ddffa483c696c035634a81c3cc8ffe882e9d6eaceec74bea23996b72d62",
    "agents/small-delta-frontier/frontier_active25_inner_d16_staged_v2.py":
        "bb00675f722a843c0d87ef36e382aea812d6622c79da517e238b0146af9592dd",
    "agents/small-delta-frontier/frontier_active25_inner_d16_staged_v3.py":
        "79cbeb74b994e8d6bdd5f16e7d0f7d11aa148d6f9d6d4f32a12932854d62efd8",
    "agents/small-delta-frontier/frontier_active25_inner_d16_staged_v4.py":
        "7d5188ec18ef99ae22aeada193471a69c11cf15363aa26496ef8b3217387beef",
    "agents/small-delta-frontier/frontier_active25_inner_d16_staged_v5.py":
        "8bb0d5088e419d196b4aca732ec384804bf2918554cf001f372a3127e7f1f775",
    "agents/small-delta-frontier/frontier_active25_inner_d16_tagged_shell.py":
        "1393a2dd29e5660f10e632b19b6b5eeafe9363bf79b2cd4a8254049d1f9c669a",
    "agents/small-delta-frontier/results/frontier_active25_innerD16_tagged_shell_authorized_gate_v3.json":
        "19ab3d54c08fbd24d6b70ea9d946ca7272030bf20716da383f4bed285de411bb",
    "agents/small-delta-frontier/results/frontier_active25_innerD16_tagged_shell_authorized_gate_v4.json":
        "2dcfb44e4c9fbc5ec5f9b030f6565a35b06af478dff60c0805f96b44078c35fe",
    "agents/small-delta-frontier/results/frontier_active25_innerD16_tagged_shell_authorized_gate_v5.json":
        "b814507140740a821d67b6ccdec65eda3c30985075a19505d8bc485c84fa2420",
    "agents/small-delta-frontier/results/frontier_active25_innerD16_tagged_shell_authorized_gate_v6.json":
        "7b37c89dd84b03301e3937c981b7c67ea6ce17e21bfd07a76199430bcfb16b80",
    "agents/small-delta-frontier/results/frontier_active25_innerD16_tagged_shell_prelaunch_gate.json":
        "1642a5efcc4e2b304271fe3b785d439ce9b1ddb405855f56a7e62a1b4e61e6ac",
    "agents/small-delta-frontier/test_assemble_frontier_active25_inner_d16_v3.py":
        "f69f4dac10b610a5a08ec792b7e6bb4c74c4199d0edab78492dadd9703f8aa19",
    "agents/small-delta-frontier/test_assemble_frontier_active25_inner_d16_v4.py":
        "bb2a751b0459365641e188afc0f67fea27781e7a17a04538b5f35b3bae1140db",
    "agents/small-delta-frontier/test_assemble_frontier_active25_inner_d16_v5.py":
        "9d6a242a7e3b76d8cada75ee23f1ba24c7c100ff7a0d73de0d637e8166c09e74",
    "agents/small-delta-frontier/test_frontier_active25_inner_d16_staged_v2.py":
        "27fabdfa8e4f73820ca70af6189751d2e30acd7f699b580b9cd2cfdb625f10ed",
    "agents/small-delta-frontier/test_frontier_active25_inner_d16_staged_v3.py":
        "ab74ac22409f58e3bc7c3ae5a8c50a05c482c47cea69f6f30493adbeaa864e73",
    "agents/small-delta-frontier/test_frontier_active25_inner_d16_staged_v4.py":
        "4082c32c1358d564f6ed17743c3ccdc471813c67df5a5a3013acd9aa1e227ac0",
    "agents/small-delta-frontier/test_frontier_active25_inner_d16_staged_v5.py":
        "28b5b8d182fc0836a0bf905af4d7f9b907b403e35a9e61cae779428fb7f899bf",
    "agents/small-delta-frontier/two_band_full_outer_constant.py":
        "75637298284a40be523621ebe1fcdc85bda59dcac42514fb8b50ffd8b460259d",
    "agents/small-delta-frontier/verify_frontier_active25_prelaunch_gate.py":
        "552e6e92916c62179f56262f33fddfeda46d65463c7a13edb165892f0c15020b",
    "agents/small-delta-frontier/wide_shell_stratum_diagnostic.py":
        "dbbf990caf2c1e6bc418d525d4becdaedc82af54eec457e8eb5578da29555cc5",
}


class ReconstructionFailure(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise ReconstructionFailure(message)


def sha256_bytes(data):
    require(type(data) is bytes, "SHA input is not bytes")
    return hashlib.sha256(data).hexdigest()


def strict_sha(value, name):
    require(type(value) is str and SHA_PATTERN.fullmatch(value) is not None,
            f"{name} is not a canonical SHA-256")
    return value


def canonical_json(value):
    try:
        return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                           allow_nan=False) + "\n").encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise ReconstructionFailure("value is not canonical ASCII JSON") from error


def strict_json_bytes(data, name, *, canonical=False):
    require(type(data) is bytes, f"{name} is not bytes")

    def pairs(items):
        answer = {}
        for key, value in items:
            require(type(key) is str, f"non-string JSON key in {name}")
            require(key not in answer, f"duplicate JSON key in {name}: {key}")
            answer[key] = value
        return answer

    try:
        value = json.loads(
            data, object_pairs_hook=pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(
                ReconstructionFailure(f"nonfinite JSON token in {name}: {token}")))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ReconstructionFailure(f"{name} is not JSON") from error
    if canonical:
        require(canonical_json(value) == data, f"{name} is not canonical JSON")
    return value


def strict_fraction(raw, name):
    require(type(raw) is str, f"{name} is not a rational string")
    try:
        value = Q(raw)
    except (ValueError, ZeroDivisionError) as error:
        raise ReconstructionFailure(f"{name} is not rational") from error
    require(str(value) == raw, f"{name} is not a canonical rational")
    return value


def strict_nonnegative_int(value, name):
    require(type(value) is int and value >= 0, f"{name} is not nonnegative int")
    return value


def _identity(info):
    return (int(info.st_dev), int(info.st_ino), int(info.st_size),
            int(info.st_mtime_ns), int(info.st_ctime_ns), int(info.st_nlink))


def _read_descriptor(descriptor, maximum):
    require(type(maximum) is int and maximum >= 0, "invalid read bound")
    os.lseek(descriptor, 0, os.SEEK_SET)
    parts = []
    remaining = maximum + 1
    while remaining:
        block = os.read(descriptor, min(1_048_576, remaining))
        if not block:
            break
        parts.append(block)
        remaining -= len(block)
    data = b"".join(parts)
    require(len(data) <= maximum, "bounded file exceeds size limit")
    return data


def _open_file(path, maximum, *, expected_sha256=None):
    path = Path(path).absolute()
    try:
        raw_info = os.lstat(path)
    except OSError as error:
        raise ReconstructionFailure(f"cannot lstat file: {path}") from error
    require(stat.S_ISREG(raw_info.st_mode), f"not a regular nonsymlink file: {path}")
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise ReconstructionFailure(f"cannot open file: {path}") from error
    try:
        before = os.fstat(descriptor)
        data = _read_descriptor(descriptor, maximum)
        after = os.fstat(descriptor)
        identity = _identity(before)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1,
                f"file is not singly linked regular: {path}")
        require(identity == _identity(after) and len(data) == after.st_size,
                f"file changed while read: {path}")
        digest = sha256_bytes(data)
        if expected_sha256 is not None:
            require(digest == strict_sha(expected_sha256, f"expected SHA for {path}"),
                    f"file hash mismatch: {path}")
        return {
            "bytes": data, "descriptor": descriptor, "path": str(path),
            "device": identity[0], "inode": identity[1], "size": identity[2],
            "mtime_ns": identity[3], "ctime_ns": identity[4],
            "nlink": identity[5], "sha256": digest,
        }
    except Exception:
        os.close(descriptor)
        raise


def _open_directory(path):
    path = Path(path).absolute()
    try:
        raw_info = os.lstat(path)
    except OSError as error:
        raise ReconstructionFailure(f"cannot lstat directory: {path}") from error
    require(stat.S_ISDIR(raw_info.st_mode), f"not a nonsymlink directory: {path}")
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise ReconstructionFailure(f"cannot open directory: {path}") from error
    info = os.fstat(descriptor)
    require(stat.S_ISDIR(info.st_mode), f"directory descriptor changed type: {path}")
    return {"descriptor": descriptor, "path": str(path),
            "device": int(info.st_dev), "inode": int(info.st_ino),
            "mtime_ns": int(info.st_mtime_ns), "ctime_ns": int(info.st_ctime_ns)}


def _safe_leaf(leaf):
    require(type(leaf) is str and leaf not in ("", ".", "..") and
            "/" not in leaf and "\\" not in leaf and "\x00" not in leaf,
            "unsafe leaf name")
    return leaf


def _open_leaf(directory, leaf, maximum, *, expected_sha256=None):
    leaf = _safe_leaf(leaf)
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(leaf, flags, dir_fd=directory["descriptor"])
    except OSError as error:
        raise ReconstructionFailure(f"cannot open protected leaf {leaf}") from error
    try:
        before = os.fstat(descriptor)
        data = _read_descriptor(descriptor, maximum)
        after = os.fstat(descriptor)
        identity = _identity(before)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1,
                f"leaf is not singly linked regular: {leaf}")
        require(identity == _identity(after) and len(data) == after.st_size,
                f"leaf changed while read: {leaf}")
        digest = sha256_bytes(data)
        if expected_sha256 is not None:
            require(digest == strict_sha(expected_sha256, f"expected SHA for {leaf}"),
                    f"leaf hash mismatch: {leaf}")
        return {
            "bytes": data, "descriptor": descriptor, "leaf": leaf,
            "device": identity[0], "inode": identity[1], "size": identity[2],
            "mtime_ns": identity[3], "ctime_ns": identity[4],
            "nlink": identity[5], "sha256": digest,
        }
    except Exception:
        os.close(descriptor)
        raise


def require_exact_leaf_set(directory, expected):
    require(type(expected) in (set, frozenset, tuple, list) and
            all(type(leaf) is str for leaf in expected),
            "expected leaf set is malformed")
    if type(expected) in (tuple, list):
        require(len(expected) == len(set(expected)),
                "expected leaf inventory contains a duplicate")
    require(set(os.listdir(directory["descriptor"])) == set(expected),
            "directory leaf set mismatch")
    return True


def _snapshot_binding(snapshot, *, include_leaf=False):
    keys = ("leaf", "sha256", "device", "inode") if include_leaf else (
        "sha256", "device", "inode")
    return {key: snapshot[key] for key in keys}


def _rebind_file(snapshot):
    held = os.fstat(snapshot["descriptor"])
    expected = tuple(snapshot[key] for key in
                     ("device", "inode", "size", "mtime_ns", "ctime_ns", "nlink"))
    require(_identity(held) == expected and held.st_nlink == 1,
            f"held file changed: {snapshot['path']}")
    fresh = _open_file(snapshot["path"], snapshot["size"],
                       expected_sha256=snapshot["sha256"])
    try:
        observed = tuple(fresh[key] for key in
                         ("device", "inode", "size", "mtime_ns", "ctime_ns", "nlink"))
        require(observed == expected and fresh["bytes"] == snapshot["bytes"],
                f"file path rebound to different bytes: {snapshot['path']}")
    finally:
        os.close(fresh["descriptor"])


def _rebind_leaf(directory, snapshot):
    held = os.fstat(snapshot["descriptor"])
    expected = tuple(snapshot[key] for key in
                     ("device", "inode", "size", "mtime_ns", "ctime_ns", "nlink"))
    require(_identity(held) == expected and held.st_nlink == 1,
            f"held leaf changed: {snapshot['leaf']}")
    fresh = _open_leaf(directory, snapshot["leaf"], snapshot["size"],
                       expected_sha256=snapshot["sha256"])
    try:
        observed = tuple(fresh[key] for key in
                         ("device", "inode", "size", "mtime_ns", "ctime_ns", "nlink"))
        require(observed == expected and fresh["bytes"] == snapshot["bytes"],
                f"leaf path rebound: {snapshot['leaf']}")
    finally:
        os.close(fresh["descriptor"])


def _rebind_directory(directory, expected_leaves=None):
    held = os.fstat(directory["descriptor"])
    expected = (directory["device"], directory["inode"],
                directory["mtime_ns"], directory["ctime_ns"])
    require((int(held.st_dev), int(held.st_ino), int(held.st_mtime_ns),
             int(held.st_ctime_ns)) == expected,
            f"held directory changed: {directory['path']}")
    fresh = _open_directory(directory["path"])
    try:
        observed = (fresh["device"], fresh["inode"],
                    fresh["mtime_ns"], fresh["ctime_ns"])
        require(observed == expected, f"directory path rebound: {directory['path']}")
    finally:
        os.close(fresh["descriptor"])
    if expected_leaves is not None:
        try:
            require_exact_leaf_set(directory, expected_leaves)
        except ReconstructionFailure as error:
            raise ReconstructionFailure(
                f"directory leaf set changed: {directory['path']}") from error


def _close_snapshots(values):
    for value in values:
        if type(value) is dict:
            descriptor = value.get("descriptor")
            if type(descriptor) is int:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
                value["descriptor"] = None


require(not stat.S_ISLNK(os.lstat(RAW_FILE).st_mode),
        "checker must not be launched through a symlink")
_SELF = _open_file(FILE, 4_000_000)


def _bind_startup_self(expected_sha256):
    expected_sha256 = strict_sha(expected_sha256, "expected checker self SHA")
    require(_SELF["sha256"] == expected_sha256,
            "checker self SHA does not match external pin")
    _rebind_file(_SELF)
    return _SELF["bytes"]


def _strict_keys(value, keys, name):
    require(type(value) is dict and set(value) == set(keys),
            f"{name} schema mismatch")
    return value


def _strict_binding(value, name, *, path=False, leaf=False):
    keys = {"sha256", "device", "inode"}
    if path:
        keys.add("path")
    if leaf:
        keys.add("leaf")
    _strict_keys(value, keys, f"{name} binding")
    strict_sha(value["sha256"], f"{name} binding SHA")
    strict_nonnegative_int(value["device"], f"{name} device")
    strict_nonnegative_int(value["inode"], f"{name} inode")
    if path:
        require(type(value["path"]) is str and value["path"],
                f"{name} path is malformed")
    if leaf:
        _safe_leaf(value["leaf"])
    return value


def _strict_dependency_record(value):
    require(type(value) is dict and len(value) == 46,
            "producer transitive dependency inventory is not exactly 46 files")
    require(value == EXPECTED_PRODUCER_DEPENDENCY,
            "producer dependency map differs from frozen 46-file closure")
    for relative, digest in value.items():
        require(type(relative) is str and relative == PurePosixPath(relative).as_posix(),
                "dependency path is not canonical POSIX")
        pieces = PurePosixPath(relative).parts
        require(pieces and not PurePosixPath(relative).is_absolute() and
                all(piece not in ("", ".", "..") for piece in pieces),
                f"unsafe dependency path: {relative}")
        strict_sha(digest, f"dependency SHA {relative}")
    for path, expected in STATIC_PINS.items():
        try:
            relative = path.relative_to(REPO).as_posix()
        except ValueError:
            continue
        if path in (ASSEMBLER, ASSEMBLER_TESTS, PRODUCER, PRODUCER_TESTS,
                    V6_SPEC, V6_PRELAUNCH_REPORT):
            continue
        if relative in value:
            require(value[relative] == expected,
                    f"frozen dependency pin changed: {relative}")
    mandatory = {
        path.relative_to(REPO).as_posix(): digest
        for path, digest in STATIC_PINS.items()
        if path not in (ASSEMBLER, ASSEMBLER_TESTS, PRODUCER, PRODUCER_TESTS,
                        V6_SPEC, V6_PRELAUNCH_REPORT,
                        UNGROUPED_ORACLE, DIRECT_ORACLE)
    }
    # The representative oracle result is transitively bound by the old gate,
    # rather than listed as a direct producer dependency.  All remaining core
    # and audit closure leaves must be explicit in the ledger.
    for relative, digest in mandatory.items():
        require(value.get(relative) == digest,
                f"mandatory producer dependency absent or changed: {relative}")
    return value


def _strict_authorization(value):
    return _strict_binding(value, "authorization")


def _strict_authorization_file(value, record, snapshot):
    _strict_keys(value, {
        "driver_sha256", "format", "gate_sha256",
        "independent_prelaunch_report_sha256", "max_total_wall_seconds",
        "one_shot_attempt_authorized", "record_directory", "status",
        "theorem_ready", "workers",
    }, "root launch authorization")
    require(value["driver_sha256"] == PRODUCER_SHA256 and
            value["format"] ==
            "frontier-active25-inner-D16-v6-root-launch-authorization-v1" and
            value["gate_sha256"] == GATE_SHA256 and
            value["independent_prelaunch_report_sha256"] ==
            STATIC_PINS[V6_PRELAUNCH_REPORT] and
            value["max_total_wall_seconds"] == 14_400 and
            type(value["max_total_wall_seconds"]) is int and
            value["one_shot_attempt_authorized"] is True and
            value["record_directory"] == record["path"] and
            value["status"] ==
            "ROOT_AUTHORIZED_AFTER_INDEPENDENT_PRELAUNCH_PASS" and
            value["theorem_ready"] is False and
            value["workers"] == 1 and type(value["workers"]) is int,
            "root launch authorization identity mismatch")
    return _snapshot_binding(snapshot)


def _strict_ledger(value, directory, ledger_snapshot):
    _strict_keys(value, {
        "allowed_leaves", "authorization_binding", "boot_id",
        "deadline_monotonic_ns", "dependency_sha256", "driver_sha256",
        "format", "gate_sha256", "max_single_shard_nanoseconds",
        "max_total_wall_nanoseconds", "record_directory", "runtime_mode",
        "start_monotonic_ns", "status", "theorem_ready",
    }, "v6 ledger")
    authorization = _strict_authorization(value["authorization_binding"])
    start = strict_nonnegative_int(value["start_monotonic_ns"], "ledger start")
    deadline = strict_nonnegative_int(
        value["deadline_monotonic_ns"], "ledger deadline")
    duration = strict_nonnegative_int(
        value["max_total_wall_nanoseconds"], "ledger wall allowance")
    require(value["allowed_leaves"] == list(ALLOWED_LEAVES),
            "ledger leaf inventory mismatch")
    require(type(value["boot_id"]) is str and
            BOOT_PATTERN.fullmatch(value["boot_id"]) is not None,
            "ledger boot id is malformed")
    dependency = _strict_dependency_record(value["dependency_sha256"])
    record = value["record_directory"]
    _strict_keys(record, {"path", "device", "inode"}, "ledger directory")
    require(record == {key: directory[key] for key in ("path", "device", "inode")},
            "ledger record-directory binding mismatch")
    require(0 <= start <= deadline <= MAX_CLOCK and
            duration == 14_400 * 10**9 and deadline == start + duration and
            value["driver_sha256"] == PRODUCER_SHA256 and
            value["format"] ==
            "frontier-active25-inner-D16-immutable-ledger-v6-production" and
            value["gate_sha256"] == GATE_SHA256 and
            value["max_single_shard_nanoseconds"] == 600 * 10**9 and
            type(value["max_single_shard_nanoseconds"]) is int and
            value["runtime_mode"] == "production" and
            value["status"] == "initialized-one-shot" and
            value["theorem_ready"] is False,
            "ledger identity or time envelope mismatch")
    return authorization, dependency


def _strict_resource(value, ledger):
    _strict_keys(value, {"first", "minimum_separation_nanoseconds", "second"},
                 "resource observation")
    require(value["minimum_separation_nanoseconds"] == 5 * 10**9 and
            type(value["minimum_separation_nanoseconds"]) is int,
            "resource separation changed")
    intervals = []
    for label in ("first", "second"):
        row = value[label]
        _strict_keys(row, {"before_monotonic_ns", "after_monotonic_ns",
                           "mem_available_kib"}, f"resource {label}")
        before = strict_nonnegative_int(
            row["before_monotonic_ns"], f"resource {label} before")
        after = strict_nonnegative_int(
            row["after_monotonic_ns"], f"resource {label} after")
        memory = strict_nonnegative_int(
            row["mem_available_kib"], f"resource {label} memory")
        require(ledger["start_monotonic_ns"] <= before <= after <=
                ledger["deadline_monotonic_ns"] and memory >= 1_400_000,
                f"resource {label} violates frozen bounds")
        intervals.append((before, after))
    require(intervals[1][0] - intervals[0][1] >= 5 * 10**9,
            "resource readings are too close")
    return intervals


def _strict_shard_schema(value, expected_r=None):
    _strict_keys(value, {
        "common_r", "complete_common_r", "domain_counts", "faces",
        "geometric_group_count", "inner_48J", "inner_I",
        "inner_basis_dimension", "nonzero_group_count",
        "raw_J_cross_by_target_R",
    }, "v6 shard")
    r = value["common_r"]
    require(type(r) is int and r in ACTIVE and
            (expected_r is None or r == expected_r),
            "shard common count mismatch")
    require(value["complete_common_r"] is True,
            "shard is not complete")
    counts = value["domain_counts"]
    _strict_keys(counts, {"rh", "rl", "vh", "vl"}, "shard domain counts")
    for tag, count in counts.items():
        strict_nonnegative_int(count, f"shard domain count {tag}")
    strict_nonnegative_int(value["faces"], "shard faces")
    strict_nonnegative_int(value["geometric_group_count"],
                           "shard geometric groups")
    strict_nonnegative_int(value["nonzero_group_count"],
                           "shard nonzero groups")
    inner_b = strict_fraction(value["inner_48J"], "shard inner 48J")
    inner_i = strict_fraction(value["inner_I"], "shard inner I")
    require(inner_i > 0 and value["inner_basis_dimension"] == 307 and
            type(value["inner_basis_dimension"]) is int,
            "shard inner identity mismatch")
    raw = value["raw_J_cross_by_target_R"]
    require(type(raw) is list and len(raw) == K + 1,
            "shard cross vector dimension mismatch")
    vector = [strict_fraction(item, f"shard r={r} target={s}")
              for s, item in enumerate(raw)]
    allowed = {r} | ({r + 1} if r + 1 < len(ACTIVE) else set())
    require(all(value == 0 for s, value in enumerate(vector) if s not in allowed),
            "shard cross escaped active r/r+1 support")
    return r, vector, inner_i, inner_b


def _expected_shard(r, vector, counts, groups, nonzero, faces,
                    inner_i, inner_b, dimension):
    require(type(r) is int and r in ACTIVE and len(vector) == K + 1,
            "invalid fresh shard inputs")
    result = {
        "common_r": r,
        "complete_common_r": True,
        "domain_counts": dict(counts),
        "faces": faces,
        "geometric_group_count": groups,
        "inner_48J": str(inner_b),
        "inner_I": str(inner_i),
        "inner_basis_dimension": dimension,
        "nonzero_group_count": nonzero,
        "raw_J_cross_by_target_R": [str(value) for value in vector],
    }
    _strict_shard_schema(result, r)
    return result


def _strict_stage(value, r, ledger, ledger_binding, authorization,
                  dependency, expected_shard):
    _strict_keys(value, {
        "authorization_binding", "child_stdout_sha256", "dependency_sha256",
        "driver_sha256", "format", "gate_sha256", "ledger_binding",
        "parameters", "resource_observation", "runtime_mode", "shard",
        "status", "supervised_child_interval",
        "supervised_child_nanoseconds", "theorem_ready",
    }, f"stage {r}")
    interval = value["supervised_child_interval"]
    _strict_keys(interval, {"start_monotonic_ns", "end_monotonic_ns"},
                 f"stage {r} child interval")
    start = strict_nonnegative_int(interval["start_monotonic_ns"],
                                   f"stage {r} child start")
    end = strict_nonnegative_int(interval["end_monotonic_ns"],
                                 f"stage {r} child end")
    duration = strict_nonnegative_int(value["supervised_child_nanoseconds"],
                                      f"stage {r} duration")
    resource_intervals = _strict_resource(value["resource_observation"], ledger)
    require(ledger["start_monotonic_ns"] <= start < end <=
            ledger["deadline_monotonic_ns"] and duration == end - start and
            0 < duration <= ledger["max_single_shard_nanoseconds"] and
            resource_intervals[1][1] <= start,
            f"stage {r} child/resource timing mismatch")
    require(value["authorization_binding"] == authorization and
            value["dependency_sha256"] == dependency and
            value["driver_sha256"] == PRODUCER_SHA256 and
            value["format"] ==
            "frontier-active25-inner-D16-common-r-stage-v6-production" and
            value["gate_sha256"] == GATE_SHA256 and
            value["ledger_binding"] == ledger_binding and
            value["parameters"] == PARAMETERS and
            value["runtime_mode"] == "production" and
            value["status"] == "complete" and value["theorem_ready"] is False,
            f"stage {r} provenance identity mismatch")
    require(value["shard"] == expected_shard,
            f"stage {r} arithmetic differs from fresh reconstruction")
    _strict_shard_schema(value["shard"], r)
    child = {
        "arithmetic_core_sha256": CORE_SHA256,
        "authorization_binding": authorization,
        "dependency_sha256": dependency,
        "driver_sha256": PRODUCER_SHA256,
        "format":
            "frontier-active25-inner-D16-child-arithmetic-v6-production",
        "gate_sha256": GATE_SHA256,
        "ledger_binding": ledger_binding,
        "parameters": PARAMETERS,
        "shard": expected_shard,
        "status": "complete",
        "theorem_ready": False,
    }
    require(value["child_stdout_sha256"] == sha256_bytes(canonical_json(child)),
            f"stage {r} child stdout binding mismatch")
    return (resource_intervals[0][0], end, duration)


def _strict_manifest(value, directory, ledger, ledger_snapshot,
                     authorization, dependency, stage_snapshots,
                     stage_timing, fresh_merged):
    _strict_keys(value, {
        "authorization_binding", "complete",
        "cumulative_supervised_child_nanoseconds", "dependency_sha256",
        "dimension", "driver_sha256", "elapsed_monotonic_nanoseconds",
        "final_monotonic_ns", "format", "gate_sha256", "ledger_binding",
        "merged_raw_J_cross_by_target_R", "parameters", "record_directory",
        "runtime_mode", "stages", "status", "theorem_ready",
    }, "v6 manifest")
    final = strict_nonnegative_int(value["final_monotonic_ns"],
                                   "manifest final time")
    elapsed = strict_nonnegative_int(value["elapsed_monotonic_nanoseconds"],
                                     "manifest elapsed time")
    cumulative = strict_nonnegative_int(
        value["cumulative_supervised_child_nanoseconds"],
        "manifest cumulative child time")
    ledger_binding = _snapshot_binding(ledger_snapshot, include_leaf=True)
    require(value["authorization_binding"] == authorization and
            value["complete"] is True and
            value["dependency_sha256"] == dependency and
            value["dimension"] == 27 and type(value["dimension"]) is int and
            value["driver_sha256"] == PRODUCER_SHA256 and
            value["format"] ==
            "frontier-active25-inner-D16-stage-manifest-v6-production" and
            value["gate_sha256"] == GATE_SHA256 and
            value["ledger_binding"] == ledger_binding and
            value["parameters"] == PARAMETERS and
            value["record_directory"] == {
                key: directory[key] for key in ("path", "device", "inode")} and
            value["runtime_mode"] == "production" and
            value["status"] == "complete-one-shot" and
            value["theorem_ready"] is False,
            "manifest provenance identity mismatch")
    require(ledger["start_monotonic_ns"] <= final <=
            ledger["deadline_monotonic_ns"] and
            elapsed == final - ledger["start_monotonic_ns"] and
            0 < cumulative <= elapsed <= ledger["max_total_wall_nanoseconds"],
            "manifest time accounting mismatch")
    rows = value["stages"]
    require(type(rows) is list and len(rows) == len(ACTIVE),
            "manifest does not bind exactly 26 stages")
    seen = {(ledger_snapshot["device"], ledger_snapshot["inode"])}
    prior_end = ledger["start_monotonic_ns"]
    summed = 0
    for r, (row, snapshot, timing) in enumerate(
            zip(rows, stage_snapshots, stage_timing)):
        _strict_keys(row, {"common_r", "device", "inode", "leaf", "sha256"},
                     f"manifest stage row {r}")
        expected = {"common_r": r,
                    **_snapshot_binding(snapshot, include_leaf=True)}
        require(row == expected, f"manifest stage {r} binding mismatch")
        identity = (snapshot["device"], snapshot["inode"])
        require(identity not in seen, "ledger/stage inode alias")
        seen.add(identity)
        first_before, child_end, duration = timing
        require(first_before >= prior_end and child_end <= final,
                "stage intervals are not globally monotone")
        prior_end = child_end
        summed += duration
    require(summed == cumulative, "manifest cumulative child time mismatch")
    raw = value["merged_raw_J_cross_by_target_R"]
    require(type(raw) is list and len(raw) == K + 1,
            "manifest merged vector dimension mismatch")
    merged = [strict_fraction(item, f"manifest merged target {r}")
              for r, item in enumerate(raw)]
    require(merged == list(fresh_merged),
            "manifest merge differs from fresh reconstruction")
    require(all(value == 0 for value in merged[len(ACTIVE):]),
            "manifest has a nonzero target above active count 25")
    return seen


def assemble_fresh_forms(inner_i, inner_b, raw_cross, masses, shell_48j):
    """Pure Definition-5 assembly used by the checker and hostile fixtures."""
    require(isinstance(inner_i, Q) and isinstance(inner_b, Q),
            "inner blocks are not exact fractions")
    require(type(raw_cross) in (list, tuple) and len(raw_cross) == K + 1 and
            all(isinstance(value, Q) for value in raw_cross),
            "fresh cross vector malformed")
    require(type(masses) in (list, tuple) and len(masses) >= K + 1 and
            all(isinstance(value, Q) for value in masses),
            "fresh shell masses malformed")
    require(type(shell_48j) in (list, tuple) and len(shell_48j) == K + 1 and
            all(type(row) in (list, tuple) and len(row) == K + 1
                for row in shell_48j) and
            all(isinstance(value, Q) for row in shell_48j for value in row),
            "fresh shell matrix malformed")
    require(inner_i > 0 and all(masses[r] > 0 for r in ACTIVE) and
            all(masses[r] == 0 for r in range(len(ACTIVE), K + 1)),
            "fresh I diagonal support/positivity failed")
    require(all(raw_cross[r] == 0 for r in range(len(ACTIVE), K + 1)),
            "fresh cross has inactive-count tail")
    require(all(shell_48j[r][s] == shell_48j[s][r]
                for r in range(K + 1) for s in range(K + 1)),
            "fresh shell matrix is not symmetric")
    require(all(shell_48j[r][s] == 0
                for r in ACTIVE for s in ACTIVE if abs(r - s) > 1),
            "fresh active shell matrix is not tridiagonal")
    require(all(shell_48j[r][s] == 0
                for r in range(K + 1) for s in range(K + 1)
                if r >= len(ACTIVE) or s >= len(ACTIVE)),
            "fresh shell matrix has inactive-count support")
    a_diag = [inner_i, *(masses[r] for r in ACTIVE)]
    b_matrix = [[Q(0) for _ in range(27)] for _ in range(27)]
    b_matrix[0][0] = inner_b
    for r in ACTIVE:
        # The grouped result is raw J.  Apply k once; symmetry supplies the
        # second quadratic-form occurrence, so there is no polarization 2.
        mixed = Q(K) * raw_cross[r]
        b_matrix[0][r + 1] = mixed
        b_matrix[r + 1][0] = mixed
        for s in ACTIVE:
            b_matrix[r + 1][s + 1] = shell_48j[r][s]
    require(len(a_diag) == 27 and all(value > 0 for value in a_diag) and
            all(b_matrix[i][j] == b_matrix[j][i]
                for i in range(27) for j in range(27)),
            "fresh 27-dimensional forms failed")
    return a_diag, b_matrix


def exact_certificate(a_diag, b_matrix, vector):
    """Pure exact contraction; never consumes serialized scalar claims."""
    require(len(a_diag) == len(vector) == len(b_matrix) and
            all(len(row) == len(vector) for row in b_matrix) and
            all(isinstance(value, Q) for value in a_diag) and
            all(isinstance(value, Q) for value in vector) and
            all(isinstance(value, Q) for row in b_matrix for value in row),
            "certificate form/vector dimension mismatch")
    denominator = sum((a_diag[i] * vector[i] * vector[i]
                       for i in range(len(vector))), Q(0))
    numerator = sum((vector[i] * b_matrix[i][j] * vector[j]
                     for i in range(len(vector))
                     for j in range(len(vector))), Q(0))
    require(denominator > 0, "candidate has nonpositive exact denominator")
    return denominator, numerator, numerator - denominator


def require_exact_forms(candidate_a, candidate_b, fresh_a, fresh_b):
    require(candidate_a == list(fresh_a) and candidate_b == list(fresh_b),
            "candidate serialized forms differ from fresh forms")
    return True


def require_serialized_certificate(value, denominator, numerator, margin):
    """Match all exact scalar claims; useful for forged-margin fixtures."""
    expected = {
        "exact_rational_denominator": denominator,
        "exact_rational_numerator": numerator,
        "exact_quotient": numerator / denominator,
        "exact_margin": margin,
    }
    for key, exact in expected.items():
        require(strict_fraction(value[key], f"candidate {key}") == exact,
                f"candidate {key} differs from fresh contraction")
    return True


def _strict_finite_decimal(raw, name):
    require(type(raw) is str, f"{name} is not a decimal string")
    try:
        value = Decimal(raw)
    except InvalidOperation as error:
        raise ReconstructionFailure(f"{name} is not decimal") from error
    require(value.is_finite(), f"{name} is not finite")
    return value


def _strict_candidate(value, candidate_snapshot, record_directory,
                      ledger_snapshot, manifest_snapshot, authorization,
                      authorization_snapshot, producer_dependency,
                      stage_snapshots, fresh_a, fresh_b, fresh_shell_counts):
    _strict_keys(value, {
        "48J_matrix", "I_diagonal", "assembler_sha256",
        "authorization_binding", "complete_manifest_binding",
        "dependency_sha256", "dimension", "eigenvalue_optimality_rigorous",
        "exact_margin", "exact_quotient", "exact_rational_denominator",
        "exact_rational_numerator", "finite_space_crosses_one", "format",
        "independent_arithmetic_reconstruction", "ledger_binding",
        "parameters", "precision_discovery", "producer_driver_sha256",
        "rational_denominator_limit", "rational_vector",
        "serialized_stage_arithmetic_conditional", "shell_domain_counts",
        "stage_bindings", "status", "theorem_ready", "two_precision_gate",
    }, "v6 candidate")
    expected_candidate_dependency = dict(producer_dependency)
    expected_candidate_dependency[
        PRODUCER.relative_to(REPO).as_posix()] = PRODUCER_SHA256
    expected_candidate_dependency[
        PRODUCER_TESTS.relative_to(REPO).as_posix()] = STATIC_PINS[PRODUCER_TESTS]
    expected_candidate_dependency = dict(sorted(expected_candidate_dependency.items()))
    require(value["assembler_sha256"] == ASSEMBLER_SHA256 and
            value["dependency_sha256"] == expected_candidate_dependency and
            value["dimension"] == 27 and type(value["dimension"]) is int and
            value["eigenvalue_optimality_rigorous"] is False and
            value["independent_arithmetic_reconstruction"] is False and
            value["serialized_stage_arithmetic_conditional"] is True and
            value["producer_driver_sha256"] == PRODUCER_SHA256 and
            value["format"] ==
            "frontier-active25-inner-D16-conditional-pencil-v6" and
            value["parameters"] == PARAMETERS and
            value["rational_denominator_limit"] == 10**18 and
            type(value["rational_denominator_limit"]) is int and
            value["status"] == "CONDITIONAL_DISCOVERY_ONLY" and
            value["theorem_ready"] is False and
            value["two_precision_gate"] == {
                "precisions": [100, 160],
                "quotient_absolute_tolerance": "1e-70",
                "relative_residual_maximum": "1e-70",
            }, "candidate identity/conditional flags mismatch")
    ledger = _strict_binding(value["ledger_binding"], "candidate ledger", path=True)
    manifest = _strict_binding(value["complete_manifest_binding"],
                               "candidate manifest", path=True)
    candidate_authorization = _strict_binding(
        value["authorization_binding"], "candidate authorization", path=True)
    require({key: ledger[key] for key in ("sha256", "device", "inode")} ==
            _snapshot_binding(ledger_snapshot) and
            {key: manifest[key] for key in ("sha256", "device", "inode")} ==
            _snapshot_binding(manifest_snapshot) and
            {key: candidate_authorization[key]
             for key in ("sha256", "device", "inode")} == authorization and
            candidate_authorization["path"] == authorization_snapshot["path"] and
            Path(ledger["path"]).absolute() ==
            Path(record_directory["path"]) / LEDGER_LEAF and
            Path(manifest["path"]).absolute() ==
            Path(record_directory["path"]) / MANIFEST_LEAF,
            "candidate dynamic provenance binding mismatch")
    rows = value["stage_bindings"]
    require(type(rows) is list and len(rows) == len(ACTIVE),
            "candidate does not bind exactly 26 stages")
    for r, (row, snapshot) in enumerate(zip(rows, stage_snapshots)):
        _strict_binding(row, f"candidate stage {r}", leaf=True)
        require(row == _snapshot_binding(snapshot, include_leaf=True),
                f"candidate stage {r} binding mismatch")
    a_raw = value["I_diagonal"]
    b_raw = value["48J_matrix"]
    require(type(a_raw) is list and len(a_raw) == 27 and
            type(b_raw) is list and len(b_raw) == 27 and
            all(type(row) is list and len(row) == 27 for row in b_raw),
            "candidate matrix dimensions mismatch")
    candidate_a = [strict_fraction(raw, f"candidate I {i}")
                   for i, raw in enumerate(a_raw)]
    candidate_b = [[strict_fraction(raw, f"candidate 48J {i},{j}")
                    for j, raw in enumerate(row)]
                   for i, row in enumerate(b_raw)]
    require_exact_forms(candidate_a, candidate_b, fresh_a, fresh_b)
    vector_raw = value["rational_vector"]
    require(type(vector_raw) is list and len(vector_raw) == 27,
            "candidate rational vector dimension mismatch")
    vector = [strict_fraction(raw, f"candidate vector {i}")
              for i, raw in enumerate(vector_raw)]
    denominator, numerator, margin = exact_certificate(
        fresh_a, fresh_b, vector)
    require_serialized_certificate(value, denominator, numerator, margin)
    require(margin > 0 and value["finite_space_crosses_one"] is True,
            "candidate exact rational vector does not cross one")
    counts = value["shell_domain_counts"]
    _strict_keys(counts, {"hh", "hl", "ll"}, "candidate shell counts")
    require(counts == {key: fresh_shell_counts[key]
                       for key in ("hh", "hl", "ll")},
            "candidate shell domain counts differ from fresh traversal")
    solves = value["precision_discovery"]
    require(type(solves) is list and len(solves) == 2,
            "candidate precision discovery inventory mismatch")
    rayleighs = []
    for precision, solve in zip((100, 160), solves):
        _strict_keys(solve, {"precision", "eigenvalue", "rayleigh_quotient",
                             "relative_residual_bound", "jacobi_rotations",
                             "vector"}, "candidate discovery row")
        require(solve["precision"] == precision and
                type(solve["precision"]) is int and
                type(solve["jacobi_rotations"]) is int and
                solve["jacobi_rotations"] >= 0 and
                type(solve["vector"]) is list and len(solve["vector"]) == 27,
                "candidate discovery row shape mismatch")
        decimal_fields = [
            ("eigenvalue", solve["eigenvalue"]),
            ("rayleigh", solve["rayleigh_quotient"]),
            ("residual", solve["relative_residual_bound"]),
        ] + [(f"vector {i}", raw)
             for i, raw in enumerate(solve["vector"])]
        for label, raw in decimal_fields:
            _strict_finite_decimal(raw, f"candidate {precision} {label}")
        rayleighs.append(_strict_finite_decimal(
            solve["rayleigh_quotient"], f"candidate {precision} rayleigh"))
        residual = _strict_finite_decimal(
            solve["relative_residual_bound"],
            f"candidate {precision} residual")
        require(Decimal(0) <= residual <= Decimal("1e-70"),
                "candidate discovery residual exceeds conditional gate")
    with localcontext() as context:
        context.prec = 180
        require(abs(rayleighs[0] - rayleighs[1]) <= Decimal("1e-70"),
                "candidate discovery precisions disagree")
    return vector, denominator, numerator, margin


def ordered_shell_inclusion(hh, hl, lh, ll, *, factor=K):
    """Form HH-HL-LH+LL after validating the two ordered orientations."""
    matrices = (hh, hl, lh, ll)
    require(all(type(matrix) in (list, tuple) for matrix in matrices) and
            len(hh) > 0 and all(len(matrix) == len(hh) for matrix in matrices),
            "ordered shell matrix dimensions mismatch")
    n = len(hh)
    require(all(type(row) in (list, tuple) and len(row) == n
                for matrix in matrices for row in matrix) and
            all(isinstance(value, Q)
                for matrix in matrices for row in matrix for value in row),
            "ordered shell matrices are malformed")
    require(type(factor) is int and factor > 0,
            "shell factor is not a positive integer")
    require(all(lh[r][s] == hl[s][r] for r in range(n) for s in range(n)),
            "ordered LH is not transpose(HL)")
    raw = [[hh[r][s] - hl[r][s] - lh[r][s] + ll[r][s]
            for s in range(n)] for r in range(n)]
    scaled = [[Q(factor) * raw[r][s] for s in range(n)] for r in range(n)]
    return raw, scaled


def _snapshot_source_closure(producer_dependency):
    snapshots = {}
    requested = {
        REPO / relative: digest
        for relative, digest in producer_dependency.items()
    }
    requested.update(STATIC_PINS)
    for path, expected in sorted(requested.items(), key=lambda item: str(item[0])):
        absolute = Path(path).absolute()
        try:
            resolved = absolute.resolve(strict=True)
        except OSError as error:
            raise ReconstructionFailure(f"missing source-closure file: {absolute}") from error
        try:
            resolved.relative_to(REPO)
        except ValueError as error:
            raise ReconstructionFailure(f"source closure escapes repository: {resolved}") from error
        require(resolved == absolute, f"source closure path uses a symlink: {absolute}")
        snapshots[resolved] = _open_file(resolved, 32_000_000,
                                         expected_sha256=expected)
    return snapshots


def _rebind_source_closure(snapshots):
    for path in sorted(snapshots, key=str):
        _rebind_file(snapshots[path])


def _validate_declared_sources(dependency, snapshots, name):
    require(type(dependency) is dict, f"{name} dependency map is malformed")
    for relative, digest in dependency.items():
        path = (REPO / relative).absolute()
        require(path in snapshots and snapshots[path]["sha256"] == digest,
                f"{name} dependency is not in held source closure: {relative}")


def _validate_frozen_oracles(sources):
    oracle = strict_json_bytes(sources[UNGROUPED_ORACLE]["bytes"],
                               "ungrouped oracle", canonical=True)
    direct = strict_json_bytes(sources[DIRECT_ORACLE]["bytes"],
                               "direct grouped oracle", canonical=True)
    for value, mode, label in (
            (oracle, "ungrouped-four-branch-oracle", "ungrouped"),
            (direct, "direct-full-grouped", "direct")):
        require(value.get("common_r") == 10 and value.get("selected_h") == 10 and
                value.get("evaluation_mode") == mode and
                value.get("script_sha256") == CORE_SHA256 and
                value.get("rigorous_values") is True and
                value.get("complete_cross") is False and
                value.get("theorem_ready") is False and
                type(value.get("radial_cross_by_target_R")) is list and
                len(value["radial_cross_by_target_R"]) == K + 1,
                f"frozen {label} oracle identity mismatch")
        for r, raw in enumerate(value["radial_cross_by_target_R"]):
            strict_fraction(raw, f"{label} oracle target {r}")
    require(oracle["radial_cross_by_target_R"] ==
            direct["radial_cross_by_target_R"],
            "frozen true-ungrouped/direct oracle values disagree")
    audit = strict_json_bytes(sources[GROUPED_AUDIT_RESULT]["bytes"],
                              "grouped prelaunch audit", canonical=True)
    require(audit.get("artifact_checks", {}).get(
                "oracle_direct_exact_equal") is True and
            audit.get("low_k_literal_grouped_checks", {}).get(
                "all_exact_equal") is True and
            audit.get("definition5_and_shell_checks", {}).get("k") == K,
            "frozen formula-level grouped/oracle audit identity mismatch")


def _validate_analytic_artifact(sources):
    value = strict_json_bytes(sources[ANALYTIC]["bytes"],
                              "active25 analytic audit")
    parameters = value.get("parameters", {})
    require(value.get("status") == "AUDIT PASS" and
            value.get("schedule_id") == "nonuniform-outer-active25-tail-v4" and
            value.get("c1") == "0" and value.get("c2") == "0" and
            parameters.get("k") == K and
            parameters.get("epsilon") == PARAMETERS["epsilon"] and
            parameters.get("delta") == PARAMETERS["delta"] and
            parameters.get("A") == PARAMETERS["A"] and
            parameters.get("outer_final_plateau") ==
            PARAMETERS["outer_schedule"][-1] and
            parameters.get("outer_active") == list(ACTIVE) and
            parameters.get("outer_schedule_through_first_empty") ==
            PARAMETERS["outer_schedule"],
            "active25 analytic audit identity mismatch")


def _load_low_level_core(sources):
    """Load only the pinned low-level core after every source has been held."""
    # Reject a path/inode/byte change before any held local source is executed,
    # then rebind again immediately after the complete transitive import.
    _rebind_source_closure(sources)
    sys.dont_write_bytecode = True
    specification = importlib.util.spec_from_file_location(
        "independent_active25_low_level_core", CORE)
    require(specification is not None and specification.loader is not None,
            "cannot construct low-level core import")
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    require(Path(module.__file__).resolve(strict=True) == CORE,
            "wrong low-level core source loaded")
    expected_modules = {
        module: CORE,
        module.shell: SHELL,
        module.outer_core: OUTER,
        module.ei: EXACT_INTEGRATOR,
        module.shell.stratum_core: STRATUM_INTEGRATOR,
    }
    grouped_module = sys.modules.get(module.GroupedEvaluator.__module__)
    require(grouped_module is not None, "grouped evaluator module is missing")
    expected_modules[grouped_module] = GROUPED
    for imported, path in expected_modules.items():
        require(Path(imported.__file__).resolve(strict=True) == path,
                f"wrong imported local module for {path}")
    for imported in tuple(sys.modules.values()):
        raw = getattr(imported, "__file__", None)
        if type(raw) is not str:
            continue
        try:
            path = Path(raw).resolve(strict=True)
            path.relative_to(REPO)
        except (OSError, ValueError):
            continue
        require(path == FILE or path in sources,
                f"unbound local module imported: {path}")
        require("frontier_active25_inner_d16_staged" not in path.name and
                not path.name.startswith("assemble_frontier_active25_inner_d16"),
                f"forbidden producer/assembler module imported: {path}")
    require(module.K == K and module.parameter_record() == PARAMETERS and
            module.ETA1 == Q(PARAMETERS["eta"][0]) and
            module.ETA2 == Q(PARAMETERS["eta"][1]) and
            module.DELTA == Q(PARAMETERS["delta"]),
            "low-level core parameters changed")
    expected_core_pins = {
        path: STATIC_PINS[path]
        for path in (SHELL, OUTER, CERTIFICATE, RADIAL, ANALYTIC)
    }
    expected_shell_pins = {
        path: STATIC_PINS[path]
        for path in (EXACT_INTEGRATOR, STRATUM_INTEGRATOR, GROUPED,
                     VOLUME_ANALYTIC)
    }
    require(module.PINNED == expected_core_pins and
            module.shell.PINNED == expected_shell_pins,
            "low-level core declared pin set changed")
    _rebind_source_closure(sources)
    return module


def _parse_inner_coordinate(sources):
    """Independently parse the D16 coordinate and contract its 2x2 forms."""
    certificate = strict_json_bytes(sources[CERTIFICATE]["bytes"],
                                    "D16 certificate")
    radial = strict_json_bytes(sources[RADIAL]["bytes"], "D16 radial artifact")
    require(certificate.get("k") == K and certificate.get("degree") == 16 and
            certificate.get("integrator_sha256") ==
            STATIC_PINS[EXACT_INTEGRATOR],
            "D16 certificate identity mismatch")
    basis_raw = certificate.get("basis")
    vector_raw = certificate.get("rational_vector")
    require(type(basis_raw) is list and len(basis_raw) == 307 and
            type(vector_raw) is list and len(vector_raw) == 307,
            "D16 basis/vector dimension mismatch")
    basis = []
    for i, item in enumerate(basis_raw):
        require(type(item) is list and len(item) == 2 and
                type(item[0]) is int and item[0] >= 0 and
                type(item[1]) is list and
                all(type(part) is int and part > 0 for part in item[1]) and
                all(item[1][j] >= item[1][j + 1]
                    for j in range(len(item[1]) - 1)) and
                item[0] + sum(item[1]) <= 16,
                f"malformed D16 basis element {i}")
        basis.append((item[0], tuple(item[1])))
    vector = tuple(strict_fraction(raw, f"D16 vector {i}")
                   for i, raw in enumerate(vector_raw))
    require(len(set(basis)) == 307 and any(vector),
            "D16 basis is duplicated or vector is zero")
    require(radial.get("format") ==
            "direct-bv-radial-two-amplitude-exact-v1" and
            radial.get("k") == K and radial.get("basis_dimension") == 307 and
            radial.get("certificate_sha256") == STATIC_PINS[CERTIFICATE] and
            radial.get("integrator_sha256") == STATIC_PINS[EXACT_INTEGRATOR] and
            radial.get("R") == PARAMETERS["alpha"][0] and
            radial.get("V") == PARAMETERS["eta"][0],
            "D16 radial provenance mismatch")
    amplitudes_raw = radial.get("rational_amplitudes")
    require(type(amplitudes_raw) is list and len(amplitudes_raw) == 2,
            "D16 amplitude inventory mismatch")
    amplitudes = tuple(strict_fraction(raw, f"D16 amplitude {i}")
                       for i, raw in enumerate(amplitudes_raw))
    require(amplitudes[0] == 1, "D16 inner amplitude is not normalized")

    def matrix(field):
        raw = radial.get(field)
        require(type(raw) is list and len(raw) == 2 and
                all(type(row) is list and len(row) == 2 for row in raw),
                f"D16 {field} dimension mismatch")
        result = [[strict_fraction(raw[i][j], f"D16 {field} {i},{j}")
                   for j in range(2)] for i in range(2)]
        require(result[0][1] == result[1][0], f"D16 {field} is not symmetric")
        return result

    i_matrix = matrix("I_matrix")
    b_matrix = matrix("kJ_matrix")
    inner_i = sum((amplitudes[i] * i_matrix[i][j] * amplitudes[j]
                   for i in range(2) for j in range(2)), Q(0))
    inner_b = sum((amplitudes[i] * b_matrix[i][j] * amplitudes[j]
                   for i in range(2) for j in range(2)), Q(0))
    require(inner_i > 0 and
            strict_fraction(radial.get("exact_denominator"),
                            "radial exact denominator") == inner_i and
            strict_fraction(radial.get("exact_numerator"),
                            "radial exact numerator") == inner_b and
            strict_fraction(radial.get("exact_quotient"),
                            "radial exact quotient") == inner_b / inner_i and
            strict_fraction(radial.get("exact_margin"),
                            "radial exact margin") == inner_b - inner_i and
            radial.get("denominator_positive") is True and
            radial.get("margin_positive") is (inner_b > inner_i),
            "fresh D16 radial contraction mismatch")
    return tuple(basis), vector, amplitudes, inner_i, inner_b


def _construct_named_cross_inputs(core, basis, vector, amplitudes):
    schedule = tuple(Q(raw) for raw in PARAMETERS["outer_schedule"])
    delta = Q(PARAMETERS["delta"])
    eta1, eta2 = (Q(raw) for raw in PARAMETERS["eta"])
    alpha1, alpha2 = (Q(raw) for raw in PARAMETERS["alpha"])
    high = core.shell.ScheduledStratumSupport.make(
        K, alpha2, eta2, delta, schedule)
    low = core.shell.ScheduledStratumSupport.make(
        K, alpha1, eta2, delta, schedule)
    full_r = core.ei.OneStratumSupport(
        K, alpha1, delta, eta2, alpha1, alpha1, alpha1)
    full_v = core.ei.OneStratumSupport(
        K, eta1, delta, eta2, eta1, eta1, eta1)
    base_components = core.outer_core.components(basis, vector, K)
    one = (((), 0, 0, Q(1)),)
    named = {
        "R": (full_r, base_components),
        "V": (full_v, base_components),
        "H": (high, one),
        "L": (low, one),
    }
    catalog = (("rh", "R", "H"), ("rl", "R", "L"),
               ("vh", "V", "H"), ("vl", "V", "L"))
    inner_amplitude, outer_amplitude = amplitudes
    weights = {
        "rh": outer_amplitude,
        "rl": -outer_amplitude,
        "vh": inner_amplitude - outer_amplitude,
        "vl": -(inner_amplitude - outer_amplitude),
    }
    return named, catalog, weights, high, low


def _reconstruct_cross_expected(core, named, catalog, weights, r,
                                inner_i, inner_b):
    vector, counts, groups, nonzero, faces = core.grouped_weighted_cross(
        named, catalog, weights, Q(PARAMETERS["eta"][1]),
        common_strata=(r,), direct_full_left=("R", "V"), progress=False)
    require(type(vector) is list and len(vector) == K + 1 and
            all(isinstance(value, Q) for value in vector),
            f"fresh cross r={r} returned malformed vector")
    allowed = {r} | ({r + 1} if r + 1 < len(ACTIVE) else set())
    require(all(value == 0 for s, value in enumerate(vector) if s not in allowed),
            f"fresh cross r={r} escaped r/r+1 support")
    if r == ACTIVE[-1]:
        require(vector[26] == 0,
                "fresh r=25 cross has forbidden count-26 target")
    expected = _expected_shard(
        r, vector, counts, groups, nonzero, faces,
        inner_i, inner_b, 307)
    return tuple(vector), expected


def _reconstruct_shell(core, high, low):
    zero_label = (0, ())
    masses = [
        high.basis_m1_in_strata(r, zero_label, r, zero_label) -
        low.basis_m1_in_strata(r, zero_label, r, zero_label)
        for r in range(K + 1)
    ]
    require(all(value > 0 for value in masses[:len(ACTIVE)]) and
            all(value == 0 for value in masses[len(ACTIVE):]),
            "fresh shell I masses have wrong active support")
    ordered = {}
    counts = {}
    for tag, left, right in (
            ("hh", high, high), ("hl", high, low),
            ("lh", low, high), ("ll", low, low)):
        table, count = core.shell.cross_constant_stratum_table(
            left, right, Q(PARAMETERS["eta"][1]))
        require(type(table) is list and len(table) == K + 1 and
                all(type(row) is list and len(row) == K + 1 for row in table) and
                all(isinstance(value, Q) for row in table for value in row),
                f"fresh ordered shell table {tag} is malformed")
        strict_nonnegative_int(count, f"fresh shell count {tag}")
        ordered[tag] = table
        counts[tag] = count
    require(all(ordered["lh"][r][s] == ordered["hl"][s][r]
                for r in range(K + 1) for s in range(K + 1)),
            "fresh LH is not the transpose of fresh HL")
    require(counts["lh"] == counts["hl"],
            "fresh ordered mixed shell domain counts differ")
    raw, shell_48j = ordered_shell_inclusion(
        ordered["hh"], ordered["hl"], ordered["lh"], ordered["ll"])
    require(all(raw[r][s] == raw[s][r]
                for r in range(K + 1) for s in range(K + 1)),
            "fresh shell inclusion-exclusion is not symmetric")
    require(all(raw[r][s] == 0
                for r in ACTIVE for s in ACTIVE if abs(r - s) > 1),
            "fresh shell inclusion-exclusion is not tridiagonal")
    require(all(raw[r][s] == 0
                for r in range(K + 1) for s in range(K + 1)
                if r >= len(ACTIVE) or s >= len(ACTIVE)),
            "fresh shell inclusion-exclusion has inactive support")
    return masses, shell_48j, counts


def _open_external_candidate(path, expected_sha256):
    target = Path(path).absolute()
    parent = _open_directory(target.parent)
    try:
        snapshot = _open_leaf(parent, target.name, 64_000_000,
                              expected_sha256=expected_sha256)
    except Exception:
        os.close(parent["descriptor"])
        parent["descriptor"] = None
        raise
    snapshot["path"] = str(target)
    return parent, snapshot


def _prepare_output(path):
    target = Path(path).absolute()
    directory = _open_directory(target.parent)
    leaf = _safe_leaf(target.name)
    try:
        os.stat(leaf, dir_fd=directory["descriptor"], follow_symlinks=False)
    except FileNotFoundError:
        pass
    except OSError as error:
        os.close(directory["descriptor"])
        directory["descriptor"] = None
        raise ReconstructionFailure("cannot inspect output leaf") from error
    else:
        os.close(directory["descriptor"])
        directory["descriptor"] = None
        raise ReconstructionFailure("output path already exists")
    return {"directory": directory, "leaf": leaf, "path": str(target),
            "published": False}


def _publish_output(output, data):
    require(type(data) is bytes and not output["published"],
            "invalid or repeated output publication")
    directory = output["directory"]
    _rebind_directory(directory)
    flags = (os.O_WRONLY | os.O_CREAT | os.O_EXCL |
             getattr(os, "O_CLOEXEC", 0))
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(output["leaf"], flags, 0o444,
                         dir_fd=directory["descriptor"])
    try:
        offset = 0
        while offset < len(data):
            written = os.write(descriptor, data[offset:])
            require(written > 0, "zero-length output write")
            offset += written
        os.fsync(descriptor)
    except Exception:
        try:
            os.ftruncate(descriptor, 0)
            os.lseek(descriptor, 0, os.SEEK_SET)
            os.write(descriptor, REJECTION_SENTINEL)
            os.fsync(descriptor)
        except OSError:
            pass
        raise
    finally:
        os.close(descriptor)
    os.fsync(directory["descriptor"])
    output["published"] = True


def _dynamic_rebind(record, record_snapshots, candidate_parent,
                    candidate_snapshot, authorization_snapshot):
    _rebind_directory(record, ALLOWED_LEAVES)
    for leaf in ALLOWED_LEAVES:
        _rebind_leaf(record, record_snapshots[leaf])
    _rebind_directory(candidate_parent)
    _rebind_leaf(candidate_parent, candidate_snapshot)
    _rebind_leaf(candidate_parent, authorization_snapshot)


def _source_result_map(sources):
    return {
        path.relative_to(REPO).as_posix(): sources[path]["sha256"]
        for path in sorted(sources, key=str)
    }


def _make_production_entry():
    token = object()
    direct_module = (__name__ == "__main__" and __spec__ is None)

    def cli_capability(expected_self_sha256):
        _bind_startup_self(expected_self_sha256)
        require(sys.flags.isolated and direct_module and
                Path(sys.argv[0]).resolve(strict=True) == FILE,
                "reconstruction requires fresh isolated direct CLI")
        return token

    def invoke(args, capability):
        require(capability is token, "production reconstruction capability absent")
        # Self has been externally bound before either input directory opens.
        self_start = _bind_startup_self(args.expected_self_sha256)
        record = None
        candidate_parent = None
        record_snapshots = {}
        candidate_snapshot = None
        authorization_snapshot = None
        sources = {}
        try:
            record = _open_directory(args.record_dir)
            require_exact_leaf_set(record, ALLOWED_LEAVES)
            for leaf in ALLOWED_LEAVES:
                limit = (2_000_000 if leaf == LEDGER_LEAF else
                         16_000_000 if leaf in STAGE_LEAVES else 16_000_000)
                expected = (args.expected_manifest_sha256
                            if leaf == MANIFEST_LEAF else None)
                record_snapshots[leaf] = _open_leaf(
                    record, leaf, limit, expected_sha256=expected)
            candidate_parent, candidate_snapshot = _open_external_candidate(
                args.candidate, args.expected_candidate_sha256)
            require(Path(candidate_parent["path"]) == Path(record["path"]).parent,
                    "candidate directory is not the producer-record parent")
            authorization_leaf = Path(record["path"]).name + ".root-authorization.json"
            authorization_snapshot = _open_leaf(
                candidate_parent, authorization_leaf, 100_000)
            authorization_snapshot["path"] = str(
                Path(candidate_parent["path"]) / authorization_leaf)
            output_path = Path(args.output).absolute()
            require(output_path != Path(candidate_snapshot["path"]) and
                    output_path.parent != Path(record["path"]) and
                    (args._output_directory_binding["device"],
                     args._output_directory_binding["inode"]) !=
                    (record["device"], record["inode"]) and
                    output_path not in {FILE, *STATIC_PINS},
                    "output aliases a protected input path")
            require((record["device"], record["inode"]) !=
                    (candidate_parent["device"], candidate_parent["inode"]),
                    "candidate parent aliases producer record directory")
            dynamic_inodes = set()
            for snapshot in (*record_snapshots.values(), candidate_snapshot,
                             authorization_snapshot):
                identity = (snapshot["device"], snapshot["inode"])
                require(identity not in dynamic_inodes,
                        "producer/candidate dynamic files alias")
                dynamic_inodes.add(identity)

            ledger_snapshot = record_snapshots[LEDGER_LEAF]
            ledger = strict_json_bytes(ledger_snapshot["bytes"], "ledger",
                                       canonical=True)
            authorization, dependency = _strict_ledger(
                ledger, record, ledger_snapshot)
            require(_snapshot_binding(authorization_snapshot) == authorization,
                    "ledger authorization inode/hash binding mismatch")
            authorization_value = strict_json_bytes(
                authorization_snapshot["bytes"], "root launch authorization",
                canonical=True)
            _strict_authorization_file(
                authorization_value, record, authorization_snapshot)
            ledger_binding = _snapshot_binding(
                ledger_snapshot, include_leaf=True)
            sources = _snapshot_source_closure(dependency)
            _validate_declared_sources(dependency, sources, "producer")
            require(all((snapshot["device"], snapshot["inode"]) not in
                        dynamic_inodes for snapshot in sources.values()),
                    "dynamic input aliases a static source")
            _validate_frozen_oracles(sources)
            _validate_analytic_artifact(sources)
            core = _load_low_level_core(sources)
            basis, vector, amplitudes, inner_i, inner_b = \
                _parse_inner_coordinate(sources)
            require(tuple(core.ei.even_basis(16)) == basis,
                    "D16 certificate basis differs from fresh even D16 basis")
            named, catalog, weights, high, low = \
                _construct_named_cross_inputs(core, basis, vector, amplitudes)

            fresh_vectors = []
            expected_shards = []
            for r in ACTIVE:
                # Reparse/recontract the held radial artifacts before every
                # independent common-r integration.  No producer stage has yet
                # been parsed.
                again = _parse_inner_coordinate(sources)
                require(again == (basis, vector, amplitudes, inner_i, inner_b),
                        f"inner coordinate changed before fresh shard {r}")
                fresh, expected = _reconstruct_cross_expected(
                    core, named, catalog, weights, r, inner_i, inner_b)
                fresh_vectors.append(fresh)
                expected_shards.append(expected)
            merged = tuple(sum((fresh_vectors[r][s] for r in ACTIVE), Q(0))
                           for s in range(K + 1))
            require(all(value == 0 for value in merged[len(ACTIVE):]),
                    "fresh merged cross has inactive-count tail")

            masses, shell_48j, shell_counts = _reconstruct_shell(core, high, low)
            fresh_a, fresh_b = assemble_fresh_forms(
                inner_i, inner_b, merged, masses, shell_48j)

            # Only now, after all 26 integrations and every shell block have
            # been reconstructed, parse and compare producer stage arithmetic.
            stage_timing = []
            for r, expected in enumerate(expected_shards):
                stage = strict_json_bytes(
                    record_snapshots[STAGE_LEAVES[r]]["bytes"],
                    f"stage {r}", canonical=True)
                stage_timing.append(_strict_stage(
                    stage, r, ledger, ledger_binding, authorization,
                    dependency, expected))

            # Manifest arithmetic is parsed only after all 26 expected shards,
            # their fresh merge, and the independent shell forms exist.
            manifest_snapshot = record_snapshots[MANIFEST_LEAF]
            manifest = strict_json_bytes(manifest_snapshot["bytes"], "manifest",
                                         canonical=True)
            manifest_seen = _strict_manifest(
                manifest, record, ledger, ledger_snapshot, authorization,
                dependency,
                [record_snapshots[leaf] for leaf in STAGE_LEAVES],
                stage_timing, merged)
            require((manifest_snapshot["device"], manifest_snapshot["inode"])
                    not in manifest_seen,
                    "manifest aliases ledger or stage")

            # Candidate arithmetic is parsed last.  Its vector is the only
            # discovery datum admitted to the exact contraction.
            candidate = strict_json_bytes(candidate_snapshot["bytes"],
                                          "candidate", canonical=True)
            candidate_dependency = candidate.get("dependency_sha256")
            _validate_declared_sources(candidate_dependency, sources, "candidate")
            rational_vector, denominator, numerator, margin = _strict_candidate(
                candidate, candidate_snapshot, record, ledger_snapshot,
                manifest_snapshot, authorization, authorization_snapshot,
                dependency,
                [record_snapshots[leaf] for leaf in STAGE_LEAVES],
                fresh_a, fresh_b, shell_counts)

            forms_bytes = canonical_json({
                "48J_matrix": [[str(value) for value in row] for row in fresh_b],
                "I_diagonal": [str(value) for value in fresh_a],
            })
            result = {
                "candidate_binding": {
                    "device": candidate_snapshot["device"],
                    "inode": candidate_snapshot["inode"],
                    "path": candidate_snapshot["path"],
                    "sha256": candidate_snapshot["sha256"],
                },
                "authorization_binding": {
                    "device": authorization_snapshot["device"],
                    "inode": authorization_snapshot["inode"],
                    "path": authorization_snapshot["path"],
                    "sha256": authorization_snapshot["sha256"],
                },
                "checker_sha256": _SELF["sha256"],
                "design_sha256": STATIC_PINS[DESIGN],
                "exact_margin": str(margin),
                "exact_quotient": str(numerator / denominator),
                "exact_rational_denominator": str(denominator),
                "exact_rational_numerator": str(numerator),
                "finite_space_crosses_one": True,
                "fresh_forms_sha256": sha256_bytes(forms_bytes),
                "independent_arithmetic_reconstruction": True,
                "ledger_binding": {
                    "device": ledger_snapshot["device"],
                    "inode": ledger_snapshot["inode"],
                    "path": str(Path(record["path"]) / LEDGER_LEAF),
                    "sha256": ledger_snapshot["sha256"],
                },
                "manifest_binding": {
                    "device": manifest_snapshot["device"],
                    "inode": manifest_snapshot["inode"],
                    "path": str(Path(record["path"]) / MANIFEST_LEAF),
                    "sha256": manifest_snapshot["sha256"],
                },
                "particular_vector_sha256": sha256_bytes(canonical_json(
                    [str(value) for value in rational_vector])),
                "producer_driver_sha256": PRODUCER_SHA256,
                "record_directory": {
                    key: record[key] for key in ("path", "device", "inode")
                },
                "reconstructed_common_counts": list(ACTIVE),
                "scope": (
                    "exact 27D particular-vector certificate from fresh 26-shard "
                    "and four-ordered-shell reconstruction; no eigenvalue "
                    "optimality or sieve theorem claim"),
                "shell_domain_counts": shell_counts,
                "source_sha256": _source_result_map(sources),
                "stage_bindings": [
                    _snapshot_binding(record_snapshots[leaf], include_leaf=True)
                    for leaf in STAGE_LEAVES
                ],
                "status": "INDEPENDENT ARITHMETIC RECONSTRUCTION PASS",
                "theorem_ready": False,
            }
            payload = canonical_json(result)
            _rebind_source_closure(sources)
            _dynamic_rebind(record, record_snapshots, candidate_parent,
                            candidate_snapshot, authorization_snapshot)
            require(_bind_startup_self(args.expected_self_sha256) == self_start,
                    "checker source changed during reconstruction")
            return payload
        finally:
            _close_snapshots(sources.values())
            _close_snapshots(record_snapshots.values())
            _close_snapshots([candidate_snapshot, authorization_snapshot])
            _close_snapshots([record, candidate_parent])

    return invoke, cli_capability


_PRODUCTION_INVOKE, _CLI_CAPABILITY = _make_production_entry()


def _parser():
    parser = argparse.ArgumentParser(
        description="fresh exact active25 D16 v6 reconstruction")
    parser.add_argument("--expected-self-sha256", required=True)
    parser.add_argument("--record-dir", required=True, type=Path)
    parser.add_argument("--expected-manifest-sha256", required=True)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--expected-candidate-sha256", required=True)
    parser.add_argument("--output", required=True, type=Path)
    return parser


def main():
    args = _parser().parse_args()
    output = _prepare_output(args.output)
    args._output_directory_binding = {
        key: output["directory"][key] for key in ("path", "device", "inode")
    }
    try:
        strict_sha(args.expected_self_sha256, "expected checker self SHA")
        strict_sha(args.expected_manifest_sha256, "expected manifest SHA")
        strict_sha(args.expected_candidate_sha256, "expected candidate SHA")
        capability = _CLI_CAPABILITY(args.expected_self_sha256)
        result = _PRODUCTION_INVOKE(args, capability)
        _publish_output(output, result)
        sys.stdout.buffer.write(result)
        sys.stdout.buffer.flush()
        return 0
    except (Exception, KeyboardInterrupt):
        if not output["published"]:
            try:
                _publish_output(output, REJECTION_SENTINEL)
            except Exception:
                pass
        sys.stderr.write("REJECTED\n")
        return 1
    finally:
        _close_snapshots([output["directory"]])


if __name__ == "__main__":
    raise SystemExit(main())
