# Green-v9 r=9 cross-engine result audit

Verdict: **RESULT AUDIT PASS**, scoped to the single Green-v9 common-count
`r=9` shard and its exact comparison with the already-audited fixed-polygon
v8 r9 reference.  This is not an aggregate, quotient, compact certificate,
final certificate audit, or proof of `H_1<=236`.

## Frozen artifacts

```text
Green result
agents/exact-projection-engine/results/d14_grid38_scaled_b_green_v9_crosscheck_r9/common_r_09.json
b6cb9eb5ccbb5d9ef73fc6637481efb5bf020846316487357a097272aaf56853

fixed-polygon-v8 reference
agents/exact-projection-engine/results/d14_grid38_scaled_b_fixed_polygon_v8/common_r_09.json
e9397f72f78f9ad53716d61bb3f10854a640081f81632028904836d6c6778d88

Green result checker
agents/audit/verify_green_v9_cross_shard.py
7dbb352011d840a5bddf8f6f101f864d0a1b1e436ff4ebb5533ef1137217b4a7

independent hostile test
agents/audit/test_green_v9_r09_result_independent.py
0acdbce0b4fda10137ce7d07e96f9f1157fed5856701164d6d3222fc425e8303
```

The Green result and v8 reference are strict canonical JSON of 22,721 and
22,556 bytes respectively.  Each has one hard link.  Their bytes remained
unchanged from the first independent hash through the final mutation test.

## Exact independent comparison

The independent checker does not import either polygon moment engine.  It
parses every branch value as a reduced canonical `Fraction` and verifies

```text
scaled_b_shard = 48 * (sum(high branches) - sum(low branches)).
```

There are exactly four branches at each endpoint: `Lbig`, `Ltotal`,
`Sdelta`, and `Stotal`.  The exact result is positive and identical to the
v8 reference, with numerator/denominator bit lengths `2338/2458`; its
canonical rational string has SHA-256
`a10c4d1f46a563ac7eb792152cdad00854d43e937943401afc78ef0bf005e9c8`.
The decimal display `8.01513442332438e-37` is diagnostic only.

The following exact mathematical/work fields are bit-for-bit equal between
Green v9 and fixed-polygon v8:

- `scaled_b_shard`, `kernel_stats`, `family_stats`, `geometry`, `candidate`,
  and `scaling`;
- high and low branch values and branch statistics;
- the complete fixed-denominator integer-radialization block.

Timing and RSS fields are deliberately excluded from this mathematical
comparison.  Independently, `k=48`, common `r=9`, maximum shift
`H=14-r=5`, six live shifts per branch, and active families
`large,small,small_total` all check exactly.  The branch work totals are
`233,384,424` scalar products and `31,524` surviving product monomials.
Every one of the Green result's 30 serialized source pins matched live bytes.

## Mode, mutation, and binding checks

Fresh normal and optimized checker invocations used isolated Python with
`-B -I` and distinct absent private bytecode-cache paths.  With the v8 r9
reference supplied, both produced the identical audit SHA-256

```text
45705683105f637d49b27f3e95332cdc6f94331ed99d1dddec3c03c0528c7c62
```

and matched both preserved audit records byte for byte.  The audit record
binds `input_sha256` and `reference_sha256` to the two hashes above and sets
both exact recombination and exact-reference equality to true.

Separate mutations of the Green scalar, a Green branch, the Green convexity
contract, the Green core source pin, and one exact v8 reference branch all
failed closed.  An existing output sentinel was not overwritten.  Since the
checker reads each result into one byte snapshot, emits the corresponding
hashes, and all loaded checker code plus live source closure remained stable,
no mixed target/reference state occurred in this audit.

Both commands passed:

```text
python3 -B -I -X pycache_prefix=/tmp/green-r9-result-normal agents/audit/test_green_v9_r09_result_independent.py
python3 -O -B -I -X pycache_prefix=/tmp/green-r9-result-opt agents/audit/test_green_v9_r09_result_independent.py
```

Each prints `2/2 independent Green-v9 r9 result suites passed`.

## Scope boundary

This cross-engine equality is strong result evidence for r9 only.  It neither
reconstructs the expensive integral independently nor validates any future
Green shard without a fresh audit.  Missing common counts and the final exact
aggregate/sign remain separate obligations.
