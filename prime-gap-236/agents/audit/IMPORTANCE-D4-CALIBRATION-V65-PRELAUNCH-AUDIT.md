# Frozen exact-whitened importance calibration v6.5 hostile audit

## Verdict

`AUDIT FAIL`

V6.5 closes the v6.4 pre-square loss for both signs and correctly handles
resolved signed cancellation.  It does not check that the recomputed square
is finite.  A finite weighted marginal can overflow when squared; the later
ULP tolerance then becomes infinity, and Python's `inf > inf` comparison is
false.  The public wrapper accepts rather than failing closed.

The audited gate SHA-256 is
`5aec092841721a8e54292eb631e43c5e298088960e4031e7528df6272def905a`.
It remains production-disabled and makes no rigorous or theorem claim.  No
production chain was authorized or run.

## Compact overflow counterexample

Use the real adapter and its real tagged weights.  Supply a finite 96-entry
unit tuple with only `unit[0] = sys.float_info.max` nonzero.  Since the real
stratum-zero tagged weight is `2^-7`, v6.5 computes

```text
weighted_m0       = 0x1.fffffffffffffp+1016  (finite)
weighted_m0^2     = inf
```

`_weighted_m0_and_square` returns this pair instead of raising.  In the public
wrapper probe, let the frozen predecessor return the same tuple with recorded
`point.z = 1/8`.  V6.5 then obtains

```text
comparison discrepancy = inf
comparison tolerance   = 16 * max(ulp(1/8), ulp(inf)) = inf
discrepancy > tolerance = false
```

and accepts the point.  The tuple deliberately violates the predecessor's
unit-norm invariant; that is precisely why the new arithmetic guard must
validate its inputs rather than allow a nonfinite derived quantity to turn a
mismatch comparison into a pass.

## Findings that passed

The independent verifier confirms:

- all frozen v6 through v6.3 record attacks reject;
- the v6.4 pre-square underflow rejects for positive and negative weighted
  marginals;
- positive and negative tagged-product underflow reject;
- exact cancellation of the two allowed tagged channels is accepted as zero;
- both signs pass at the exact smallest-normal square boundary;
- the complete 68-source/nine-data gate closure is intact, all v6.4 failure
  artifacts are pinned, and runtime record validation reaches v6.5.

The frozen producer suite passes 5/5 in normal and optimized mode.  These
tests do not exercise the nonfinite derived-square path.

## Frozen artifacts

| artifact | SHA-256 |
|---|---|
| v6.5 driver | `6e6e74569dc707fc384b6774cd96d9407dcd7176ce1115ca395201d02dd12945` |
| v6.5 gate | `5aec092841721a8e54292eb631e43c5e298088960e4031e7528df6272def905a` |
| independent verifier | `5ca07de73cc4f10cabe9cc2d3e61c2c1b7bc0f2088041ba4301ebf834c7d0b7b` |
| desired regression | `f400f250b6485a4d77f02a346eae319cea3f4283acadf5630d32c5aa873c8ad2` |

## Commands and outcomes

```bash
python3 agents/audit/verify_importance_d4_calibration_v65.py
python3 -O agents/audit/verify_importance_d4_calibration_v65.py
```

Both exit zero and print identical compact `"status": "AUDIT FAIL"` output.

```bash
python3 -m unittest agents/audit/test_importance_d4_calibration_v65_square_overflow.py
python3 -O -m unittest agents/audit/test_importance_d4_calibration_v65_square_overflow.py
```

Both intentionally fail 2/2 assertions because neither the helper nor public
wrapper raises `ArithmeticError`.

## Required successor repair

A successor must reject nonfinite tagged products, sums, weighted marginals,
squares, recorded z values, tolerances, and discrepancies before ordering
comparisons.  It should enforce the predecessor's unit-coordinate and norm
bounds locally, and reject square overflow before multiplication.  It must
retain every earlier guard, pin this report/verifier/regression verbatim,
rebuild a disabled gate, and receive another fresh normal/`-O` hostile audit
before production authorization.
