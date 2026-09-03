# D12 fixed-vector input audit

Date: 2026-09-01

This is a lightweight input/provenance audit.  It did **not** run the capped
fixed-vector integration or any moment recurrence.

## Verdict

`INPUT AUDIT PASS` for the two audited JSON artifacts and for the production
grouped evaluator's load path:

- The fixed-vector record has the expected strict schema, `k=48`, degree 12,
  and dimension 272.  Its labels are unique and are exactly the complete set
  of weakly decreasing no-ones labels `(a,lambda)` with
  `a+sum(lambda) <= 12`.  All 272 serialized rational coefficients parse
  exactly and all 272 are nonzero.
- The degree-band artifact has 12 degree-at-most-four core terms and bands of
  sizes `7, 11, 15, 22, 30, 42, 56, 77` in degrees 5 through 12.  Recombining
  its 272 entries as a map from labels to `Fraction` coefficients equals the
  source map coefficient-by-coefficient, with no duplicate or misplaced label.
- A dry run of the real `grouped_fixed_vector.py` CLI load path at the capped
  C10 parameters captured exactly the same ordered 272 labels and the same 272
  `Fraction` coefficients.  Orbit precomputation and `I`/`J` evaluation were
  replaced by capture stubs, so this check performs no integration.

No schema, label, coefficient, band, or load-path counterexample was found.

## Provenance hashes

| object | SHA-256 | check |
|---|---|---|
| D12 fixed-vector JSON | `719c656e6e45388273b4c27f51f7a18b33e9ed1abb5f883e6fcc5de5d6d64a87` | equals the degree-band `source_sha256` |
| D12 degree-band JSON | `29d38a9e7ca7a352560c0a01813f2dfd2f477ec8cb829c433cce18d8229d31e9` | pinned by the audit test |
| `src/exact_integrator.py` | `941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52` | equals the fixed-vector `integrator_sha256` |
| recorded exact matrices | `b882098bd6889ff251195b45153a2204e4df1c4ef843a2ae85dcc1b2fd3e041d` | provenance only; see below |
| grouped evaluator used by the dry load | `47167e92a0f346e969706dc282ccb2dfd4ac31a0a75b654938ffbe8423cf4a4a` | audit-time implementation hash |
| audit test | `9268a4b057b2e1959661cbd54d2c056d0ee2a2d125d03ba40d8957e44f3d611c` | six-test file below |

## Exact-margin limitation

The D12 JSON does not serialize either exact matrix.  The existing C10
full-simplex SQLite cache contains only 10,082 of the 37,128 lower-triangular
entries needed for a 272-dimensional quadratic form.  A concrete first missing
entry is `(i,j)=(141,71)`, for labels `(8,(3,))` and `(5,(2,2))`.
Consequently this audit did not reconstruct or re-hash the matrices and did not
claim a matrix-trusting regression.

As a weaker serialization-consistency check only, exact rational parsing gives

```text
stored numerator - stored denominator = stored exact_margin > 0
stored numerator / stored denominator = stored exact_quotient
exact_quotient_decimal = 1.0030189929241073
```

This reuses the stored quadratic scalars.  It is neither an independent matrix
regression nor a capped-support certificate.  If complete matrices are later
serialized, a quadratic-form replay from those matrices would still be only a
matrix-trusting full-simplex regression, not the required capped certificate.

## Reproduction

```sh
python3 -m unittest \
  prime-gap-236/agents/structural-basis/tests/test_d12_input_audit.py -v

python3 prime-gap-236/agents/exact-integrator/verify_degree_bands.py \
  prime-gap-236/agents/exact-integrator/results/hb_c10_fullsimplex_noones_D12.json \
  prime-gap-236/agents/structural-basis/results/c10_D12_degree_bands.json
```

Observed results: `Ran 6 tests ... OK` and `DEGREE-BAND IDENTITY PASS` with
272 expanded terms, 12 core terms, eight bands, and compressed dimension 20.
