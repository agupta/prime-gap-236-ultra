# Frozen exact-whitened importance calibration v6.1 hostile audit

## Verdict

`AUDIT FAIL`

V6.1 correctly repairs the v6 stratum-specific upper-bound omission, but it
inherits v5 raw/batch aggregation and Jensen tolerances with an absolute
`max(1, ...)` scale.  Those tolerances are between 27 and 41 orders of
magnitude larger than the common-stratum-15 J moments.  Consequently v6.1
accepts tail records whose raw sums do not reconstruct their batches and whose
positive first moments have zero second moments.

The audited gate SHA-256 is
`ff1b6c71bf07824180a822722bbf8a627c0e671f5a4034906ce6902348ece83d`.
It remains production-disabled.  No authorization or production directory was
created, no production chain was run, and no future production output was
read.  Only isolated preflight outputs were created below `/tmp`.

## Smallest counterexample: one field

Use the deterministic tiny-smoke record for target J, common stratum 15,
replicate 0 (`expected_chain_table()[124]`).  Frozen normal and optimized
Python both produce:

```text
exact Z_15                 = 1/288230376151711744
float Z_15                 = 3.469446951953614e-18
positive mean of z batches = 4.1364572664391454e-21
original raw_sum[-1]       = 3.309165813151316e-20
sample count               = 8
```

Change only `raw_sum[-1]` to canonical positive zero.  Do not change any batch,
second moment, matrix numerator, state, seed, acceptance count, label, or index.
Frozen v6.1 `validate_chain_record(...)` returns `True`.

This contradicts the required raw/batch reconstruction: the raw mean becomes
zero while every serialized z batch mean is positive.  The frozen v5
aggregation check uses `atol = 128*eps = 2.842170943040401e-14`, whereas the
entire discrepancy is only `4.1364572664391454e-21`.  V6.1's new local upper
check accepts zero because it checks range but not locally scaled aggregation.

The reconstructed J matrix, ratio, batch means, z precision, R-hat, and roots
do not consume this raw sum and are unchanged.  The raw moments do enter ESS,
so the accepted mutation can change a gate rather than being inert metadata.

## Independent second counterexample: Jensen erased

In the same valid record:

```text
batch_z_means[0]          = 4.1364572555519545e-21
batch_z_means[0]^2        = 1.7110278627008408e-41
batch_z_second_means[0]   = 1.7110278627008408e-41
```

Set only `batch_z_second_means[0]` to positive zero, then recompute the single
aggregate field `raw_second_sum[-1]` from the four batch seconds.  Frozen v6.1
again returns `True`, even though a positive batch mean requires
`mean(z^2) >= mean(z)^2 > 0`.  The inherited batch Jensen tolerance is
`256*eps*max(1, ...) = 5.684341886080802e-14`, about 27 orders of magnitude
larger than `Z_15^2 = 1.2037062152420224e-35` and about 27 further orders above
the realized squared mean.  V6.1's upper check accepts zero and supplies no
local-scale lower check.

Permanent desired regressions:

- `agents/audit/test_importance_d4_calibration_v61_tail_moments.py`
- SHA-256
  `339e3620adae4c13bac0a00499740462dd2a3647f821a4246dc7ef32d4d2d4e6`

Both tests deliberately fail on frozen v6.1 and must pass on a corrected
successor.

## Findings that passed

### Frozen hashes and predecessor binding

All five announced v6.1 hashes match:

| Object | SHA-256 |
|---|---|
| v6.1 driver | `3ecde36c901b2fb98bb0783ae77da7916e5e8bef062b9b3169b9f3b572f43409` |
| v6.1 builder | `c8e4f9b49ccbded02c2b75a7b669d6a818ee50d773ae58a47f7de301bcc6b8cd` |
| v6.1 tests | `7018e7e2d00610411981ff99e4897412346eee0fd914678993c5429d0a89a2d6` |
| v6.1 specification | `c172e640803cd5840d3c3cf2aa5e890f048fb2c9687f8c2a7f184ead6cf04c88` |
| v6.1 gate | `ff1b6c71bf07824180a822722bbf8a627c0e671f5a4034906ce6902348ece83d` |

The gate's exact 40-source/five-data path sets all match their live hashes.  It
pins the invalid v6 gate
`d7ab62d01cc873e732857f1662d40af53624aa1fe36abaaf58bacbe03729521b`
and the three frozen v6 failure artifacts verbatim:

| Artifact | SHA-256 |
|---|---|
| v6 hostile report | `2c2b3ec5887b982185624216d041ecf44531bb0da279271e05a1a77a11d06ff4` |
| v6 independent verifier | `b643bd7458e1ecdf3909d33a753fcabe83abbf9305d811d086a5d24030837ce7` |
| v6 desired regression | `b278c5a78513e2e5ed017cdff873a519cef44c40a49ed1e076b32dfae41edc3d` |

The strict gate schema, frozen schedule/thresholds, extension and continuation
rules, factor-48 data convention, false rigorous/theorem flags, and separate
authorization requirement remain intact.

### Exact transform and direct evaluation

The fresh verifier reran the independent primary-artifact parse, rational LDL,
triangular solve, block congruence, reversed-orientation discriminator, exact
base reconstruction, Decimal normalizer/factor-48 checks, and all-stratum
direct point/marginal evaluation from the v6 audit.  It again obtained:

```text
transform SHA-256 = f2a0e8325809956c6883191d04cde6bc67ea74c4af34f86dce7a1ac60c4ac1fb
active dimensions = 16 / 47 / 93
scaled pivots      = [1.0067330611129017, 3.982032130771286]
maximum J z bound = 1/8
```

The independent 16-entry bound table derived from exact base weights equals
`J_Z_BOUNDS_EXACT` entry-for-entry.  I direct evaluation remains bit-for-bit
equal.  Independently integrated direct J marginals differ by at most
`2.8297225067907106e-12` at floating evaluation order, and physical `m0` by at
most `2.294327694733049e-12`.  No aggregate matrix transformation is used in
these point checks.

### V6.1 wrapper and upper-bound repair

Runtime installation reaches the inherited driver, record validator, point
envelope, and conditional J log-density.  The record's stratum is first bound
to its frozen chain specification and local index map by the predecessor
validator; only then is it used to select the exact v6.1 bound.  Boolean,
negative, out-of-range, relabeled, and local-index-mutated records reject.
Missing z batch, z second, raw sum, or raw second fields reject.  J validation
without the transformed adapter rejects.

The exact bounds are correctly reconstructed from
`base_constant_weights_exact`, compared to the pinned table, applied at point
evaluation, and applied to every serialized batch and raw first/second upper
bound.  The original v6 mutation `batch_z_second > Z_r^2` now rejects.  Its
ULP-scaled upper-bound tolerances do not use a unit floor.  The remaining defect
is that the predecessor's separate aggregation and lower-Jensen checks still
do use a unit floor.

### Production/preflight closure

Normal and optimized preflight runs emit zero records with status
`d4-exact-whitened-calibration-preflight-only`, `rigorous: false`,
`theorem_ready: false`, and no authorization binding.  Production invocation
without both authorization and record directory exits nonzero before creating
the requested output.  No D12 screen or theorem claim is reachable from the
preflight gate.

## Commands and outcomes

Fresh independent verifier (both exit zero and print the same
`"status": "AUDIT FAIL"` findings):

```bash
python3 agents/audit/verify_importance_d4_calibration_v61.py
python3 -O agents/audit/verify_importance_d4_calibration_v61.py
```

Verifier SHA-256:
`ce527cf6176fe168fd0862be1189bdef0ccccbe96c48bc205327a53c3fbfe69c`.

Frozen v6.1 producer suite:

```bash
python3 -m unittest agents/structural-basis/tests/test_importance_d4_calibration_v61.py
python3 -O -m unittest agents/structural-basis/tests/test_importance_d4_calibration_v61.py
```

Observed: 6/6 pass in both modes (`4.978s`, `3.639s`).

New tail-scale regressions:

```bash
python3 -m unittest agents/audit/test_importance_d4_calibration_v61_tail_moments.py
python3 -O -m unittest agents/audit/test_importance_d4_calibration_v61_tail_moments.py
```

Observed: both tests fail in both modes with
`AssertionError: ArithmeticError not raised` (`1.846s`, `1.443s`).

Preflight commands used isolated, initially empty `/tmp` directories:

```bash
python3 agents/structural-basis/code/importance_d4_calibration_v61.py --gate agents/structural-basis/results/importance_d4_calibration_gate_v61.json --output /tmp/v61-audit-normal.IqrNri/preflight.json --mode preflight
python3 -O agents/structural-basis/code/importance_d4_calibration_v61.py --gate agents/structural-basis/results/importance_d4_calibration_gate_v61.json --output /tmp/v61-audit-opt.6zPlGA/preflight.json --mode preflight
```

Both exit zero with the preflight-only status and zero records.  The analogous
`--mode production` commands without authorization/record-directory arguments
both exit 1 with `v6 production requires authorization/record-dir`; neither
creates its output path.

## Launch consequence

Do not authorize frozen v6.1.  A successor must authenticate raw-vs-batch first
and second moments and raw-, batch-, and batch-aggregate Jensen inequalities at
the local stratum scale.  Its error terms must be derived from operation counts
and ULPs of the compared magnitudes, without `max(1, ...)` or another envelope-
independent floor, and must fail closed on underflow that erases a mathematically
positive square.  It must pin this report/verifier/regression, rebuild the gate,
and receive another fresh normal/`-O` hostile audit before authorization.
