# Importance-sampled Ritz discovery around a fixed exact vector

## Scope

**Audit supersession.**  The global-chain calibration described below is
blocked for the full stratum space: exact D4 tail masses make its
missing-stratum gate infeasible, and the direct J ratios can have unbounded
variance at cancellation zeros.  `IMPORTANCE-STRATIFICATION.md` gives the
only currently authorized discovery repair: conditional chains in every
stratum and the bounded `sum_i m_i^2` J envelope.  Neither design supplies a
finite-sample unbiased MCMC estimator or a proof certificate.

This is a discovery mechanism, not a certificate and not a source of a
rigorous error bound.  It is intended to rank finite, explicitly rational
multiplier spaces around the already reconstructed C10 D12 polynomial
`F_0`, without rebuilding the 272-term orbit products for every trial.
Every selected vector must still be reevaluated by the grouped
multiprecision code and, if positive, by an independent exact or outward-
rounded checker.

The earlier uniform-simplex Monte Carlo probe is not reused: its four D4
replicates ranged from `0.7561` to `4.3806` against the exact comparator
`0.9348269...`.  The proposal below samples from the two *quadratic-form
densities themselves* and uses the known exact base forms as normalizers.

## Exact ratio identities

Let `D` be the C10 support, let

\[
 I_0=\int_D F_0(t)^2\,dt,
 \qquad m_0(u)=\int F_0(u,x)1_D(u,x)\,dx,
 \qquad J_0=\int m_0(u)^2\,du .
\]

For an explicit multiplier list `H_0=1,H_1,...,H_s`, define

\[
 G_i(t)=F_0(t)H_i(t),\qquad
 m_i(u)=\int G_i(u,x)1_D(u,x)\,dx .
\]

On the zero sets of `F_0` and `m_0` define the ratios below arbitrarily;
those sets have zero measure for the corresponding probability laws.  Put

\[
 d\mu_I(t)=I_0^{-1}F_0(t)^2 1_D(t)\,dt,
 \qquad
 d\mu_J(u)=J_0^{-1}m_0(u)^2\,du,
\]

and `R_i(u)=m_i(u)/m_0(u)`.  Then, identically,

\[
 A_{ij}=I(G_i,G_j)=I_0\,\mathbb E_{\mu_I}[H_iH_j],             \tag{1}
\]

\[
 B_{ij}=48J(G_i,G_j)=48J_0\,\mathbb E_{\mu_J}[R_iR_j].       \tag{2}
\]

Thus a Monte Carlo calculation estimates only dimensionless correlation
matrices.  It must hard-code neither an independently estimated `I_0` nor
an independently estimated `J_0`; it imports their byte-pinned values from
the audited C10 base artifact.  In particular `(A_00,B_00)` must reproduce
those base values by construction.

For the stratum-polynomial family, use

\[
 H_{R,a,b}(t)=1_{\#\{j:t_j>\delta\}=R}
              (L(t)/\alpha)^a(Z(t)/\alpha)^b,
\]

or rational piecewise Bernstein polynomials in the two slacks
`B_R-L` and `alpha-L-Z`.  For each common point `u`, every `m_i(u)` is a
one-dimensional integral of a polynomial over at most four explicit branch
intervals.  It should be evaluated analytically in floating point from the
same branch partition as Definition 5, not by an inner Monte Carlo loop.

## Markov kernels

Both target laws live in a simplex with an extra slack coordinate.  A
reversible proposal chooses two of the physical/slack coordinates and
redistributes their fixed sum uniformly.  Reject if the candidate leaves
the cap support; otherwise use the Metropolis ratio

\[
 \min(1,F_0(t')^2/F_0(t)^2)
\]

for `mu_I`, or `min(1,m_0(u')^2/m_0(u)^2)` for `mu_J`.  Mixtures must include
physical--physical and physical--slack moves.  Independent chains start
from separately generated uniform-simplex points accepted by the cap, then
use a short tempering ladder from density power zero to one.  Log absolute
values are used for acceptance to avoid overflow.

No effective-sample-size estimate is allowed to rely only on within-chain
autocorrelation.  The discovery report must include at least eight chains,
split-R-hat for every retained matrix entry or for a conservative spanning
set, batch-means ESS, acceptance rates for both proposal types, and repeated
solves after deleting each chain in turn.

## Required falsification tests

1. On signed `k=2` and `k=3` fixtures, analytic marginal evaluation agrees
   pointwise with the literal one-variable polynomial integral on every
   branch and at both one-sided boundary limits.
2. At C10 D4, the sampled matrices for the constant, affine and quadratic
   multiplier spaces contain the independently exact matrices within
   predeclared simultaneous confidence bands.  Failure on any of these
   comparators retires the sampler.
3. Replacing the target-density sampler by uniform-simplex sampling must
   reproduce the already observed variance failure, so an accidental fallback
   cannot masquerade as the new method.
4. Permuting all 48 coordinates leaves every evaluated basis value and
   support decision unchanged.  The distinguished-coordinate marginal test
   is repeated after at least five coordinate permutations.
5. Chains initialized in different feasible large-count strata must mix to
   consistent stratum probabilities.  A missing stratum is a hard failure,
   not a zero estimate.
6. The estimated `A` and `B` are symmetrized only after recording the raw
   antisymmetric discrepancy.  A negative realized denominator for the
   proposed vector, unstable generalized root, or chain-deletion shift above
   one quarter of the apparent gain rejects the proposal.
7. A selected multiplier is serialized as a finite rational list before the
   fresh grouped evaluation.  The stochastic matrices and eigenvalue are not
   accepted by any theorem checker.

## Decision gate

First reproduce all three exact C10 D4 comparator spaces.  The initial D12
screen is allowed to authorize one fresh grouped scalar run only if

* all diagnostics above pass;
* every leave-one-chain-out quotient exceeds `1.005`; and
* the lower end of a conservative simultaneous batch-means interval exceeds
  `1.002`.

These thresholds are discovery cost controls, not confidence statements and
not mathematical bounds.  A candidate failing them remains numerical data
only and does not consume a production exact run.

## First implemented component

`code/importance_point_eval.py` (SHA-256
`e006f998d285119cc534612fbfdfa69beea8f807c2b7d2000c396f0aabac0022`)
evaluates the orbit-symmetric polynomial at a point by a downward-closed
exponent-multiplicity dynamic program.  It does not enumerate the orbit and
does not divide by repeated-part factorials after the fact; equal exponents
are unordered in the state, while unequal exponents are assigned in every
coordinate order.  The four-test suite
`tests/test_importance_point_eval.py` (SHA-256
`1e9e129827a0a456c71d248e51fd33b5586330722a4400ba879feb187e3999c5`)
passes in normal and optimized modes.  It checks exact Fraction equality to
brute-force orbit enumeration for repeated and unequal parts, exact
permutation invariance, the complete 272-label D12 input under a nontrivial
48-coordinate permutation, and malformed-input rejection.  The same module
now expands `t -> F_0(u,t)` exactly, constructs the two feasible distinguished
intervals directly from the strict large-coordinate convention and the cap
schedule, and analytically integrates every `(R,a,b)` multiplier channel.  A
signed rational two-variable fixture checks all small/large constant, `L`, and
`Z` branches against literal antiderivatives; pointwise polynomial values are
also checked at four rational distinguished-coordinate values.

The expanded seven-test suite
`tests/test_importance_point_eval.py` (SHA-256
`126cdaa8c28d88c6c02ee188fbe351f409b266858a38d2b618e5ff3a2db4fdca`)
passes in normal and optimized modes.  This closes pointwise normalization
and analytic one-coordinate marginal evaluation.

`code/importance_sampler.py` (SHA-256
`23f5a09d5eb0bd8aaae3ecf13c7cd6584b082e97d05ac11ab7d528586fc5074b`)
implements the physical/physical and physical/slack redistribution kernel and
the unnormalised-log-density Metropolis rule.  Its six-test suite (SHA-256
`a8e3d6e23c87d727f87d28b8fbf5309cf321f173d911b75a7511c409b98dc623`)
passes in normal and optimized modes.  Exact Fraction forward/reverse moves,
constant-density acceptance, density and support rejection, the power-zero
tempering endpoint, seeded reproducibility, simplex preservation, and invalid
arguments are covered.

The D12 density adapters, tempering/multi-chain coordinator, D4 statistical
calibration, and all convergence diagnostics remain unimplemented, so no
stochastic quotient has been run.
