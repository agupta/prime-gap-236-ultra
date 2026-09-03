# Active25 D16 staged v6 independent prelaunch audit

Status: **PRELAUNCH PASS** for the exact frozen v6 one-shot producer and
conditional assembler tuple below.  This authorizes neither a theorem claim
nor trust in the serialized shard arithmetic.  No target shard integration or
conditional target assembly was executed during this audit.

## Frozen tuple

- one-shot producer `frontier_active25_inner_d16_staged_v6.py`:
  `cfc4c3803312d5e41d87c27a753cd843da9534e85ea5e73d77079bf9ce8e284e`
- producer tests: `c5e45fe4a929fba55f29ae96f6e127bd8a680d8fa0ca01ca17dfa70f2b56d6ff`
- conditional assembler `assemble_frontier_active25_inner_d16_v6.py`:
  `4b834f1a87b995a73a86d4e02505ddea599191467eccd69d43eed1d8f85b1356`
- assembler tests: `e6ad2423ce9545e7a3f890b30f4e230bc49f4a15bfea04ed6f8d4340cdeb80ff`
- disabled v6 gate: `7b37c89dd84b03301e3937c981b7c67ea6ce17e21bfd07a76199430bcfb16b80`
- v6 prelaunch contract: `ed9fd5aacc27308f3dd2827d6517044be18057e937cdb99942420c3a3a1e308a`

The gate remains `launch_authorized:false`.  This PASS makes the tuple
eligible only for a later explicit root authorization artifact binding one
new empty attempt directory, this producer and gate, and the SHA-256 of this
report.

## Independent review

The checker independently exercised a complete 26-shard synthetic one-shot
run.  It observed exactly the ledger, `common_r_00` through `common_r_25`, and
manifest: 28 distinct regular inodes.  It reconstructed the global timeline
and exact cumulative child time, checked both memory observations per shard,
their five-second separation, all child intervals, the 600-second shard limit,
the four-hour immutable deadline, and the final manifest merge.

Fresh-directory, provenance, and abandonment tests rejected a nonempty
initializer directory, fabricated prefix, completed replay, interrupted
prefix, wrong external ledger SHA, hardlinked ledger, wrong boot, insufficient
memory, and an overlong child before an invalid stage or manifest could be
accepted.  The producer and assembler bind their startup source inodes, root
authorization, ledger, manifest, 26 stage files, and a 46-file transitive
source/data closure.  The assembler also rebinds its external result before a
successful verification response and never overwrites an existing output.

Hostile mathematical records were rejected for an extra field, wrong common
count, noncanonical fraction, off-support target, inconsistent inner identity,
nonpositive inner `I`, D16 dimension other than 307, and a nonzero inactive
count-26 tail in shard 25.  Conditional-result mutations of the factor-48
entry, exact margin, stage-inode inventory, `theorem_ready`, and
`independent_arithmetic_reconstruction` were also rejected.

The inactive count-26 tail, loose D16 dimension/positive-I check, and
incomplete transitive closure were concrete defects found while the tuple was
still moving.  They were repaired before the six hashes above were frozen and
the hostile cases were rerun successfully.

## Regression and replay evidence

The final producer suite passes 14/14 and the assembler suite passes 9/9 under
both ordinary and optimized Python.  Isolated normal and `-O` preflight output
is byte-identical with SHA-256
`be576a376b884a2a821c4feef4c29167aede6772f0f549f0f3206dc7ae57de4b`.
Two full invocations of the independent checker, normal and `-O`, emitted
byte-identical canonical results.

- independent checker `verify_frontier_active25_v6_prelaunch.py`:
  `c88bb29f830c9c5fefc3cd9be636df018278dad8e9741991fdcf23ae667f03e6`
- canonical result `results/frontier_active25_v6_prelaunch_audit.json`:
  `c6eaa5b4de9d102c0d39782e9194ba02d3042a6adbc3a7db046f863d78128408`

Replay without executing target arithmetic:

```text
python3 agents/audit/verify_frontier_active25_v6_prelaunch.py
python3 -O agents/audit/verify_frontier_active25_v6_prelaunch.py
```

The staged and assembled values remain explicitly conditional:
`independent_arithmetic_reconstruction=false`,
`serialized_stage_arithmetic_conditional=true`,
`eigenvalue_optimality_rigorous=false`, and `theorem_ready=false`.  A later
one-shot checker must independently recompute every shard and both exact forms
before any mathematical promotion.
