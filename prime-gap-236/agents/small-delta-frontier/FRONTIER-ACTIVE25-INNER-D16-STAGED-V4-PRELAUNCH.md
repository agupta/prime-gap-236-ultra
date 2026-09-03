# Frontier active25 D16 staged v4 prelaunch package

Status: **PRELAUNCH ONLY — target execution is withheld pending an independent
v4 delta audit and a later explicit root launch instruction.**  The embedded
gate records authorization to construct this package; it is not, by itself,
authorization to execute the target.

## Frozen tuple

- arithmetic core: `frontier_active25_inner_d16_tagged_shell.py`, SHA-256
  `1393a2dd29e5660f10e632b19b6b5eeafe9363bf79b2cd4a8254049d1f9c669a`
- v2 independent PRELAUNCH PASS result: SHA-256
  `bd93b52f3556b9d35edb2568b61c74362e4e156f5b607e6755f2ac7203a3c9a2`
- v3 frozen failure regression/report: SHA-256
  `13c5a756ca7b12e718fbd9b731bf62fae48b556d895cfd5b2caf1b344d3a2b67` /
  `a384a19332f87c7f8adbc17c7514ea2dc070514b5b477bd6d95d256203b40d14`
- v4 resource gate: `results/frontier_active25_innerD16_tagged_shell_authorized_gate_v4.json`,
  SHA-256 `2dcfb44e4c9fbc5ec5f9b030f6565a35b06af478dff60c0805f96b44078c35fe`
- v4 staged driver: `frontier_active25_inner_d16_staged_v4.py`, SHA-256
  `7d5188ec18ef99ae22aeada193471a69c11cf15363aa26496ef8b3217387beef`
- staged-driver tests: `test_frontier_active25_inner_d16_staged_v4.py`,
  SHA-256 `4082c32c1358d564f6ed17743c3ccdc471813c67df5a5a3013acd9aa1e227ac0`
- v4 assembler/consumer: `assemble_frontier_active25_inner_d16_v4.py`,
  SHA-256 `0b60c03e3743fe8003c9571423e79922a3ded08594d30894bee2461e980d0d85`
- assembler tests: `test_assemble_frontier_active25_inner_d16_v4.py`,
  SHA-256 `bb2a751b0459365641e188afc0f67fea27781e7a17a04538b5f35b3bae1140db`

The wrapper pins the exact active25 schedule audit, arithmetic closure, v2
prelaunch audit, and frozen v3 failure.  The assembler pins the wrapper and its
test bytes and inherits that full closure.

## State and resource invariant

The first and only initial leaf is an O_EXCL immutable ledger.  It binds the
held canonical record-directory device/inode, Linux boot ID, monotonic start,
fixed `start + 14400 s` deadline, exact dependency hashes, and the only allowed
leaf names: ledger, 26 `common_r_00..25` stages, and manifest.  Resume uses the
same ledger, boot, and deadline; an empty pre-existing ledger cannot resume.

Before each new shard the production CLI records two actual `MemAvailable`
reads of at least 1,400,000 KiB with at least five monotonic seconds between
them.  It starts one fresh isolated child, supervises it for at most
`min(600 s, remaining global deadline)`, kills/reaps on timeout, validates its
sole canonical stdout payload, and only then publishes the stage via a held
directory fd and O_EXCL.  Nonempty stderr, truncated/extra stdout, nonzero
exit, timeout, source mutation, clock reversal/overflow, boot change, and any
extra/missing/replaced/aliased leaf fail closed.  Synthetic test records use a
different format and all-zero synthetic gate SHA and are rejected by the
production assembler.  Production coordination is direct isolated-CLI only;
the injectable internal path cannot emit production-format records.

The final manifest rebinds the immutable ledger and all 26 stage SHAs and
inodes, records cumulative supervised and total monotonic time, and recomputes
the exact merged cross vector.  The consumer requires a caller-supplied
manifest SHA, rebinds the exact directory leaf set before and after assembly,
applies 48 exactly once to raw inner/shell cross-J entries, reconstructs the
exact rational particular forms, and publishes only through a held output
directory fd with O_EXCL and post-publication hash/inode checks.  It remains a
finite-space result with `theorem_ready=false` until the separate analytic and
certificate chain is complete.

## Tests and deterministic preflight

The staged suite passes 13/13 under normal Python and `python3 -O`; the
assembler suite passes 6/6 under both modes.  Both modules pass `py_compile`.
The isolated preflight is byte-identical in normal and `-O`.  Hostile fixtures
cover the v3 resume-wall bypass, fake production runtime, production-runtime
monkeypatch, disjoint synthetic formats, reboot/clock edges, real timeout
kill/reap, stderr and noncanonical child output, memory-field booleans, extra
leaf races, ledger/stage tamper and hardlinks, completed-set mutation, factor
48, exact contraction, O_EXCL collision, and foreign output-inode replacement.

## Withheld execution contract

The intended fresh record directory (currently absent) is:

`agents/small-delta-frontier/results/frontier_active25_innerD16_v4_stages`

After a future explicit launch authorization, create that directory once and
run exactly:

```text
python3 -I agents/small-delta-frontier/frontier_active25_inner_d16_staged_v4.py --record-dir agents/small-delta-frontier/results/frontier_active25_innerD16_v4_stages
```

After completion, record the externally observed manifest SHA.  Only then run:

```text
python3 -I agents/small-delta-frontier/assemble_frontier_active25_inner_d16_v4.py --record-dir agents/small-delta-frontier/results/frontier_active25_innerD16_v4_stages --expected-manifest-sha256 MANIFEST_SHA --output agents/small-delta-frontier/results/frontier_active25_innerD16_v4_exact_pencil.json
```

Neither command has been run.  The record directory and output path were both
verified absent at freeze time.
