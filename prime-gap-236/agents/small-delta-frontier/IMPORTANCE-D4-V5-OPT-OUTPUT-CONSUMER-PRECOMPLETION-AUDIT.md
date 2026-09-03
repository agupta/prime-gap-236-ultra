# Importance D4 v5 optimized-replication output consumer audit

## Verdict

**SCOPED PRE-COMPLETION PARITY AUDIT PASS.**  No optimized production result
or optimized checkpoint was opened.  The optimized consumer is byte-for-byte
the repaired normal consumer after exactly six declared text substitutions:
its documentation label, authorization path, production-result path,
record-directory path, authorization SHA, and run-specific invalid predecessor
auditor SHA.

| Object | SHA-256 |
|---|---|
| optimized consumer | `319d9e2c8aa09c7d6ab1dfe54ba0624519953e9e6ac84e6bf15bd8c603bff642` |
| optimized parity tests | `49c145664946e4cff48a84b7ec66e8630aad112e47d66618917b204ea69990e6` |
| optimized authorization | `26f8da920c032d9fdf1f0000a65cec26894f07a47d17ba675b1f2ca2f6e117c9` |
| shared decision table | `3660ae47168ccbadb8cfa2cb2152deecf64321f9cd78ba2df1d4a0f8a68c29b4` |
| normal consumer used as parity reference | `7a0685f089125654f5faddced809cce784f9b7aabfd9c4ae8e669771710ab2da` |

The optimized authorization strict-parses as the same production schema and
binds the same driver/gate to the distinct canonical
`importance_d4_calibration_v5_records_opt` inode.

## Checks

- A unified source diff contains only the six declared substitutions.
- The parity test performs the inverse substitutions and requires exact source
  equality with the normal consumer; thus all three repaired hostile mechanisms
  (external self binding, import-cache/module binding, trusted-directory
  output exclusion, three-key publication closure, and explicit
  `analysis_failure` emission) transfer without reimplementation.
- Optimized authorization, output, and record names are distinct from the
  normal run.  The external output-completion and consumer-self tokens are
  validated before any live read.
- Tests pass 3/3 under both normal Python and `python3 -O`.

## Scope

This is a static derivation/parity audit only.  It does not inspect optimized
records, produce a decision, or establish statistical agreement between the
normal and optimized runs.  A root-supplied completed optimized-output SHA is
still mandatory, and any emitted audit needs a fresh post-completion review.
The normal-run partial-byte exposure recorded in the companion report was not
used in this parity audit and no optimized live path was read.
