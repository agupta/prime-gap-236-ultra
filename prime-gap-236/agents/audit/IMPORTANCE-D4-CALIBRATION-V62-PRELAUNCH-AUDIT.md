# Frozen exact-whitened importance calibration v6.2 hostile audit

## Verdict

`AUDIT FAIL`

V6.2 replaces the inherited unit-scale tolerances with local-scale checks, but
it forms several means in binary64 before checking that a positive serialized
quantity survived the division.  A minimum-positive subnormal raw total (or
positive batch aggregate) can therefore round to zero.  Both sides of the
subsequent comparison are then zero, as is the local tolerance, and the
inconsistent record is accepted.

The audited gate SHA-256 is
`3642ace1f95b13e32259190ccb1690d726fcc2bd7cbda3298875a6f14d082bca`.
It remains production-disabled (`rigorous: false` and
`production_launch_authorized: false`).  No production chain was authorized
or run.

## Compact counterexample

Take four batches of two samples, so the sample count is eight, and let
`tiny = 0x0.0000000000001p-1022`, the minimum positive binary64 value.  Supply
zero batch first and second moments and set just the serialized raw first total
to `tiny`.  V6.2 computes

```text
raw/sample_count = tiny/8 = 0x0.0p+0
mean(batch means)          = 0x0.0p+0
local tolerance            = 0x0.0p+0
```

and `_validate_j_local_consistency` returns `True`.  The same failure occurs
with only the raw second total positive.  A third fixture sets one batch second
moment to `tiny` and the raw second total to `2*tiny`; both required averages
underflow to zero and are accepted.

The verifier also constructs the deterministic valid J, stratum-15 tiny-smoke
chain in memory, changes its four z means and seconds to zero, its raw z total
to `tiny`, and its raw z-second total to zero.  The public
`validate_chain_record` wrapper accepts the mutation.  The large serialized
chain is deliberately neither stored nor printed.

This is a fail-closed defect even though real D4 stratum-15 moments are much
larger than the minimum subnormal: the validator authenticates externally
serialized checkpoint records and claims its convention for all schedules.
An accepted positive-total/zero-batch record is not a valid regrouping of any
nonnegative sample sequence.

## Frozen artifacts

| artifact | SHA-256 |
|---|---|
| v6.2 driver | `031f244728fd5ff4df041bb50bfa006bd3bab6724d2c9e3bb82298882f54c63a` |
| v6.2 gate | `3642ace1f95b13e32259190ccb1690d726fcc2bd7cbda3298875a6f14d082bca` |
| independent verifier | `2c503f9f1b9c7e5d9ae9c3c99faf96ee4c2798a12746b3f307e4ca9564d0684b` |
| desired regression | `bb2a1aa0689d1d351fb094e4cb2b3133ba6e5fd3e267423766cff5f8c1dc0dd8` |

The verifier checks the frozen v6.2 driver, builder, producer test,
specification, gate, and desired-regression hashes; invokes the gate's full
47-source/six-data dependency validation; confirms the gate is disabled; and
reproduces all three short counterexamples plus the public-wrapper mutation.

## Commands and outcomes

```bash
python3 agents/audit/verify_importance_d4_calibration_v62.py
python3 -O agents/audit/verify_importance_d4_calibration_v62.py
```

Both exit zero and print the same compact `"status": "AUDIT FAIL"` result.

```bash
python3 -m unittest agents/audit/test_importance_d4_calibration_v62_underflow.py
python3 -O -m unittest agents/audit/test_importance_d4_calibration_v62_underflow.py
```

Both intentionally fail all four assertions (`3` test methods, one with two
subtests): v6.2 raises no `ArithmeticError`.

The frozen producer suite still passes 8/8 in normal and optimized mode.  That
confirms this is an omitted hostile case, not a failure already detected by
the producer tests.

## Required successor repair

Before division, a successor must authenticate raw totals directly against
their batch regroupings and reject every positive numerator or positive batch
aggregate whose required division rounds to zero.  The rule is needed for
both first and second J moments and for the aggregate of batch squares.  It
must also retain the v6.2 local-scale/Jensen protections, pin this report,
verifier, and regression verbatim, rebuild a disabled gate, and undergo a
fresh normal/`-O` hostile audit before production authorization.
