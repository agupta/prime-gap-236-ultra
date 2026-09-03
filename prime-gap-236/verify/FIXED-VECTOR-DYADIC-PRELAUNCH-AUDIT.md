# Fixed-vector dyadic driver: pre-launch audit

Date: 2026-09-02

Verdict: **SCOPED AUDIT PASS AFTER THREE REPAIR ROUNDS**. This verdict covers certificate
plumbing before a target run. It is not a positive sieve certificate, does not
audit every primitive in the dyadic arithmetic backend a second time, and does
not replace the required independent reconstruction and output audit.

## Frozen files

- Driver: `verify/check_c10_d12_fixed_vector_dyadic.py`, SHA-256
  `1759db7e6c03bc25fb9b0d3826413f548deb3dff8bb87a7bc5b6869c2d6556ed`.
- Hostile tests: `verify/test_c10_d12_fixed_vector_dyadic.py`, SHA-256
  `533cbb264709d2a17196903f827fa31dfbed11e1c5c30849374253b5d219b000`.
- Integer-directed interval ring: `verify/dyadic_interval.py`, SHA-256
  `f6f1730f77ba490f04326338e7b3bfe5ab2e5c6438f10892bdf3f5bfe6fc875d`.
- Dyadic grouped-backend adapter: `agents/exact-integrator/dyadic_backend.py`,
  SHA-256
  `1dae20016b5fcbde5f56cf222ce92b45899f14bd5ff07fd3c70b7b10ce4ce608`.
- Grouped evaluator: `agents/exact-integrator/grouped_fixed_vector.py`, SHA-256
  `47167e92a0f346e969706dc282ccb2dfd4ac31a0a75b654938ffbe8423cf4a4a`.
- Exact recurrence dependency:
  `agents/exact-integrator/src/exact_integrator.py`, SHA-256
  `941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52`.
- Input/parser reference: `verify/exact_capped_certificate.py`, SHA-256
  `1787e7b482a5c2982de56486bc774794f6e671b3db4d9ab7207ebb1c85dc079c`.

## Checks performed

The input loader reads the candidate once under a required SHA-256, rejects
duplicate JSON keys and noncanonical rationals, reconstructs the complete 272
element no-ones degree-at-most-12 basis, and keeps each coefficient paired with
its ordered label. If `L` is the coefficient-denominator LCM and `g` is the
integer content, the evaluator uses the primitive integer vector

\[
 z_i=(L/g)c_i.
\]

Thus both quadratic forms are multiplied by the same positive factor
`(L/g)^2`; the quotient and the sign of `48J-I` are unchanged. The real source
regression recovers a 714-bit LCM, content one, 272 labels, and ordered payload
SHA `8ea54de0e3bb4d9f978fee80a6788c81d542a7d6839ed8c69e22a5374845fe4e`.

The driver rebuilds all 5,929 required orbit products and uses the pinned
grouped evaluator on the literal C10 support. It requires the target traversal
counts `1575` I groups, `312` I faces, `695` marginal components, and `1200` J
domains. The numerator is constructed as the interval product
`DyadicInterval(48) * J`. Acceptance is exactly

\[
 I_{\rm lo}>0\quad\hbox{and}\quad (48J-I)_{\rm lo}>0.
\]

All interval fields are serialized with exact dyadic integer endpoints and
canonical rational reconstructions. The I stage has an exact field schema and
is consumed only under a required byte hash. It binds the input hash, primitive
vector hash, support, precision, shadow precision, dependency hashes, worker
count, traversal direction, and driver hash. The input, stage, driver, and
dependency closure are rebound at the end of the relevant phase. Stale stage
or result destinations receive a non-certificate sentinel before parsing or
long work begins.

The first reviewed version attempted to reverse nonexistent private hooks on
the pinned grouped evaluator, so `--reverse-faces` raised `AttributeError`.
The frozen driver repairs this with a namespaced `OrderedGroupedEvaluator`
whose serial I and J methods reproduce the pinned aggregation formulas while
reversing the complete list of `r` blocks. Reverse mode rejects multiple
workers. The regression now exercises the actual order and the rejection gate;
the pinned grouped implementation is unchanged.

The second reviewed version had two additional fail-closed counterexamples.
First, Python equality allowed Boolean `true` endpoint metadata to compare
equal to the integer one, so a staged interval whose integer bounds represented
`[1,1]` but whose rational endpoint fields were Boolean could be accepted.
Every serialized endpoint is now required to be a nonempty string with
canonical integer and `Fraction` spelling before the exact dyadic identity is
checked. Second, I/J closure hashes were checked only before the result write;
a mutation triggered by the write itself could leave an accepted-looking file.
The frozen driver rehashes the input, stage/result, driver, and full dependency
closure after publication. A postwrite mismatch replaces the apparent result
with `theorem_ready: false` failure data and raises. Recursive metadata
comparison is type-exact, so `true` cannot substitute for `1`. Timing and RSS
metadata are deliberately required to be finite and nonnegative (child RSS and
mocked clock increments may legitimately be zero); strict positivity is
required only for `I.lo` and the accepted margin lower endpoint.

Independent commands run from `prime-gap-236/`:

```text
python3 -m unittest verify.test_c10_d12_fixed_vector_dyadic
python3 -O -m unittest verify.test_c10_d12_fixed_vector_dyadic
python3 -m py_compile verify/check_c10_d12_fixed_vector_dyadic.py verify/test_c10_d12_fixed_vector_dyadic.py
```

Both test modes report `Ran 9 tests ... OK`; compilation passes. Tests include
the real-source scaling identity, content removal, duplicate/noncanonical input
rejection, interval serialization mutations, the factor-48 strict lower-margin
gate, real reverse traversal, the serial-worker gate, and stale-output
replacement. They also include Boolean endpoint/metadata attacks and a
post-publication input mutation which must replace the apparent result by a
failure sentinel.

## Prepared target launch template

The candidate and its exact SHA must replace the two placeholders. Use fresh,
distinct stage and result paths and retain their byte hashes.

```text
python3 verify/check_c10_d12_fixed_vector_dyadic.py \
  <CANDIDATE_JSON> \
  --expect-input-sha256 <CANDIDATE_SHA256> \
  --phase i --precision 512 --shadow-bits 96 --workers 1 --progress \
  --stage verify/results/c10_d12_fixed_dyadic_p512.I-stage.json \
  --output verify/results/c10_d12_fixed_dyadic_p512.json

sha256sum verify/results/c10_d12_fixed_dyadic_p512.I-stage.json

python3 verify/check_c10_d12_fixed_vector_dyadic.py \
  <CANDIDATE_JSON> \
  --expect-input-sha256 <CANDIDATE_SHA256> \
  --phase j --precision 512 --shadow-bits 96 --workers 1 --progress \
  --stage verify/results/c10_d12_fixed_dyadic_p512.I-stage.json \
  --expected-stage-sha256 <I_STAGE_SHA256> \
  --output verify/results/c10_d12_fixed_dyadic_p512.json
```

A positive result must be rerun in reverse order (or independently at another
precision), audited byte-for-byte, and reconstructed by the independent
checker. In particular, this pre-launch audit does not license changing the
result's `theorem_ready: false` flag.
