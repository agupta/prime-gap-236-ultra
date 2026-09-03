# Source-bound D12 transformed-multiplier target

Status: adapter/test candidate only.  No D12 chain, sampled quotient, fresh
scalar recurrence, or theorem claim is authorized by this file.

The target is the **unmultiplied** 272-label D12 polynomial with source SHA
`719c656e...d64a87`.  The computational input is its exactly common-scaled
integer copy SHA `8650e44c...f4a93`; every coefficient and the common scale
are checked in `Fraction`.  The negative D4-quadratic transfer SHA
`7e9f62fd...4978`, quotient `0.955596...`, is a rejection regression and is
never used as a target or normalizer.

The 16 I masses and 16 unscaled J masses come from the raw sparse-gradient
traversal SHA `0ac99ee5...d644d`, whose sole rejection was nine redundant
one-ulp half-array mismatches.  The substantive recovery SHA is
`6411f11d...56a43`; its producer, tests, and independent audit are also
byte-pinned.  The sum of I masses must match its denominator, and 48 times
the sum of J masses must match its numerator, to relative error at most
`1e-98`.  Both must match the independent grouped base SHA
`02e1a667...121d9` to relative error at most `1e-50`.  These are discovery
normalizers, not exact forms.

At every sampled I point the target density is the unmultiplied `F0^2`, and
the complete frozen 93-active-coordinate v6 transform is evaluated directly.
At every common J point all transformed marginals of `F0*H_i` are evaluated
analytically and the bounded envelope is their squared norm.  The exact
transformed constant weights reconstruct the physical F0 multiplier and
marginal.  Transforming an already estimated matrix is forbidden.

The eventual D12 screen is a separate driver; the D4 calibration driver does
not accept this target.  It must retain all 16 strata, four chains per target
and stratum, all v6 acceptance/R-hat/ESS/z/active-null/rank checks, and the
unchanged `1e-12` relative rank tolerance.  Replicates 0--1 are the fixed
training set and replicates 2--3 the disjoint validation set.  Candidate
selection may inspect only training records.  Validation, every deletion of
one validation replicate, and a conservative simultaneous lower endpoint
must respectively exceed the predeclared gates `1.005`, `1.005`, and `1.002`
before one separately authorized rational scalar input can be emitted.  A
failed/extension-only D4 v6 calibration forbids this screen.

The machine target gate additionally blocks a full screen unless timed D4
and D12 adapter smokes project at most 7200 wall seconds and 1048576 KiB peak
RSS.  The target gate itself always records `screen_launch_authorized=false`;
an audited passing D4 v6 result and a separate root authorization are both
external trust roots.

The fresh scalar consumer is
`agents/exact-integrator/stratum_quadratic_transfer_decimal.py`.  It takes the
pinned 272-term integer base separately and a complete 96-entry exact
multiplier JSON.  The latter has status
`exact-stratum-quadratic-rational-vector`, `rigorous_forms=true`,
`block_direct_bitwise_equal=true`, `k=48`, all labels
`[r,1/L/Z/L^2/LZ/Z^2]` for `r=0,...,15` in that order, and 96 canonical
rational coefficients.  A selected transformed vector `c_new` is converted
exactly to old coordinates as `T*c_new`; the three inactive entries are
explicit zeroes.  The transfer recurrence inserts this multiplier before I
integration and before marginal branch squaring, so it does not falsely
truncate the degree-14 product back into the 272-term D12 space.  It
reconstructs the actual caps without importing sampled matrix entries.
