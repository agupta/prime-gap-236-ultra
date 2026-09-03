# Frozen exact-whitened importance calibration v6.6 hostile audit

## Verdict

`AUDIT PASS`

The frozen v6.6 prelaunch package closes the known v6--v6.5 arithmetic and
record-validation counterexamples.  Its gate remains production-disabled,
non-rigorous, and theorem-neutral.  This verdict approves the package's
fail-closed prelaunch arithmetic; it does not itself authorize a production
run.

Audited gate SHA-256:
`fa1019605ef6b5efd486b234451806efcf1912f7b3f181c9511839d873b63bf6`.
The gate binds 75 source files and ten data files, supersedes frozen v6.5,
and pins the v6.5 failure report, verifier, and regression verbatim.

## Independent checks

- Rebuilt the gate from its self-hashed builder and obtained the frozen gate
  object exactly; a false builder trust root rejects.
- Rehashed every source and data dependency and independently validated the
  trusted adapter against the pinned vector, exact oracle, whitening
  transform, and exact tagged weights.
- Traced runtime installation through the inherited v6/v5 execution sites
  and the conditional-density callback.  All resolve to the v6.6 envelope
  and record wrappers.
- Replayed the v6 Cauchy-bound mutation, both v6.1 regrouping/Jensen
  mutations, both v6.2 raw/batch underflow mutations, the v6.3 positive-first
  zero-second mutation, the signed v6.4 pre-square mutation, and the v6.5
  finite-marginal square-overflow mutation.  Every public path rejects.
- Probed both signs immediately below and at the smallest resolved-square
  boundary, and at the last-finite/first-overflow square boundary.
- Verified exact signed cancellation passes while a one-minimum-subnormal
  residual of individually normal dyadic products rejects.
- Exercised nonfinite unit entries, coordinate/norm forgeries, off-tagged and
  exact/float-mismatched weights, product overflow, `fsum` overflow,
  nonfinite recorded values/tolerance/discrepancy paths, signed negative
  zero, and zero/nonzero disagreement.
- Confirmed the comparison is local: a discrepancy of 16 ULPs passes and 17
  ULPs rejects on both sides of the minimum-normal scale.
- Rechecked one genuine envelope point in each of all 16 strata.

The independent verifier and its eight-test regression suite produce the
same result under normal Python and `python3 -O`.  The producer's eight tests
also pass in both modes.  Full CLI preflight runs in both modes exit zero and
produce semantically identical preflight-only records; only measured wall
time and peak RSS differ.

## Frozen artifacts and commands

| artifact | SHA-256 |
|---|---|
| v6.6 driver | `69698f7766d9077bd5026dee8fc1e065b762a1f3d344ea2b7af0282763ce21f9` |
| v6.6 builder | `17176dab64811a0832c253eb9e0f964903bba951e0734a289731fc98f0d13739` |
| v6.6 producer tests | `fb4d2c2d898c54365c5281557563ecd348481485ec62e2c6f859606cd43b5e29` |
| v6.6 specification | `5b056a37d9a7e8d1acfef9264ea009739debcc06df4690abbda15472fbfe8f6b` |
| v6.6 gate | `fa1019605ef6b5efd486b234451806efcf1912f7b3f181c9511839d873b63bf6` |
| independent verifier | `4d3698a2c5a4f39b2703980282f895fc44c6e1f0c6952865fb6d6dd6aad15825` |
| independent hostile regression | `36084f03d40dc63607a5c01afeb7b9414b32e2334c500ccc21d4324e67ca513b` |

Run from `prime-gap-236/`:

```bash
python3 agents/audit/verify_importance_d4_calibration_v66.py
python3 -O agents/audit/verify_importance_d4_calibration_v66.py
python3 agents/audit/test_importance_d4_calibration_v66_hostile.py
python3 -O agents/audit/test_importance_d4_calibration_v66_hostile.py
```

Each verifier prints `"status": "AUDIT PASS"`; each regression run passes
8/8.  No production chain was run during this audit.
