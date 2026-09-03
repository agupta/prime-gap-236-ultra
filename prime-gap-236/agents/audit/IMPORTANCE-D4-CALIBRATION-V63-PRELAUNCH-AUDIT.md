# Frozen exact-whitened importance calibration v6.3 hostile audit

## Verdict

`AUDIT FAIL`

V6.3 successfully closes the v6.2 loss of a positive numerator during
averaging, but it enforces only one direction of zero-status consistency: it
rejects a positive second moment with zero first moment, not a positive first
moment with zero second moment.  The inherited v6.2 Jensen tolerance is an
operation-count multiple of a subnormal ULP, so it can erase a one-ULP Jensen
contradiction.

The audited gate SHA-256 is
`b5098156a85f6b94d3c8f2c000839e4fa1de680c439800ee6736eccc8c22ce16`.
It remains production-disabled and makes no rigorous or theorem claim.  No
production chain was authorized or run.

## Smallest counterexample mechanism

Let

```text
h   = 0x1.0000000000000p-537
h^2 = 0x0.0000000000001p-1022
```

so `h^2` is exactly the minimum positive binary64 number.  For four batches of
two samples, serialize every batch z mean as `h`, every batch z-second mean as
positive zero, the raw z total as `8*h`, and the raw z-second total as zero.
All raw/batch totals regroup exactly, and no positive average underflows.
Nevertheless these moments cannot come from real observations because
`mean(z^2) >= mean(z)^2 = h^2 > 0` in every batch.

V6.3's pre-total validator returns `True`.  The inherited local Jensen check
also returns `True`: its subnormal allowance is 136 ULPs for the two-sample
batch, while the contradiction is one ULP.  The public wrapper accepts the
same four-field mutation of a deterministic valid J, stratum-15 tiny-smoke
record.  The verifier constructs that record in memory and does not serialize
or print it.

## Findings that passed

The fresh verifier confirms that v6.3 rejects all previously frozen attacks:

- v6's stratum-specific z-second upper-bound violation;
- v6.1's raw/batch scale mismatch and zeroed batch second moment at the real
  stratum-15 scale;
- v6.2's positive raw numerator and positive batch numerator that vanish on
  averaging.

It also confirms that signed negative zero and overflowing positive batch
sums fail closed.  The gate pins all three v6.2 failure artifacts verbatim and
validates its complete 54-source/seven-data dependency sets.

Normal and optimized producer tests pass 8/8.  Normal and optimized preflight
runs emit zero records with `rigorous: false` and `theorem_ready: false`.
Production invocation without authorization and a record directory exits one
without creating output.

## Frozen artifacts

| artifact | SHA-256 |
|---|---|
| v6.3 driver | `32030ecb5eaa2f73983309a20563a8702abfe9a4c0d22a2675936e7d802d9830` |
| v6.3 gate | `b5098156a85f6b94d3c8f2c000839e4fa1de680c439800ee6736eccc8c22ce16` |
| independent verifier | `6302c8f8d9dbc2e557081784e359fb811ca4b1d1998aa69955169029fd1dfe6b` |
| desired regression | `0aa8fa5c9db51d3c433e6e1ecefaa740883c4b1282e09fbff7504ffa78934b65` |

## Commands and outcomes

```bash
python3 agents/audit/verify_importance_d4_calibration_v63.py
python3 -O agents/audit/verify_importance_d4_calibration_v63.py
```

Both exit zero and print the same compact `"status": "AUDIT FAIL"`, including
`"all_predecessor_counterexamples_closed": true` and the accepted new
counterexample.

```bash
python3 -m unittest agents/audit/test_importance_d4_calibration_v63_zero_second.py
python3 -O -m unittest agents/audit/test_importance_d4_calibration_v63_zero_second.py
```

Both intentionally fail 2/2 assertions because v6.3 raises no
`ArithmeticError`.

## Required successor repair

A successor must enforce zero-status equivalence for nonnegative J moments,
both per batch and after aggregation: a first moment is zero if and only if
its corresponding second moment is zero.  It must prevent subnormal ULP
allowances from hiding a positive Jensen gap, retain the v6.3 direct-total and
underflow checks, pin this report/verifier/regression verbatim, rebuild a
disabled gate, and receive another fresh normal/`-O` hostile audit before any
production authorization.
