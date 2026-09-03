# Importance D4 v5 completed-output consumer: pre-completion audit

## Verdict

**SCOPED PRE-COMPLETION AUDIT PASS AFTER THREE REPAIRS.**  No production
result or checkpoint was opened during this audit.  The verdict applies only
to the frozen consumer plumbing and decision policy below; it does not predict
which decision a completed run will receive.

| Object | SHA-256 |
|---|---|
| `agents/structural-basis/code/audit_importance_d4_calibration_v5_output.py` | `4e9ab0002b3f33019162d537f03310880e0ff788d48b36239957d05cb9608cf7` |
| `agents/structural-basis/tests/test_audit_importance_d4_calibration_v5_output.py` | `3b5694bfb1497d4ec25ce3f990b949d17489a2962a55d6404a308383b0d66085` |
| `agents/structural-basis/results/importance_d4_calibration_v5_decision_table.json` | `3660ae47168ccbadb8cfa2cb2152deecf64321f9cd78ba2df1d4a0f8a68c29b4` |

The consumer explicitly supersedes invalid auditor
`906a2f8ec92bc6b083ff4f36ebe19f6523382c22fa2d7c6ed56e7417abaf6f01`.

## Repaired counterexamples

1. **Unbound auditor bytes.**  The first consumer dynamically reported and
   closed over whatever hash its own file had late in execution.  A modified
   consumer could therefore bless itself.  The repair requires a canonical
   caller-supplied expected auditor SHA before any production path is opened,
   checks it again after analysis, writes that exact value into the report,
   and includes it in publication closure.
2. **Python import-cache substitution.**  Preloading a fake
   `importance_statistics` module made the first consumer execute fake
   functions while the gate still successfully hashed the correct disk file.
   This was reproduced explicitly: `accepted_fake_module True` and
   `disk_gate_hash_passed True`.  The repair requires a standalone process
   with no preloaded local or NumPy modules, then checks canonical file paths
   and gate hashes for all eight imported importance modules.  It also binds
   NumPy version 2.2.4 and the installed `numpy/__init__.py` hash.
3. **Audit output inside the trusted record directory.**  A new audit-output
   leaf under the authorized record directory was not an exact-path alias, so
   it could add a 129th file while the directory inode and all 128 checkpoint
   hashes still passed.  The repair canonicalizes the fresh output path before
   any production read and rejects the record directory and all its
   descendants, as well as exact trusted-input aliases.

All three failures are permanent normal/optimized regressions.

## Static checks

- The root must supply both the completed production-result SHA and the frozen
  consumer SHA before the first production-result read.
- The v5 driver, gate, authorization, and predeclared decision table are pinned
  to their frozen bytes.  The consumer records the rejected predecessor hash.
- The decision order is exactly pass, extension eligible, retired, or
  implementation rejected, with exit codes 0, 2, 3, and 1.  None implies a
  rigorous error bound, exact sieve quotient, or `H_1 <= 236`.
- The authorized directory is opened by its bound canonical inode.  Its leaf
  names must be exactly the scheduled 128 checkpoints.  Every checkpoint is
  reopened through that held directory descriptor, strict-parsed and checked
  against its scheduled chain identity, byte hash, inode, and the binding
  serialized in the final result.
- Embedded records must equal the reopened checkpoint records.  Analysis and
  status are recomputed and must equal the serialized values.  Gate,
  authorization, result, all checkpoints, the exact leaf-name manifest,
  decision table, auditor, local arithmetic modules, and NumPy runtime are
  represented in the output audit or its publication closure.
- The audit output is fresh-only and published by the already audited v5
  held-directory/O_EXCL writer.

## Tests

```sh
cd /home/anish/code/prime-gap-236-ultra/prime-gap-236
python3 agents/structural-basis/tests/test_audit_importance_d4_calibration_v5_output.py -v
python3 -O agents/structural-basis/tests/test_audit_importance_d4_calibration_v5_output.py -v
```

Both modes pass 8/8 tests.  These are deliberately pre-completion tests and
do not read the live result or record directory.

## Scope and remaining trust boundary

- **Output-blindness incident after the pre-completion tests.**  While locating
  the separately named optimized consumer, I ran the overbroad command
  `rg -n "d67005ba|26f8|optimized|opt" agents/structural-basis/code
  agents/structural-basis/tests agents/structural-basis/results | head -n 160`.
  Because the search included the live results tree, it printed part of
  `importance_d4_calibration_v5_records/J_r00_rep2_initial.json`.  I did not
  parse, hash, compare, analyze, or use any printed value and stopped broad
  searches immediately.  This does not change deterministic production bytes
  or the static consumer verdict, but it disqualifies this auditor from a
  wholly output-blind normal-run post-completion verdict.  Root must run the
  frozen consumer, and a separate auditor/optimized replication must supply
  post-completion evidence.  All subsequent commands are restricted to
  explicit frozen code, test, authorization, and report paths.
- The recomputation is an independent read of all checkpoint bytes but uses
  the same frozen production driver/analyzer.  It is not a second statistical
  implementation; the independent prelaunch algebra and hostile audit of that
  driver remain part of the trust chain.
- NumPy is bound by version, package entry path, and `__init__.py` hash, not by
  hashes of every compiled extension or the Python interpreter itself.  This
  is discovery-only numerical infrastructure.
- A well-formed completed-output SHA is an external root completion token.  A
  caller must not invoke the consumer on a partial output merely by supplying
  the partial file's hash.
- Any completed production result and emitted audit artifact require a fresh
  post-completion review.  Even `CALIBRATION_PASS` only permits a separately
  authorized D12 discovery run; any finite candidate still needs exact or
  outward-rounded dyadic reevaluation.
