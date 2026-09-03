# Active25 inner-D16 staged v6 prelaunch contract

Status: **PRELAUNCH CANDIDATE — TARGET EXECUTION NOT AUTHORIZED**.

This v6 package replaces the rejected resumable v5 protocol with a one-shot
protocol.  It does not authorize a D12 traversal, certify any finite form, or
change the separate requirement for an independent arithmetic reconstruction.

## Frozen candidate tuple

| Role | Path | SHA-256 |
|---|---|---|
| one-shot producer | `agents/small-delta-frontier/frontier_active25_inner_d16_staged_v6.py` | `cfc4c3803312d5e41d87c27a753cd843da9534e85ea5e73d77079bf9ce8e284e` |
| producer tests | `agents/small-delta-frontier/test_frontier_active25_inner_d16_staged_v6.py` | `c5e45fe4a929fba55f29ae96f6e127bd8a680d8fa0ca01ca17dfa70f2b56d6ff` |
| conditional assembler | `agents/small-delta-frontier/assemble_frontier_active25_inner_d16_v6.py` | `4b834f1a87b995a73a86d4e02505ddea599191467eccd69d43eed1d8f85b1356` |
| assembler tests | `agents/small-delta-frontier/test_assemble_frontier_active25_inner_d16_v6.py` | `e6ad2423ce9545e7a3f890b30f4e230bc49f4a15bfea04ed6f8d4340cdeb80ff` |
| disabled prelaunch gate | `agents/small-delta-frontier/results/frontier_active25_innerD16_tagged_shell_authorized_gate_v6.json` | `7b37c89dd84b03301e3937c981b7c67ea6ce17e21bfd07a76199430bcfb16b80` |

The predecessor v5 failure is frozen at checker
`127024d7117a130b21e4a93cb5f99ddbf59273e756802270feb52f0494c881a8`,
result `a173658fa20ada39cf2ca78e98ea92601be6e3709db9674826512c9e3a76c875`,
and report
`c60934e5c88c7d13160b488042c1a5446808201b57b356c4dbd6cb6404d77b99`.
The independent arithmetic-reconstruction design is pinned at
`976d7f43d52d45be33def40f376ebfe657af0fe3aba880f5c4de807a46b2693e`.

## Trust boundary and one-shot state machine

Production entry is a fresh isolated `python3 -I` process.  The caller must
supply the producer SHA, and the process binds it directly to source bytes and
the singly linked inode opened at process startup.  All inherited v5, v2,
arithmetic-core, support, exact-integrator, grouped-integrator, data, gate, and
audit dependencies are captured and rebound.  The standard interpreter,
kernel, `/proc` readings, monotonic clock, and filesystem primitives are in the
declared trust boundary; arbitrary malicious mutation inside that fresh Python
process is not.

The protocol has exactly two producer invocations:

1. `--initialize-ledger-only` requires an empty, already-existing canonical
   attempt directory.  It exclusively creates the sole `ledger.json` leaf and
   exits.  The ledger binds the directory device/inode, Linux boot ID,
   monotonic start/deadline, all source hashes, the producer SHA, gate SHA, and
   separately authorized root artifact.
2. Root records the ledger byte SHA, device, and inode outside the producer.
   A second fresh isolated invocation must receive those three values and must
   find exactly that one ledger leaf at startup.  It computes common counts
   0--25 continuously and has no resume/reuse path.  Every child is a fresh
   isolated subprocess, returns bytes only, is killed/reaped at the lesser of
   600 seconds and the remaining global deadline, and is validated before the
   parent exclusively publishes its shard.

Any crash, timeout, rejection, or interruption abandons the entire attempt
directory.  A new attempt requires a new empty directory, new root
authorization bound to that directory, and a new ledger.  Existing prefixes
or manifests can never be resumed, even if individually canonical.

Before every shard, the parent takes two real `MemAvailable` readings of at
least 1,400,000 KiB.  Their measured monotonic intervals are disjoint and
separated by at least five seconds.  Resource and child intervals are globally
ordered.  Every persisted timestamp is no later than a subsequent fresh live
observation, on the same boot, and no later than the immutable four-hour
deadline.  The exact directory leaf set is checked before and after every
exclusive publication.  Ledger, all 26 stages, and manifest must be distinct,
singly linked regular inodes.

The v6 shard wrapper strengthens the inherited parser: dimension is exactly
307, inner `I` is positive, and a common-`r` raw cross can be supported only on
active targets `{r,r+1} intersect {0,...,25}`.  In particular, target count 26
is exactly zero for the `r=25` shard and in the merged vector.

## Separate future root authorization

The frozen gate deliberately contains `launch_authorized:false`.  Only after
an independent byte-specific prelaunch PASS may root create a canonical,
singly linked authorization artifact outside the record directory.  Its SHA
must be supplied externally to both producer invocations and the assembler.
It has exactly these keys and values (substitute the audited report SHA and
canonical fresh attempt directory):

```json
{
  "driver_sha256": "cfc4c3803312d5e41d87c27a753cd843da9534e85ea5e73d77079bf9ce8e284e",
  "format": "frontier-active25-inner-D16-v6-root-launch-authorization-v1",
  "gate_sha256": "7b37c89dd84b03301e3937c981b7c67ea6ce17e21bfd07a76199430bcfb16b80",
  "independent_prelaunch_report_sha256": "AUDITOR_REPORT_SHA",
  "max_total_wall_seconds": 14400,
  "one_shot_attempt_authorized": true,
  "record_directory": "/ABSOLUTE/FRESH/ATTEMPT/DIRECTORY",
  "status": "ROOT_AUTHORIZED_AFTER_INDEPENDENT_PRELAUNCH_PASS",
  "theorem_ready": false,
  "workers": 1
}
```

This artifact is governance evidence supplied by root, not a cryptographic
signature.  Its externally recorded SHA and inode are bound into the ledger,
every child, every stage, the manifest, and the conditional result.

## Resource model

The frozen predecessor probe projects 3,329.7498 seconds for all common-count
shards.  The predeclared wall safety factor is 3, yielding 9,989.2494 seconds,
below the immutable 14,400-second deadline.  The measured peak-RSS basis was
152,640 KiB; the factor-4 projection is 610,560 KiB.  The launch-time gate is
the stronger direct requirement of two live `MemAvailable >= 1,400,000 KiB`
readings before every shard, with one worker.  These thresholds are frozen
before observing any target timing and are not relaxed by this document.

## Commands (documented only; do not execute before authorization)

Intended fresh paths:

```text
ATTEMPT=agents/small-delta-frontier/results/frontier_active25_innerD16_v6_attempt_001
AUTH=agents/small-delta-frontier/results/frontier_active25_innerD16_v6_attempt_001.root-authorization.json
RESULT=agents/small-delta-frontier/results/frontier_active25_innerD16_v6_conditional_pencil.json
```

After independent PASS and root creation of `AUTH`, initialize only:

```text
python3 -I agents/small-delta-frontier/frontier_active25_inner_d16_staged_v6.py \
  --initialize-ledger-only --record-dir "$ATTEMPT" \
  --expected-self-sha256 cfc4c3803312d5e41d87c27a753cd843da9534e85ea5e73d77079bf9ce8e284e \
  --authorization-file "$AUTH" \
  --expected-authorization-sha256 AUTH_SHA
```

Root must independently record `LEDGER_SHA`, `LEDGER_DEVICE`, and
`LEDGER_INODE` from the new leaf.  The only permissible production command is:

```text
python3 -I agents/small-delta-frontier/frontier_active25_inner_d16_staged_v6.py \
  --record-dir "$ATTEMPT" \
  --expected-self-sha256 cfc4c3803312d5e41d87c27a753cd843da9534e85ea5e73d77079bf9ce8e284e \
  --authorization-file "$AUTH" \
  --expected-authorization-sha256 AUTH_SHA \
  --expected-ledger-sha256 LEDGER_SHA \
  --expected-ledger-device LEDGER_DEVICE \
  --expected-ledger-inode LEDGER_INODE
```

After root independently records the completed manifest SHA, conditional
assembly (still not certification) is:

```text
python3 -I agents/small-delta-frontier/assemble_frontier_active25_inner_d16_v6.py \
  --record-dir "$ATTEMPT" \
  --authorization-file "$AUTH" \
  --expected-authorization-sha256 AUTH_SHA \
  --expected-self-sha256 4b834f1a87b995a73a86d4e02505ddea599191467eccd69d43eed1d8f85b1356 \
  --expected-producer-sha256 cfc4c3803312d5e41d87c27a753cd843da9534e85ea5e73d77079bf9ce8e284e \
  --expected-manifest-sha256 MANIFEST_SHA \
  --expected-ledger-sha256 LEDGER_SHA \
  --expected-ledger-device LEDGER_DEVICE \
  --expected-ledger-inode LEDGER_INODE \
  --output "$RESULT"
```

## Result scope

The assembler checks the complete one-shot provenance, reconstructs the exact
27-dimensional serialized pencil, uses `48 * raw_J_cross` exactly once for
each inner/shell matrix entry, and exactly contracts its rationalized vector.
It always emits:

```text
independent_arithmetic_reconstruction = false
serialized_stage_arithmetic_conditional = true
eigenvalue_optimality_rigorous = false
theorem_ready = false
```

Even a positive conditional margin is only a discovery signal.  The frozen
independent reconstruction design requires a new one-shot checker to recompute
all 26 grouped integrations and the shell blocks without importing this
producer or assembler before any theorem claim.

## Test evidence

The producer suite has 14 tests and the assembler suite has 9 tests.  Both are
required to pass under ordinary Python and `python3 -O`.  They cover the v5
fabricated-prefix failure surface, isolated/self-bound CLI, authorization and
ledger inode rebinding, interruption/no-resume behavior, boot/deadline and
memory intervals, timeout kill/reap, exact leaf sets, transitive dependency
mutation, inactive count 26, D16 dimension/positive-I gates, factor 48, exact
result contraction, forbidden theorem flags, output O_EXCL behavior, and
external-result inode replacement.
