# Frozen exact-whitened importance calibration v6.4 hostile audit

## Verdict

`AUDIT FAIL`

V6.4 closes every frozen record-level attack through v6.3, including both
directions of first/second zero-status disagreement.  It nevertheless checks
for underflow one operation too late.  The frozen envelope computes
`point.z = weighted_m0 * weighted_m0`; if that square has already rounded to
zero, v6.4's guard `if point.z > 0` is false and the lost positive quantity is
accepted as a genuine zero.

The audited gate SHA-256 is
`6fac38311cb0914761c15f8bbab6abca839bf622ab60418df2e9cde7eeb0c8ad`.
It remains production-disabled and makes no rigorous or theorem claim.  No
production chain was authorized or run.

## Reproducible pre-square counterexample

The verifier instantiates the real exact-whitened adapter, retaining its real
tagged weights.  In common stratum zero it supplies a structurally valid
96-entry marginal vector with

```text
marginal[0] = 0x1p-600
marginal[1] = 1
all other marginals = 0
real tagged weight[0] = 0x1p-7
```

The envelope normalization leaves those two relevant values unchanged at
binary64 precision.  Independently recomputing from the returned unit
marginals gives

```text
weighted_m0                    = 0x1.0000000000000p-607  (nonzero)
weighted_m0 * weighted_m0      = 0x0.0p+0
frozen envelope point.z        = 0x0.0p+0
```

The frozen envelope's reconstruction and exact-stratum upper checks pass.
V6.4 then returns this point instead of raising.  Subsequent observations
record both z and z-second as zero, so no record-level support check can
recover the information already lost.

This fixture uses a synthetic marginal vector to isolate the arithmetic
contract; it does not assert that the production Markov chain will encounter
that point.  The validator and point wrapper are explicitly fail-closed
prelaunch guards, so accepting a nonzero weighted marginal as exact zero is
enough to reject authorization.

## Findings that passed

The independent verifier confirms all of the following:

- every frozen v6, v6.1, v6.2, and v6.3 counterexample now rejects;
- positive zero passes, signed negative zero rejects;
- the minimum and maximum positive subnormals reject, while the minimum
  normal value passes the serialized-moment parser;
- a Jensen pair whose square is exactly the minimum normal value passes;
- point z immediately below the z-second normal boundary rejects, and values
  at and above that boundary pass;
- the complete 61-source/eight-data gate closure is intact and all v6.3
  failure artifacts are pinned verbatim.

The frozen producer suite passes 7/7 in normal and optimized mode.  These
successes do not cover the pre-square loss above.

## Frozen artifacts

| artifact | SHA-256 |
|---|---|
| v6.4 driver | `189177cec83727077e3ce21ae5e56264b08db4479ee8a20f5b5f36db9fb2cbdd` |
| v6.4 gate | `6fac38311cb0914761c15f8bbab6abca839bf622ab60418df2e9cde7eeb0c8ad` |
| independent verifier | `fd3370ae784a04b35f8846512de6db14c456049cb77a1ccd47f447e9eb166714` |
| desired regression | `3e387aca92ac30f14dff5f88d5c9de67f17d645e5776fbb0aa55def64890c517` |

## Commands and outcomes

```bash
python3 agents/audit/verify_importance_d4_calibration_v64.py
python3 -O agents/audit/verify_importance_d4_calibration_v64.py
```

Both exit zero and print the same compact `"status": "AUDIT FAIL"`, with all
predecessor and boundary checks true and the accepted pre-square failure.

```bash
python3 -m unittest agents/audit/test_importance_d4_calibration_v64_presquare.py
python3 -O -m unittest agents/audit/test_importance_d4_calibration_v64_presquare.py
```

Both intentionally fail the single assertion because v6.4 raises no
`ArithmeticError`.

## Required successor repair

Before trusting `point.z`, a successor must independently recompute
`weighted_m0` from the adapter's tagged weights and the returned unit
marginals.  It must reject nonzero `weighted_m0` whenever its square is zero
or subnormal, and locally authenticate `point.z` against that recomputed
square.  It must retain all v6.4 record and point guards, pin this
report/verifier/regression verbatim, rebuild a disabled gate, and receive a
fresh normal/`-O` hostile audit before production authorization.
