# Active25 grouped D16 v2: scoped PRELAUNCH PASS

Date: 2026-09-03 (Europe/Berlin).

## Verdict

`PRELAUNCH PASS FOR FROZEN DISABLED V2; LAUNCH DISABLED`.

This passes the exact grouped arithmetic, the true ungrouped oracle check,
the Definition-5 signs and factors, the resource-envelope arithmetic, and the
v2 disabled staging scaffold.  It does **not** authorize a target shard, a
complete matrix, a quotient, or a sieve conclusion.  Direct attempts to run
a shard fail before integration and publish no file because the pinned gate
has `launch_authorized=false`.

The earlier unversioned staged tuple remains separately recorded as an audit
failure because its bytes moved after its announced freeze.  This verdict is
only for the distinct versioned v2 paths and hashes.

## Independently checked facts

- The true ungrouped and direct-grouped `r=10,h=10` artifacts agree in all 49
  exact entries, and every raw pair table independently recontracts as
  `b*(RH-RL)+(a-b)*(VH-VL)`.
- Literal, grouped, direct-full, and canonical target-count recurrences agree
  exactly for independent low-dimensional tests.
- The shell matrix is reconstructed as
  `48*(HH-HL-HL^T+LL)`, with factor 48 exactly once; the raw inner/shell
  cross remains raw J for a future assembler to multiply once.
- The active shell counts are `0..25`; 26 shell coordinates plus one inner
  coordinate give dimension 27.
- All 585 faces and the stated time/RSS safety-envelope arithmetic reconstruct
  from the six pinned benchmark artifacts.  One worker is required.
- The v2 merge is order-independent exact Fraction addition and rejects
  incomplete, duplicate, escaped-support, and inconsistent-inner fixtures.
- Normal and `python3 -O` checker outputs are byte-identical.

## Mandatory next authorization step

Before any target stage can run, create a **new versioned authorized gate**
and a **new versioned wrapper revision that pins that gate**.  A fresh
independent delta audit must verify the live-memory readings, one-worker
enforcement, all immutable pins, and fail-closed publication.  Before any
stage result can be consumed, a strict envelope-aware post-run consumer must
pin the complete stage artifacts and reject missing, duplicate, malformed, or
foreign-provenance envelopes.  Editing the current v2 gate or wrapper in
place is forbidden.

## Frozen audit artifacts

- checker: `agents/audit/verify_frontier_active25_grouped_prelaunch.py`;
- result: `agents/audit/results/frontier_active25_grouped_prelaunch_v2_audit.json`.

Reproduce from `prime-gap-236/`:

```bash
python3 agents/audit/verify_frontier_active25_grouped_prelaunch.py
python3 -O agents/audit/verify_frontier_active25_grouped_prelaunch.py
python3 agents/small-delta-frontier/test_frontier_active25_inner_d16_staged_v2.py
python3 -O agents/small-delta-frontier/test_frontier_active25_inner_d16_staged_v2.py
```
