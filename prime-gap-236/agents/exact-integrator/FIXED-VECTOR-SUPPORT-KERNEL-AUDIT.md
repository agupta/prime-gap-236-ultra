# Fixed-vector support-kernel audit

Date: 2026-09-02

Verdict: **SCOPED AUDIT PASS** for discovery infrastructure; this is not a
certificate-producer audit.

Audited artifacts:

- `agents/structural-basis/code/fixed_vector_support_kernel.py`
  SHA-256 `774b8f3a09d77d79d6e4abe56cce4ed1eb82fc5f71ca08cb033bd383091073a3`.
- `agents/structural-basis/tests/test_fixed_vector_support_kernel.py`
  SHA-256 `7662e0e8cb96998a7a9bd9552e63e4f2422c4b47fe56c76b96e9b788bcd87e59`.

Independent commands, both passing 5/5 tests:

```text
python3 agents/structural-basis/tests/test_fixed_vector_support_kernel.py
python3 -O agents/structural-basis/tests/test_fixed_vector_support_kernel.py
```

Formula checks:

1. The raw `I` contraction stores
   \(\sum_{i,j}c_i c_j m_{\lambda_i}m_{\lambda_j}\), using factor two only
   for distinct coefficient indices.  Translating a raw term of total slack
   degree \(d\) by
   \(\sum_{c=0}^d {d\choose c}(1-\alpha)^{d-c}(\alpha-\sum t_i)^c\)
   is exactly `GroupedEvaluator.square_residual_terms`.
2. The marginal kernel stores every distinguished-coordinate split as
   `(remaining_partition, distinguished_exponent, slack_exponent)`, with the
   original coefficient.  This is exactly the input needed by each
   support-dependent marginal polynomial.
3. For one branch, diagonal residual-partition pairs have factor one and
   distinct pairs factor two.  For two different unordered branches, every
   ordered cross product has factor two.  These agree with the reference
   branch polarization and do not double-count diagonal terms.
4. Orbit products needed by both the `I` contraction and all distinguished
   residual pairs are compiled.  Canonical lookup does not alter their
   structure constants.
5. Signed low-dimensional cases, a zero-dimensional marginal, two distinct
   supports, a nonconstant scheduled support, and serial versus two-worker
   replay agree exactly with a freshly constructed `GroupedEvaluator`.

Practical limitation: the reusable kernel is thin.  It precontracts fixed
coefficients and retains orbit-product tables, but support-dependent marginal
polynomials, branch-polynomial products, face densities and domains, and all
integrations are still rebuilt for every support.  Moreover,
`multiply_monomial_orbits` is already process-global `lru_cache` data.  The
kernel can reduce overhead in an in-process support scan, but the present
implementation does not provide a substantial asymptotic speedup for a D12
certificate reconstruction.

