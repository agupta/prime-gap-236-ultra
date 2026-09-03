# Conditional-envelope screen for the full capped D12 coefficient space

Status: **new mechanism; algebraic design only; no run and no quotient**.

## Claim under test

The transferred full-simplex D12 vector has C10 quotient
`0.9709698476...`, but the selected six-coordinate deterministic Ritz
correction gained only `4.62e-6`.  Neither calculation estimates the optimum
of the complete 272-dimensional capped C10 polynomial space.  This route asks
whether reoptimizing the global orbit coefficients themselves, rather than
multiplying the inherited vector by a low-degree stratum polynomial, produces
a rational vector with `48J/I>1`.

This is incompatible with the fixed-base multiplier route: its trial
functions need not be divisible by the inherited polynomial and can move its
interior zero set.  Sampling is discovery only.  Every selected vector still
requires a fresh grouped recurrence and then an exact or outward-rounded
certificate.

## Exact conditional-envelope identities

Let `Phi_1,...,Phi_272` be the explicit no-ones D12 orbit basis on the C10
support, and let `F_0=sum c_i Phi_i` be the byte-pinned inherited vector.  Pick
an index `p` with `c_p != 0` and replace `Phi_p` by `F_0`; this is an exact
invertible rational change of basis.  Apply fixed nonzero rational scale
factors and denote the resulting independent functions by

```text
G_0 = F_0, G_1, ..., G_271.
```

The change-of-basis matrix, pivot, scales, and inverse must be serialized and
checked exactly.  Numerical rank decisions are forbidden at this step.

On the I stratum `D_r`, put

```text
v_i(t) = G_i(t),             g_I(t) = sum_i v_i(t)^2,
I_ij,r = integral_Dr v_i v_j,  I_0,r = integral_Dr F_0^2.
```

Sample the conditional density proportional to `g_I` and write its
expectation as `E_I,r`.  With the separately pinned base weights
`w_I,r=I_0,r/I_0`, the following identity is exact:

```text
I_ij/I_0 = sum_r w_I,r * E_I,r[v_i v_j/g_I]
                              / E_I,r[F_0^2/g_I].                 (1)
```

For the common-coordinate J stratum `C_r`, let

```text
m_i(u) = integral G_i(u,x) 1_T(u,x) dx,
g_J(u) = sum_i m_i(u)^2,
J_ij,r = integral_Cr m_i m_j,  J_0,r = integral_Cr m_0^2.
```

Sampling the conditional density proportional to `g_J` gives the second exact
identity

```text
48 J_ij/(48 J_0) = sum_r w_J,r * E_J,r[m_i m_j/g_J]
                                      / E_J,r[m_0^2/g_J],         (2)
```

where `w_J,r=J_0,r/J_0`.  Thus neither unknown envelope normalizer is needed.
For either envelope, every diagonal observable lies in `[0,1]`, every
off-diagonal observable has absolute value at most `1/2`, and the base
denominator observable lies in `[0,1]`.  Zeros of all coordinates have zero
envelope measure.  Equations (1)--(2), unlike ratios `G_i/F_0` or `m_i/m_0`,
remain bounded at cancellation zeros of the inherited vector.

The C10 D12 Decimal100 transfer artifact supplies discovery normalizers by
stratum.  Their scale convention (`I_r`, but unscaled `J_r`) must be checked
against the serialized totals before use.  They are not exact certificate
inputs.

## Representation and cost control

At one point, all orbit-basis values must be produced by a shared
downward-closed exponent dynamic program, not 272 separate orbit expansions.
All distinguished-coordinate polynomials must likewise be expanded once and
integrated branchwise for the complete basis.  Exact signed `k=2,3` fixtures
must compare every component with brute-force orbit enumeration and literal
antiderivatives.

Accumulating every outer product naively in Python is too expensive.  Within
each batch, store a dense scaled feature block and use one deterministic
matrix multiplication `X^T X`; stream batches so no complete chain sample
array is retained.  Record the raw antisymmetric discrepancy before
symmetrization.  A matrix-free alternative is permitted only if it fixes the
sketch vectors before samples and validates the eventual candidate on an
independent chain split.

The initial screen uses the exact 12-dimensional D4 global basis as an oracle
and measures point/marginal evaluation time.  A D12 launch is permitted only
if count-scaled wall time is at most two hours and projected peak RSS is at
most 1 GiB.  Otherwise first use a fixed 48-coordinate residual/sketch space;
do not silently reduce the 272-dimensional claim after observing samples.

## Predeclared statistical and continuation gates

Use at least four independent chains in every positive I and J stratum, the
same tempering and fixed-stratum proposal audit as the repaired importance
calibration, and at least 20 batches per chain.  Before a D12 run:

1. the complete sampled D4 matrices must contain every exact oracle entry in
   their predeclared simultaneous bands and reproduce the exact D4 generalized
   root;
2. all structural entries, factor-48 conventions, support decisions, branch
   intervals, and permutation tests must pass normal and `python -O`;
3. every retained conditional moment must pass split-R-hat and batch-means
   ESS gates, and every envelope denominator must have a positive
   six-standard-error lower endpoint;
4. candidate selection and validation must use disjoint predeclared chain
   replicates, followed by leave-one-validation-chain reconstructions; and
5. no stochastic matrix or numerical eigenvalue may enter a theorem checker.

A fresh scalar C10 recurrence is authorized only if the validation estimate,
every leave-one-validation-chain quotient, and a conservative simultaneous
lower endpoint all exceed `1.005`.  Rationalize the selected vector on a
predeclared grid, prune only by a threshold fixed before the scalar run, and
serialize the complete expanded 272-vector.  The scalar recurrence must then
reconstruct the actual caps without importing sampled matrix entries.

If the fresh scalar display exceeds one, rerun at a second precision and then
build a cache-free exact or directed-rounding checker for that one rational
vector.  Until those steps give `I>0` and `48J-I>0`, this mechanism proves
nothing about `H_1`.

## Falsification criteria

Retire this implementation, rather than retune it post hoc, if the D4 oracle
calibration fails; if bounded-observable identities fail on any exact signed
fixture; if a basis/change-of-basis dependency is handled numerically; if a
tail stratum is omitted; if training-to-validation loss exceeds one quarter
of the apparent gain above the inherited quotient; or if the two independently
repeated seeded runs disagree outside their serialized arithmetic and timing
fields.  A negative sampled D12 result is data, not an upper bound for the
272-dimensional exact pencil.
