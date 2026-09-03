# Varying the C10 support enlargement

## Status

This note isolates the analytic effect of changing the support enlargement
`epsilon_s` while retaining the audited C10 values of `A_1`, `delta`, and the
cap schedule.  The candidate `epsilon_s=7/2000` was selected by a float64
degree-2 proxy.  Its exact capped degree-4 falsification has now been completed:
it improves the exact rationalized particular-vector quotient over
`epsilon_s=1/200`, but remains decisively below one.  This says nothing about
the degree-12 ordering.

## Definition-1 checks

Keep

\[
 A_1=\frac{77747}{300000},\qquad \delta=\frac1{100},
 \qquad B_1=B_2=\frac3{20},\quad B_m=\frac{97}{625}\ (m\ge3),
\]

and set

\[
 \varepsilon_s=\frac7{2000}=\frac{1050}{300000},\qquad
 A_0=-\varepsilon_s.
\]

Then the denominator support endpoint and Definition-5 common-coordinate
cutoff are

\[
 \alpha=A_1+\varepsilon_s=\frac{78797}{300000},\qquad
 \eta=A_1-\varepsilon_s=\frac{76697}{300000}.
\]

The total interval still starts at zero.  The only changed scalar
Definition-1 margin is

\[
 \frac12-\varepsilon_s-A_1=\frac{71203}{300000}>0.
\]

Every `delta,B_m` condition and the list of feasible large-coordinate counts
is unchanged.  The same statement applies to the exact nonconstant schedule,
because that schedule also depends only on `delta` and the `B_m` values.

For completeness, the exact Definition-1 transition/emptiness reserves are

\[
 B_1-\delta=B_2-\delta=\frac7{50},\qquad
 B_3-\delta=\frac{363}{2500},
\]
\[
 B_3-B_2=\frac{13}{2500},\qquad
 B_2+\delta-B_3=\frac3{625}.
\]

The transitions `B_1=B_2` and `B_m=B_3` for `m>=3` use the weak lower
inequality permitted by Definition 1; their upper reserves are respectively
`1/100` and `1/100`.  Exactly the counts `1,...,15` are feasible, with

\[
 B_{15}-15\delta=\frac{13}{2500},\qquad
 16\delta-B_{16}=\frac3{625}.
\]

## Relevant-modulus exponent

For one support stratum, Definition 2 gives the two exact bounds

\[
 \log_x\!\left(e\prod f_i\right)
 \le (1-\varepsilon_0)(A_1-\varepsilon_s),\qquad
 \log_x\!\left(e'\prod f'_i\right)
 \le (1-\varepsilon_0)(A_1+\varepsilon_s).
\]

Adding them cancels the support enlargement:

\[
 q\le x^{(1-\varepsilon_0)2A_1}\le x^{2A_1}.
\]

Thus the direct Heath--Brown modulus endpoint, its
`omega=A_1-1/4`, and every Type-0, Type-II, and Type-III exponent condition are
identical to the audited `epsilon_s=1/200` argument.  The continuum partition
problems use only `delta` and the two cap schedules and are likewise unchanged.

The weighted-prime minorant, its mass, `c_1=c_2=0`, and
`beta=1/2>B_1` do not involve `epsilon_s`.  The repaired Proposition-1 proof
uses only that the support separation is a fixed positive number and that the
strict relevant-modulus exponent is below one; both remain true.  Consequently
the analytic C10 proof specializes to any fixed positive `epsilon_s` satisfying
`A_1<1/2-epsilon_s`, including `7/2000`.

## Computational consequence

At the original point,

\[
 \alpha-\eta=\frac1{100}=\delta.
\]

At the candidate point,

\[
 \alpha-\eta=\frac7{1000}\ne\delta.
\]

The research integrator already implements the general four marginal branches,
so it can test the candidate.  The independent target checker currently
specializes its ordered geometry to `alpha-eta=delta`; it must not be pointed
at this parameter by changing constants.  If this route produces a positive
exact candidate, an independent general-geometry preset and regression suite
are required before certification.

## Discovery evidence and falsification test

Using the identical degree-2, order-8, stratum-aligned quadrature code gives

| `epsilon_s` | heuristic `48J/I` |
|---:|---:|
| `1/1000` | `0.8510012614198819` |
| `1/400` | `0.8544709558661934` |
| `3/1000` | `0.8549924257573451` |
| `7/2000` | `0.8551796766981505` |
| `1/250` | `0.8550333650313265` |
| `1/200` | `0.8537682150600729` |

These values are only a ranking proxy.  The immediate falsification test is a
fresh exact 12-dimensional degree-4 capped matrix at `epsilon_s=7/2000`,
followed by a rational-vector evaluation.  No degree-12 run should be selected
from this table alone.

## Exact degree-4 result

The complete 12-dimensional no-ones degree-4 matrix was rebuilt cache-free
with exact rational moments at

```
k=48, alpha=78797/300000, eta=76697/300000, delta=1/100,
B_1=B_2=3/20, B_m=97/625 (m>=3).
```

The matrix has SHA-256
`868307f366effe807c70532463b923b94a80193903b885ab36bd311607f33fc4`.
The 160- and 240-digit generalized-eigenvalue discoveries agree on

\[
 0.896837259628928073309820817264039399061736\ldots.
\]

After coefficient rationalization with denominator bound `10^15`, exact
pair-matrix contraction gives

\[
 q_{7/2000}=0.8968372596289280733098208172640393990617363638566\ldots,
\]

so the exact particular-vector shortfall is

\[
 1-q_{7/2000}=0.1031627403710719266901791827359606009382636361434\ldots>0.
\]

An independent exact grouped traversal (20 I orbit groups, 312 I faces, 19
marginal components, and 1,496 J branch integrals) reconstructs exactly the
same `I` and `48J`, not merely the same decimal quotient.  Its artifact SHA is
`65fc03c97818b867b5d9ba4e3cc2afcb5061d2858d2fe248e6fd759a7caf189b`.

For the earlier `epsilon_s=1/200` rationalized D4 vector, the already
independently reconstructed exact quotient is

\[
 q_{1/200}=0.8963676783427826288116142626306203472028136097168\ldots.
\]

Exact fraction cross-multiplication gives

\[
 q_{7/2000}-q_{1/200}
 =0.0004695812861454444982065546334190518589227541398117\ldots>0.
\]

The full reduced fraction, all endpoint/transition margins, and both artifact
hashes are checked (in normal and optimized Python modes) by

```
python3 prime-gap-236/agents/small-delta-frontier/verify_c10_epsilon_d4.py
python3 -O prime-gap-236/agents/small-delta-frontier/verify_c10_epsilon_d4.py
```

The checker SHA is
`c01631dc06e49a23a2441f9049a9ac428905c67f28736b675e401de7f43c1a5a`.
It deliberately labels generalized-eigenvalue optimality non-rigorous.  The
only rigorous statement here is the pair of exact particular-vector
contractions and their exact comparison.  In particular, the D4 gain is not
evidence for the sign or ordering at D12.
