# Importance D4 v5 normal completed-output reaudit

## Verdict

**REPAIRED PUBLICATION PASS; CALIBRATION IMPLEMENTATION REJECTED.**  The
completed 128-checkpoint replay passes provenance, checkpoint, core-analysis,
and repaired publication closure, but the frozen analysis itself terminates
with

```text
ArithmeticError: active denominator matrix is numerically rank deficient
```

Consequently the predeclared decision is `IMPLEMENTATION_REJECTED`, exit code
1.  There is no stochastic Ritz matrix, candidate, quotient, extension, or D12
authorization from this run.

## Frozen inputs and repair

- completed production result:
  `5a7a05f3dbddc589149841e3a4d4a52850e232447ec230ad2b9ac3f5e0070634`;
- repaired consumer:
  `7a0685f089125654f5faddced809cce784f9b7aabfd9c4ae8e669771710ab2da`;
- repaired tests:
  `110376bba1a867d285792575ff17d8061e52ec9efb87698a8c83ca66fd4b6821`;
- deliberately preserved first failed publication sentinel:
  `agents/structural-basis/results/importance_d4_calibration_v5_production.audit.json`,
  SHA-256
  `a4f8518b52de5fb9c79e58c770d0c861c7e283481d745c31b6a8a3802761d879`.

The first completed replay reached audit publication but the frozen driver's
publisher normalizes dynamic bindings twice: a bare SHA becomes a one-key
dictionary on the first pass, which the second pass rejects.  The repaired
consumer snapshots its own source, decision table, eight local arithmetic
modules, and NumPy entry file and supplies only stable three-key
`{sha256,device,inode}` bindings.  A regression invokes the real frozen
publisher, proves the three-key form succeeds, and preserves the one-key
rejection.  Tests pass 8/8 under normal and optimized Python.

## Completed-fixture replay

Root authorized one repaired replay to a fresh temporary output, never the
canonical audit path:

```text
/tmp/pg236-v5-audit-repair-eOQw7e/normal-v5-audit.json
```

The artifact has SHA-256
`db1b7b74623d5d34c2541f2dda5951942eb0e958f6b8cb45007ed7d30e824740`.
It records:

- all 128 checkpoint files reopened through the authorized directory;
- checkpoint-manifest SHA `b7b5f62f...`;
- record-core SHA `1bc61ef8...`;
- analysis-core SHA `70ade593...`;
- exact production-result binding to SHA `5a7a05f3...`;
- decision `IMPLEMENTATION_REJECTED`, code 1;
- exact strict-parsed `analysis_failure` equal to
  `{"exception_type":"ArithmeticError","message":"active denominator matrix is numerically rank deficient"}`;
- no hard/statistical gate lists, because analysis construction failed before
  a matrix-level gate object existed.

The production result itself has status
`d4-stratified-calibration-rejected`, `analysis=null`, and the exact failure
type/message quoted above.  The repaired consumer independently reproduced
that serialized analysis/failure pair before publishing its audit.

## Scope

This audit is not wholly output-blind: the earlier accidental partial-byte
exposure is recorded in
`IMPORTANCE-D4-V5-OUTPUT-CONSUMER-PRECOMPLETION-AUDIT.md`.  No exposed value
was used, and the completed replay is deterministic, but root and the separate
optimized replication must supply the independent post-completion evidence.
The repaired artifact now stores both the analysis-core hash and the exact
strict-parsed failure diagnostic.  The canonical proposed audit-v2 output was
left untouched; this replay wrote only the fresh temporary leaf shown above.
