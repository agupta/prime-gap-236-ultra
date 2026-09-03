# Hostile review of the degree-band gradient and line search

Date: 2026-09-01.  Reviewed discovery code:

- `../structural-basis/code/band_operator.py`, SHA-256
  `e4fbf7a97d061d362c32b54bf0d49a89c4195b965e96d7ab89a2581bc907c073`;
- `../structural-basis/code/band_line_search.py`, SHA-256
  `ab5a424873d5cbd8ab96cb19d6429a7f33c8858e9209c872bdc1548333300dde`.

This review concerns discovery integrity only.  Neither a jet result nor a
projected line-search result is a rigorous sieve certificate.

## Algebra checked

For expanded coefficient `f_p=w_p theta_owner(p)`, the code initializes the
jet derivative as `w_p e_owner(p)`.  Jet multiplication implements

`d(xy)=x dy+y dx`.

Consequently the grouped `I` and `J` traversals return

`(D,grad D,N,grad N)=(theta^T A theta,2A theta,theta^T B theta,2B theta)`

with `N=48J`.  Dividing the gradients by two therefore gives `A theta` and
`B theta`.  The inherited geometry is scalar; only polynomial coefficient
payloads are jets.  Scalar zero promotes to a jet only when the first nonzero
payload is added.  Current I/J construction makes every nonempty payload
polynomial homogeneous (all scalar or all jet), so inspecting the first
coefficient in `integrate_domain` is valid.

The full-simplex preconditioner correctly aggregates expanded labels into the
20 compressed directions.  For an orbit `P_nu` and residual power `b`, its
moment is

`orbit(nu) sum_c binom(b,c)c!prod(nu_i!)(1-alpha)^(b-c)
 alpha^(|nu|+k+c)/(|nu|+k+c)!`.

The stationary equation used by the line search is also correct.  For

`R(t)=(b0+2b1 t+b2 t^2)/(a0+2a1 t+a2 t^2)`,

its finite stationary points solve

`c0+c1 t+c2 t^2=0`, where

`c0=b1 a0-a1 b0`, `c1=b2 a0-a2 b0`, and
`c2=b2 a1-a2 b1`.

Five exact small tests passed, including fresh pairwise compressed matrices,
central polarization, Euler identities, scalar/grouped equality, and
serial/fork equality.  A fresh Decimal70 scalar-versus-jet test differed by
only `4.1e-69` and `7.3e-69` relatively in `I` and `N`, respectively; its Euler
errors were of order `1e-72`.

## Checks required on the gradient artifact

Before preparing a direction, reject unless all of the following hold:

1. status is exactly `multiprecision-degree-band-gradient-discovery`,
   `rigorous` is false, `complete` is true, and `decimal_dps>=90`;
2. source, degree-band, operator, grouped-evaluator, and imported-integrator
   hashes equal the pinned files; source `k` is 48 and its 272 labels reconstruct
   the 20-direction map coefficient for coefficient;
3. the six support parameters equal the intended C10 rationals, not merely
   numerically close decimals;
4. `theta`, `a_theta`, `b_theta`, and both gradient arrays have length 20, and
   every numeric token is finite; for this first pass `theta` equals the exact
   compressed source coordinate after Decimal conversion;
5. `a_theta=grad_denominator/2` and
   `b_theta=grad_numerator/2` componentwise;
6. denominator is positive, `quotient=numerator/denominator` to the stated
   precision, and the relative Euler residuals
   `|theta.grad-2Q|/|Q|` retain at least 50 clean decimal digits;
7. the exact traversal counts are the complete C10 counts (312 I faces, 1,200
   positive-measure J branch intersections, and the pinned orbit/component
   counts), and no calibration/face-limit flag is present;
8. `D`, `N`, and `N/D` agree for at least 50 significant digits with the prior
   independent scalar MP100 evaluation of the identical theta, input SHA, and
   support.  This comparison costs no new integration.

The current `prepare` command checks only a subset of these items.  In
particular it does not bind the dependency hashes and support parameters, does
not check vector lengths/Euler errors/baseline forms, and does not explicitly
check the positive `P` norm of theta.  These are fail-closed requirements for a
reusable driver; for the already running discovery they must be checked on the
completed artifact before it is consumed.

After solving for the correction `d`, additionally check and record scaled
residuals for `P d-r`, `theta^T P d`, and `d^T P d-1`.  Recompute at a second
precision and require stable direction coordinates and projected quotient.

## Checks required on the scalar direction and line search

The scalar direction result must be bound to the exact prepared input by SHA
and must have a recognized grouped-evaluator status.  Require the pinned
grouped/integrator hashes, all C10 parameters, `k=48`, dimension 272, complete
face/branch counts, positive `I(d)`, and (for a Decimal result) adequate
precision.  Recompute `48J`, the quotient, and the input expansion rather than
trusting their serialized fields.

The current `finish` command has important fail-closed gaps: it does not repeat
the gradient status/dependency/parameter checks; it does not bind the
source/band hashes at finish time; it does not verify that the direction input's
basis and 272 coefficients are exactly the expansion of the recorded 20-vector;
and it does not check the scalar direction result's status, dependency hashes,
support parameters, dimension, or traversal counts.  A counterfeit but
self-consistent direction input/result pair carrying the genuine gradient SHA
could therefore be accepted.  These gaps do not change the line-search
formula, but they must be closed before treating its output as an auditable
discovery artifact.

Also require the two-dimensional I Gram determinant
`a00*a11-a01^2` to be positive by a margin large compared with Decimal error.
Solve the stationary equation at a second precision and directly recompute the
reported projected quotient at every candidate root and at infinity.

## Cheapest independent directional check

No extra full D12 traversal is needed.  The scalar evaluation of the final
rationalized candidate `theta+t d`, which is mandatory anyway, supplies a
polarization check for both forms:

`A01_observed=(D(theta+t d)-D(theta)-t^2 D(d))/(2t)`,

`B01_observed=(N(theta+t d)-N(theta)-t^2 N(d))/(2t)`.

Compare these with `d dot Atheta` and `d dot Btheta` from the jet artifact.
This is the exact quadratic analogue of a directional finite difference and
tests the only new cross terms used by the projected line search.  It reuses
the already completed scalar theta run, the required scalar direction run, and
the required scalar candidate run.  If an earlier check is desired, one extra
scalar run at `theta+d` gives the same polarization identity; two separate
`theta+/-h d` runs are unnecessary.

The scalar candidate forms must also agree with the projected `2x2` forms at
the actual finite rational `t`, not merely have a similar quotient.  Failure of
either form equality retires the candidate even if rounding makes its quotient
look favorable.

## Rationalization and ledger status

The raw 230-digit Decimal coordinates should not automatically become the
final exact vector: doing so creates enormous denominators without adding
mathematical information.  First retain enough digits that a repeated
high-precision projected calculation and scalar grouped calculation preserve a
comfortable positive margin.  Then reduce/quantize the 20 compressed
coordinates, expand all 272 coefficients exactly, and repeat the scalar
multiprecision check before launching Fraction certification.  Only the final
Fraction run may decide the sign.

Use three distinct experiment statuses:

- `heuristic-gradient` for the 20-channel Decimal jet and projected line search;
- `mp-scalar-candidate` for an ordinary scalar grouped Decimal evaluation of a
  fixed rationalized vector;
- `exact-certificate` only for a Fraction reconstruction with positive exact
  denominator and positive exact `48J-I`, followed by independent audit.

A projected quotient, a jet quotient, or a scalar Decimal quotient must never
be entered in the certificate column or described as rigorous.
