# Frontier active25 inner-D16 staged v5 prelaunch contract

Status: **frozen construction candidate; target execution withheld**.  This
document does not authorize ledger initialization, a shard traversal, or final
assembly.  A fresh independent v5 audit and a later explicit root launch are
required.

## Frozen tuple

- coordinator: `frontier_active25_inner_d16_staged_v5.py`, SHA-256
  `8bb0d5088e419d196b4aca732ec384804bf2918554cf001f372a3127e7f1f775`
- coordinator tests: `test_frontier_active25_inner_d16_staged_v5.py`, SHA-256
  `28b5b8d182fc0836a0bf905af4d7f9b907b403e35a9e61cae779428fb7f899bf`
- conditional assembler: `assemble_frontier_active25_inner_d16_v5.py`, SHA-256
  `6163402f5333c73ae011acbe64191ebff7dfac043f43d8e11c2ce635019807e9`
- assembler tests: `test_assemble_frontier_active25_inner_d16_v5.py`, SHA-256
  `9d6a242a7e3b76d8cada75ee23f1ba24c7c100ff7a0d73de0d637e8166c09e74`
- construction/resource gate:
  `results/frontier_active25_innerD16_tagged_shell_authorized_gate_v5.json`,
  SHA-256
  `b814507140740a821d67b6ccdec65eda3c30985075a19505d8bc485c84fa2420`

The gate pins the final analytic active-count-25 schedule, the audited v2
arithmetic package, the v2 prelaunch PASS, and the v3/v4 failure evidence.  In
particular, v4's mutable-dispatch forgery and v3's resumable-wall bypass are
not accepted predecessors.

## Execution boundary

Production is a two-step fresh `python3 -I` protocol.  The coordinator has no
public import-callable `run_all`, no `_REAL_*` dispatch globals, and imported
calls cannot select production formats.  Synthetic tests emit a distinct
format and the all-zero synthetic gate SHA; the production assembler rejects
those bytes.  The bounded claim assumes an ordinary fresh isolated Python
process and the operating-system file/process primitives.  It does not claim
resistance to arbitrary malicious introspection or mutation inside that same
process.

Ledger initialization is the only first step.  It creates the sole file
`ledger.json` through the held canonical directory descriptor with `O_EXCL`,
records the Linux boot ID and immutable 14,400-second monotonic deadline, and
exits before any memory reading or arithmetic child.  Root must independently
observe its SHA-256, device, and inode.  Every later resume requires all three
values, plus the externally observed coordinator SHA.  Ledger, stages, and
manifest must remain singly linked regular files.

Each of the 26 common-count shards has two actual `MemAvailable` readings of
at least 1,400,000 KiB separated by at least five monotonic seconds.  All
resource and child intervals are globally ordered.  A fresh child computes
bytes only; its parent supervises it for at most the smaller of 600 seconds
and the original remaining deadline, kills/reaps a timeout, validates exact
canonical bytes, and then publishes one stage with held-dirfd `O_EXCL`.
Every scan and publication requires the exact allowed set: one ledger, the
deterministic prefix of 26 stage leaves, and finally one manifest.  Resumption
uses the original boot/deadline and cannot reset elapsed time.

## Withheld commands

The intended fresh record directory and output are currently absent:

```
agents/small-delta-frontier/results/frontier_active25_innerD16_tagged_shell_v5_records
agents/small-delta-frontier/results/frontier_active25_innerD16_tagged_shell_v5_exact.json
```

Only after explicit authorization, create the empty directory and initialize
the immutable ledger:

```
python3 -I agents/small-delta-frontier/frontier_active25_inner_d16_staged_v5.py \
  --initialize-ledger-only \
  --record-dir agents/small-delta-frontier/results/frontier_active25_innerD16_tagged_shell_v5_records \
  --expected-self-sha256 8bb0d5088e419d196b4aca732ec384804bf2918554cf001f372a3127e7f1f775
```

Root must then supply the observed `LEDGER_SHA`, `LEDGER_DEVICE`, and
`LEDGER_INODE` unchanged to every resume:

```
python3 -I agents/small-delta-frontier/frontier_active25_inner_d16_staged_v5.py \
  --record-dir agents/small-delta-frontier/results/frontier_active25_innerD16_tagged_shell_v5_records \
  --expected-self-sha256 8bb0d5088e419d196b4aca732ec384804bf2918554cf001f372a3127e7f1f775 \
  --expected-ledger-sha256 LEDGER_SHA \
  --expected-ledger-device LEDGER_DEVICE \
  --expected-ledger-inode LEDGER_INODE
```

After root separately supplies the completed manifest SHA, conditional exact
assembly would use:

```
python3 -I agents/small-delta-frontier/assemble_frontier_active25_inner_d16_v5.py \
  --record-dir agents/small-delta-frontier/results/frontier_active25_innerD16_tagged_shell_v5_records \
  --expected-self-sha256 6163402f5333c73ae011acbe64191ebff7dfac043f43d8e11c2ce635019807e9 \
  --expected-ledger-sha256 LEDGER_SHA \
  --expected-ledger-device LEDGER_DEVICE \
  --expected-ledger-inode LEDGER_INODE \
  --expected-manifest-sha256 MANIFEST_SHA \
  --output agents/small-delta-frontier/results/frontier_active25_innerD16_tagged_shell_v5_exact.json
```

## Cost gate and tests

The pinned representative-face projection is 3,329.749849067302635 seconds
at one worker.  The predeclared three-times wall envelope is
9,989.249547201907905 seconds, below the immutable 14,400-second deadline.
The four-times measured RSS envelope is 152,640 KiB.  A single shard is
limited to 600 seconds.  These limits are fixed before target timing is
observed.

The following completed without creating any target ledger or shard:

```
python3 agents/small-delta-frontier/test_frontier_active25_inner_d16_staged_v5.py
python3 -O agents/small-delta-frontier/test_frontier_active25_inner_d16_staged_v5.py
python3 agents/small-delta-frontier/test_assemble_frontier_active25_inner_d16_v5.py
python3 -O agents/small-delta-frontier/test_assemble_frontier_active25_inner_d16_v5.py
```

Results: coordinator 13/13 in each mode; assembler 7/7 in each mode.  The
tests include external ledger mismatch, wrong self SHA, deadline/reboot and
Boolean clock cases, global interval overlap, external hardlinks, extra-leaf
injection, timeout kill/reap with no shard, malformed child/stage data,
missing/replaced/symlink leaves, factor-47 rejection, exact factor-48 cross,
output `O_EXCL`, foreign-inode preservation, and external-output hardlinks.

## Exact claim boundary

The assembler recomputes the shell forms and exact rational contraction, and
applies the factor 48 to each serialized raw inner/shell cross exactly once.
It does **not** independently recompute the 26 expensive shard integrals.  Its
output therefore fixes
`independent_arithmetic_reconstruction=false`,
`serialized_stage_arithmetic_conditional=true`, and `theorem_ready=false`,
even if its conditional finite-space rational vector crosses one.  A theorem
claim requires the one-shot independent reconstruction contract in
`agents/audit/FRONTIER-ACTIVE25-INDEPENDENT-ARITHMETIC-RECONSTRUCTION-DESIGN.md`
(SHA-256
`976d7f43d52d45be33def40f376ebfe657af0fe3aba880f5c4de807a46b2693e`).
