# V6.7 records-only recovery hostile audit

Date: 2026-09-03 (Europe/Berlin).

## Verdict

`AUDIT PASS`, scoped only to recovery of the 128 frozen v6.6 checkpoint
records.  It is safe for the root to create one explicit authorization with
the frozen builder and then run the byte-pinned records-only recovery.

This verdict does not authorize a new chain, make the recovered Monte Carlo
analysis rigorous, inspect or endorse a quotient, or permit any mathematical
use without the predeclared exact reconstruction.

The shipped authorization artifact remains a template with
`authorized=false`; no recovery result was published during this audit.

## Independent checks

- Rehashed the frozen recovery driver, builder, producer tests, specification,
  and unauthorized template.
- Reopened the original v6.6 gate, authorization, rejection sentinel, and
  held record-directory inode.  All 128 exact scheduled leaves, checkpoint
  SHA-256 digests, devices, and inodes equal the template manifest in canonical
  schedule order.
- Trapped every inherited chain-execution entry point while loading and
  validating the records.  Static AST inspection also finds no chain call in
  either recovery source or authorization builder.
- Rebound every loaded local runtime module to the gate-pinned path and bytes.
- Located, without reporting any estimator/root value, exactly one actual
  serializer repair path:
  `$.hard_gates.constant_coordinate_sums_one`.
- Verified that the replacement serializer agrees with the legacy serializer
  on representative preexisting cases, converts `numpy.bool_` recursively,
  and still rejects unrelated unknown types.
- Exercised a hypothetical authorization only through preflight/binding:
  changing one checkpoint binding fails, and selecting the record directory
  as output parent fails.  No full jackknife recovery or publication ran.
- Confirmed the external self-hash check and false-template rejection occur
  before records-only execution can proceed, and preloaded local runtime
  modules are rejected in a fresh interpreter.
- Producer tests pass 9/9 and independent hostile tests pass 6/6 under normal
  Python and `python3 -O`.  Independent checker outputs are byte-identical in
  both modes.

## Frozen audit artifacts

- verifier: `agents/audit/verify_importance_d4_calibration_v67_recovery.py`;
- hostile regression:
  `agents/audit/test_importance_d4_calibration_v67_recovery_hostile.py`;
- verifier result:
  `agents/audit/results/importance_d4_calibration_v67_recovery_audit.json`.

Replay from `prime-gap-236/`:

```bash
python3 agents/audit/verify_importance_d4_calibration_v67_recovery.py
python3 -O agents/audit/verify_importance_d4_calibration_v67_recovery.py
python3 agents/audit/test_importance_d4_calibration_v67_recovery_hostile.py
python3 -O agents/audit/test_importance_d4_calibration_v67_recovery_hostile.py
```

Authorization, if root chooses to proceed, must use exactly the audited
source/builder bytes, one fresh authorization path, and one fresh output leaf.
The emitted authorization SHA should be recorded before invoking recovery.
