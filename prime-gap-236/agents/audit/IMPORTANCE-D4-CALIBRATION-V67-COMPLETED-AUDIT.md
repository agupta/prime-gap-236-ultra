# v6.7 completed-recovery audit

Verdict: **AUDIT PASS OF REJECTED OUTPUT**.  The recovered file is an
authentic, reproducible fail-closed result.  It does not pass its frozen
calibration gates, authorize an extension, provide a rigorous matrix, or
support a candidate even as reliable heuristic sign evidence.

## Frozen inputs

- recovery driver: `agents/structural-basis/code/importance_d4_calibration_v67_recover.py`, SHA-256
  `118b56e6e7fe07c3a95ed1f49da6cbaf1c0352f5f9776526ea8bb5aa0d4782f8`
- recovery authorization: `agents/structural-basis/results/importance_d4_calibration_v67_recovery_authorization.json`, SHA-256
  `1656f18c9ce0601b08616ee072511cfc2caf89b3513f10115a3e3bf0c63a7bae`
- recovered result: `agents/structural-basis/results/importance_d4_calibration_v67_recovered_from_v66.json`, SHA-256
  `3ff38ac49371100c66777f321d993f00b8ba9ef673c42c1f41cb1c7b8ebf79b0`
- v6.6 driver/gate/authorization/rejection sentinel SHA-256:
  `69698f7766d9077bd5026dee8fc1e065b762a1f3d344ea2b7af0282763ce21f9`,
  `fa1019605ef6b5efd486b234451806efcf1912f7b3f181c9511839d873b63bf6`,
  `25c516af4cefacf08405632f38797f2e43d46a7275d1e07ee3f4202a192489c2`,
  `a4f8518b52de5fb9c79e58c770d0c861c7e283481d745c31b6a8a3802761d879`.

## Independent reconstruction

The checker reopened the v6.6 gate, authorization, rejection sentinel, held
record directory, and all 128 authorized checkpoint inodes and hashes.  It
trapped every inherited chain-execution entry point and the recovery
publication function.  It then reran the complete analysis, including the
deletion calculation, and required exact JSON-value equality with the entire
serialized analysis.

That equality includes every matrix, root, and deletion field.  The checker
does not print or copy any numeric root or quotient.  This prevents a rejected
search diagnostic from being promoted while still authenticating every byte
of the computation relevant to the verdict.

## Smallest rejection and independent failures

The sole false hard gate is `root_deletion_stability`.  In increasing degree:

- degree 0 relative discrepancy is
  `0x1.5f13fee1afa03p-9` (approximately `0.00267851`) and passes;
- degree 1 is already
  `0x1.96b74bfd44f30p-2` (approximately `0.397184`) and fails the frozen
  `1/200 = 0.005` limit;
- degree 2 is `0x1.ddc4676a8f2cfp+0` (approximately `1.86628`) and also fails.

All three exact reference values lie inside their respective six-standard-error
deletion intervals.  Thus the smallest hard failure is specifically the
degree-1 relative-discrepancy comparison, not a mislabeled interval test.

All four statistical gates fail independently:

- maximum split R-hat is `0x1.7f8addd310cd1p+0` (approximately `1.49821`),
  above `1.05`;
- minimum batch-means ESS is `0x1.5662a6967c560p+6` (approximately `85.5963`),
  below `200`;
- all 16 J-stratum denominator-precision checks fail;
- simultaneous coverage fails for both matrices.  The worst standardized
  discrepancies are `0x1.31ef56cf32c15p+4` (approximately `19.1209`) over
  336 I entries and `0x1.16cb3e4d1d7ffp+9` (approximately `557.588`) over
  876 J entries.

The latter maximum also exceeds the separate extension ceiling `12` by a wide
margin.  In addition, the hard-gate failure alone forbids extension.  Hence no
matrix or candidate from this recovered analysis is admissible even as a
calibrated heuristic.  The records remain reproducible raw data, but the
aggregate matrix/root inference is unusable for ranking, sign, or launch
decisions.

## Frozen independent artifacts and replay

- checker: `agents/audit/verify_importance_d4_calibration_v67_completed.py`,
  SHA-256 `f051baf7b50fcf83911c9df48c8bcffcf00b8533fce4cb1cbf800a723a1500d9`
- hostile regression: `agents/audit/test_importance_d4_calibration_v67_completed_hostile.py`,
  SHA-256 `ab5940247c65f8986ca4345fb371de94a403d57434eba60cbeced36d87d461e7`
- audit result: `agents/audit/results/importance_d4_calibration_v67_completed_audit.json`,
  SHA-256 `0e1daaaf8a368369744d087d809583b13e7f9ea3e84da5e07c9672a699bde986`

Run from `prime-gap-236/`:

```sh
python3 agents/audit/verify_importance_d4_calibration_v67_completed.py
python3 -O agents/audit/verify_importance_d4_calibration_v67_completed.py
python3 -m unittest agents/audit/test_importance_d4_calibration_v67_completed_hostile.py
python3 -O -m unittest agents/audit/test_importance_d4_calibration_v67_completed_hostile.py
```

Normal and `-O` checker outputs were byte-identical at SHA-256
`0e1daaaf8a368369744d087d809583b13e7f9ea3e84da5e07c9672a699bde986`.
The hostile suite passed 7/7 in both modes and rejects hidden gate flips,
threshold mutation, degree relabeling, false passage/extension, and an
inconsistent coverage maximum.
