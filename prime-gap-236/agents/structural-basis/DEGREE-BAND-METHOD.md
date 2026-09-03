# Exact total-degree band compression

For an orbit label `(a, lambda)`, write

```text
G_(a,lambda)(t) = (1-sum_i t_i)^a P_lambda(t),
deg(a,lambda) = a + |lambda|.
```

Let a rational discovery vector be

```text
F = sum_(a,lambda) c_(a,lambda) G_(a,lambda).
```

Fix a core degree `D0` and define, over the rationals,

```text
F_core = sum_(deg(a,lambda)<=D0) c_(a,lambda) G_(a,lambda),
H_d      = sum_(deg(a,lambda)=d) c_(a,lambda) G_(a,lambda)  (d>D0).
```

Then the identity

```text
F = F_core + sum_(d>D0) H_d
```

is coefficient-by-coefficient.  Since `F_core` lies in the complete no-ones
space `B_D0`, the small subspace

```text
B_D0 + span_Q {H_(D0+1), ..., H_D}
```

contains the original eigenpolynomial exactly.  Consequently its Rayleigh
supremum is at least the exactly checked quotient of that polynomial.  No
eigenvalue perturbation or floating-point inference enters this containment.

This compression does **not** reduce the number of expanded monomials required
to reconstruct one fixed quadratic form.  Its role is to reduce the search
dimension and to expose a direct reconstruction path: `fixed_vector_cut.py`
combines `F^2` and the conditional marginal polynomial before performing any
support moments, and never reads a serialized dense matrix.

## C10 instances

For the C10 full-simplex no-ones `D=10` rational vector, `D0=4` gives the 12
core labels and six functions `H_5,...,H_10`, hence an 18-function subspace
containing the 139-term polynomial.  Generate the exact data with

```bash
python3 prime-gap-236/agents/structural-basis/code/make_degree_bands.py \
  prime-gap-236/agents/exact-integrator/results/hb_c10_fullsimplex_noones_D10_decimalexact.json \
  --core-degree 4 \
  --output prime-gap-236/agents/structural-basis/results/c10_D10_degree_bands.json
```

The capped-support fixed-vector calculation is reconstructed by
`code/fixed_vector_cut.py`; its D4 regression is exact and agrees
coefficient-for-coefficient with the independent pairwise matrix recurrence.

For the exact full-simplex D12 vector, the same construction gives the 12 D4
core labels and eight functions `H_5,...,H_12`, hence a 20-function subspace
containing the 272-term polynomial.  Its exact decomposition is

```text
results/c10_D12_degree_bands.json
SHA-256 29d38a9e7ca7a352560c0a01813f2dfd2f477ec8cb829c433cce18d8229d31e9
source SHA-256 719c656e6e45388273b4c27f51f7a18b33e9ed1abb5f883e6fcc5de5d6d64a87
```

The band sizes are `7,11,15,22,30,42,56,77`; an independent loader and
coefficientwise audit checks all 272 terms in `D12-INPUT-AUDIT.md`.

An earlier evaluator integrated each expanded orbit group over every face
separately.  It reached only 20 of 1,575 I groups in about 6.5 minutes, with no
useful intermediate certificate, so that granularity was stopped as a concrete
runtime falsification.  The active reconstruction instead combines the whole
fixed polynomial on each `(r,h)` face and integrates once.  If the fixed capped
quotient misses 1, `DEGREE-BAND-FALLBACK.md` specifies a value-and-gradient
face traversal and a blocked bilinear construction for optimizing all 20
coordinates without 210 independent full runs.
