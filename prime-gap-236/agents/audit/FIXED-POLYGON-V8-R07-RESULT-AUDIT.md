# Fixed-polygon v8 r=7 result audit

Verdict: **RESULT AUDIT PASS**, scoped to the single exact common-count
`r=7` mixed-form shard.  This is not an aggregate, quotient, compact
certificate, final certificate audit, or proof of `H_1<=236`.

Audit time: 2026-09-03 13:36 CEST.

## Frozen inputs

- result:
  `agents/exact-projection-engine/results/d14_grid38_scaled_b_fixed_polygon_v8/common_r_07.json`,
  SHA-256
  `8636441adc493afae16daaa81e60cd3bad5e1b63ce362391c7067e57fddece18`;
- producer:
  `agents/exact-projection-engine/d14_grid38_scaled_b_shard_fixed_polygon_v8.py`,
  SHA-256
  `36a8e027c83cabb272aa28a5d542dc571793cbcf90c5ca48787bc20092a55b72`;
- fixed-polygon core:
  `agents/exact-projection-engine/fixed_polygon_moments.py`, SHA-256
  `4100a9eeb86563ae84bf02ed4df9a2a5b696b5cc9ff163d15ac482b242b637bb`;
- structural/result checker:
  `agents/audit/verify_fixed_polygon_v8_cross_shard.py`, SHA-256
  `ec0162a73381d031e4ab7b5d8cb1fa16381e41f19c74a6fd74aafa0c30a8655c`;
- independent result test:
  `agents/audit/test_fixed_polygon_v8_r07_result_independent.py`, SHA-256
  `29356873ea293cb2a639230781772696bf2400090ed748b0bbdda0f373dec988`.

The result is strict canonical JSON, is 22,858 bytes with one hard link, and
pins 29 live source/test artifacts.  The independent test rehashed every
serialized source path and the externally pinned checker.  The result bytes
and source closure remained unchanged across the audit.

## Independent exact checks

The audit parses all exact values with a separate canonical-rational parser.
For both high and low distinguished-coordinate endpoints it finds exactly
the four scheduled branches

```text
Lbig, Ltotal, Sdelta, Stotal.
```

Writing their exact values as `high_*` and `low_*`, the independent
calculation verifies

```text
scaled_b_shard = 48 * (sum(high_*) - sum(low_*))
```

with no floating-point operation.  The reduced result is positive, has
numerator/denominator bit lengths `2372/2480`, and its canonical rational
string has SHA-256
`23b614688e9a011ffaf03bbc09861f9c2af428dc19f3c36619e06496bcba562c`.
Its decimal display `3.9069477689553464e-33` is diagnostic only.

The count is exact integer `r=7`, `k=48`, and the independently derived
maximum live shift is `H=14-r=7`, hence eight shifts `0..7` in every branch.
The active family list is exactly `large, small, small_total`.  Summing the
eight branch-stat records independently gives `317,128,584` scalar products
and `42,032` surviving product monomials, agreeing with both checker modes.
The factor 48 occurs once in the recombination above.

## Mode, mutation, and byte-binding checks

Fresh normal and optimized invocations used `-B -I` and distinct absent
private bytecode-cache prefixes.  They produced byte-identical audit records,
both with SHA-256
`951414e9ed0cad4d65f55ac9d73fd9855ba2d917558897eb6fc4392c5e34e675`,
and both bind `input_sha256` to the result hash above.  They also match the
two preserved normal/optimized audit records byte for byte.

The independent suite confirms fail-closed rejection after separately
mutating the exact scalar, one branch value, the polygon-core source pin, the
common count to the Boolean alias `true`, and the top-level schema.  It also
confirms that an existing output path is never overwritten.  Static control
flow plus the test show that the checker parses the shard into one byte
snapshot, performs all shard arithmetic from that parsed snapshot, and emits
the hash of those same bytes; the nested checkers and arithmetic modules are
loaded before the live source-closure recheck.  Start/end hashes agree, so no
mixed-state or path-replacement event occurred in this audit.

Commands executed successfully:

```text
python3 -B -I -X pycache_prefix=/tmp/r7-independent-normal agents/audit/test_fixed_polygon_v8_r07_result_independent.py
python3 -O -B -I -X pycache_prefix=/tmp/r7-independent-opt agents/audit/test_fixed_polygon_v8_r07_result_independent.py
```

Each prints:

```text
2/2 independent fixed-polygon-v8 r7 result suites passed
```

## Scope

This pass establishes only that the published r7 bytes satisfy the frozen
v8 result contract and their exact branch values recombine correctly.  It
does not reconstruct the expensive integral from first principles, does not
supply any missing `r=0..6` shard, and does not establish the final sign.
