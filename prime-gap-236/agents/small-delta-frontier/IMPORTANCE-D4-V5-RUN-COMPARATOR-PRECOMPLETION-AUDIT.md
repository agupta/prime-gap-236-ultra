# Importance D4 v5 normal/optimized comparator precompletion audit

## Verdict

**SCOPED PRECOMPLETION AUDIT PASS** for comparator source SHA-256
`16f1373875477c0ae93f16ce035adcfff90537e8cdc7a1ec0d009b97d060b0f6`.
No normal or optimized production/audit result, and no checkpoint, was opened
by this audit.  This verdict covers the static parser, exact mathematical
comparison, synthetic provenance/race regressions, and output publisher; it is
not a comparison of the two realized runs.

The producer tests have SHA-256
`37f7ba350428c0ea4bbbbc16e321664ab7098e6e875d4128f9424dad2098f28b`
and pass 3/3 under both normal Python and `python3 -O`.  The independent hostile
suite has SHA-256
`47840b69a3e8962059737b3c23d57a782b8207ec3fa1dd171bdd28a3266b9ac7`
and passes 4/4 in both modes.

## Repaired counterexamples

The first candidate accepted matching normal/optimized payloads with arbitrary
result statuses, pass-looking audit decisions, and arbitrary claimed auditor
hashes.  A later frozen candidate still accepted a fully schema-consistent pair
whose common convention was `k=47`; the independent regression at its original
SHA `22e35dde...` failed identically in normal and optimized mode.  It also did
not compare an audit's claimed production-result device/inode with the actual
file snapshot.

The audited revision now:

- requires exact canonical convention SHA
  `43c7a2d225f5ee676ee345194219f9460a5a24135a7ccc052de47368a92efde2`
  and schedule SHA
  `7d618324c2167e2eaf8caf8ba7c6a097a881ef23e8d35350469c78ea182fe755`;
- rejects the preserved `k=47` and `chains_total=127` mutations;
- derives the expected 128 ordered checkpoint leaves independently; they agree
  exactly with the frozen gate schedule and have sorted-name canonical SHA
  `28ee32b094fc04a7f3c2b047a042c1b7fc7b0286131a060b42c1cb57134762a7`;
- validates result status from the `analysis`/`analysis_failure` alternative,
  then checks decision and exit code against the fixed table;
- pins normal/optimized auditor SHAs `7a0685f0...` and `319d9e2c...`, their
  run-specific superseded hashes, NumPy identity, scope, and exact failure/core
  fields;
- passes each actual result snapshot's four-key path/SHA/device/inode binding
  into comparison and requires exact equality with the corresponding audit;
- permits only the declared authorization/checkpoint/resource provenance
  differences and otherwise requires exact mathematical payload equality; and
- publishes through an owned `O_EXCL` descriptor, rebinds all input bytes and
  the canonical parent, then reopens the final output and verifies its inode and
  hash.  The late foreign-inode replacement regression fails closed without
  damaging the foreign file.

## Reproduction

From the repository root:

```text
python3 agents/structural-basis/tests/test_compare_importance_d4_calibration_v5_runs.py
python3 -O agents/structural-basis/tests/test_compare_importance_d4_calibration_v5_runs.py
python3 agents/small-delta-frontier/audit_compare_importance_v5.py
python3 -O agents/small-delta-frontier/audit_compare_importance_v5.py
```

All four commands pass at the hashes above.

## Scope and remaining gate

The comparator must still receive root-supplied byte SHAs for both completed
results and both completed v3 audit artifacts.  A future comparison artifact
needs a fresh postpublication review.  This static PASS makes no statement
about whether the optimized replication completed, whether the two stochastic
runs agree, or whether any sieve quotient is rigorous.
