# Hostile audit of the exact one-band cross engine

## Verdict

**PRE-CERTIFICATE AUDIT PASS** for the source snapshot listed below.

This verdict means that the formulas and the frozen shard runner reconstruct
the exact quantity

\[
 b_r=48\int_{\substack{\sum_{i=1}^{47}u_i\leq\eta\\
                        \#\{i:u_i>\delta\}=r}}
       M_F(u)M_{H,\mathrm{high}-\mathrm{low}}(u)\,du
\]

for each `common_r = r`, including the Definition-5 cutoff and exactly one
factor 48.  It also means that the companion band-I routine reconstructs the
outer norm shards.  No target shard or assembled positive certificate existed
when this verdict was issued.  Consequently this is not yet an audit pass for
`[ONE-BAND-EXACT-CERT]`, and it is not a proof of \(H_1\leq236\).

I found no mathematical or software counterexample in the audited scope.

## Audited snapshots

| file | SHA-256 |
|---|---|
| `sources/stadlmann-2608.31126-src/Bounded_Gaps_2.0.tex` | `c0d5d2317c77f4de7eacdef6e1d4b1eb6433e6240b5c09273b3d4eee99e6c3ba` |
| `agents/exact-projection-engine/symmetric_cutoff_cross.py` | `d3aa9c1793a6c1d7e9ad2b71cb2d81dee690e7d9aaaea56134c428a752967726` |
| `agents/exact-projection-engine/d14_grid38_scaled_b_shard.py` | `deceb6c6248fa97e65c9ce5a604081f3b05f0b7c838dea2f1d1c525a59bea905` |
| `verify/exact_capped_certificate.py` | `1787e7b482a5c2982de56486bc774794f6e671b3db4d9ab7207ebb1c85dc079c` |
| `agents/small-delta-frontier/frontier_active25_inner_d16_tagged_shell.py` | `1393a2dd29e5660f10e632b19b6b5eeafe9363bf79b2cd4a8254049d1f9c669a` |
| `agents/analytic-new-lever/truncated_lower_energy_v3_exact.json` | `c9be4426ece4cc50063ee64ccae72d26c66af5296d7312b2fb9ac0192ba30c9f` |
| independent test in this audit | `b4e17d1b8bc8fb1ccae7bbcd06be9425ed1a0b7eb94df9e2203a5276a47a9855` |

The shard runner itself pins the engine, radial backend, support, D19 vector,
D19 audit result, D14 grid vector, and their checkers.  It snapshots every
dependency before work and rejects a concurrent replacement after work.  Its
own hash must still be supplied externally, so the final assembler must pin
the runner hash above rather than trusting a hash copied out of a shard.

## Derivation from the primary definition

The derivation here starts from Definitions 1 and 5 at TeX lines 140--147 and
211--217, not from comments in the implementation.

Let \(u=(t_1,\ldots,t_{k-1})\), \(U=\sum u_i\), and extend each supported
function by zero.  If \(F\) is in the inner band and \(H\) is in the single
outer band, polarization of the two ordered `(inner,outer)` and
`(outer,inner)` terms in Definition 5 gives

\[
 J(F,H)=\int_{U\leq\eta}M_F(u)M_H(u)\,du,
 \qquad
 M_P(u)=\int_0^\infty P(u,t)\,dt,
\]

where

\[
 \eta=\max(A_1-\varepsilon,A_2-\varepsilon)
      =A_2-\varepsilon=\frac{8960917}{36000000}.
\]

This is one distinguished-coordinate form.  Proposition 1, not
polarization, supplies the sole factor \(k=48\).  Thus the desired scalar is
`b = 48*J(F,H)`, not `J`, `48^2*J`, or a sum over 48 omitted coordinates.

### Full-simplex inner marginal

Write the unnormalised monomial symmetric polynomial as \(P_\lambda\).  For
each distinct distinguished exponent \(e\), including \(e=0\) exactly when
`len(lambda) < k`,

\[
 P_\lambda(u,t)=\sum_e t^eP_{\lambda\setminus e}(u).
\]

For an inner basis term \((1-U-t)^aP_\lambda(u,t)\), integration over the
full inner fiber \(0\leq t\leq\alpha_F-U\) gives, for each split,

\[
 \sum_{c=0}^a {a\choose c}(1-\alpha_F)^{a-c}
 \frac{e!c!}{(e+c+1)!}
 (\alpha_F-U)^{e+c+1}P_{\lambda\setminus e}(u).       \tag{1}
\]

Lines 117--149 implement (1): their denominator
`(e+c+1)*binom(e+c,e)` is exactly \((e+c+1)!/(e!c!)\).  The guard
`eta <= alpha_f` is sufficient because the outer integration never requests
the marginal beyond the inner simplex.

Lines 152--164 split the outer polynomial at the same distinguished
coordinate without integrating it.  Lines 167--199 multiply the resulting
shared-coordinate orbit polynomials.  The structure constants are not
silently treated as one; their integer multiplicities are retained.

### Fiber antiderivative

Every collected term before the outer fiber integral has the form

\[
 C P_\nu(u)(\alpha_F-U)^p t^e(1-U-t)^a.                \tag{2}
\]

Put \(n=e+j+1\).  Expanding first in \(t\), and then expanding
\(1-U=(1-\alpha_F)+(\alpha_F-U)\), gives the coefficient

\[
 C\frac{(-1)^j}{n}{a\choose j}{a-j\choose s}
 (1-\alpha_F)^{a-j-s}(\alpha_F-U)^{p+s}.               \tag{3}
\]

For a small full fiber, (3) is multiplied by \(\delta^n\).  For a truncated
small fiber it is multiplied by \((\alpha-U)^n\).  For a large fiber with
translated length \(q\),

\[
 (\delta+q)^n-\delta^n
   =\sum_{f=1}^n {n\choose f}\delta^{n-f}q^f.           \tag{4}
\]

Lines 380--445 are exactly (3)--(4).  In particular, the large family starts
at `fiber_power = 1`, so the lower endpoint \(t=\delta\) is subtracted rather
than counted a second time.

### Literal four-branch geometry

Fix the number \(r\) of large shared coordinates.  Translate them by
\(u_i=\delta+x_i\) and write \(X=\sum x_i\).  The other
\(s=k-1-r\) shared coordinates are small.  On an inclusion--exclusion term
where \(h\) of their upper bounds were shifted, write their remaining sum as
\(Y\), so

\[
 U=r\delta+X+h\delta+Y.                                \tag{5}
\]

For an endpoint with total bound \(\alpha\) and cap schedule \(\beta_m\),
the outer distinguished fiber is partitioned, up to null boundaries, as
follows.

| branch | fiber | shared domain before the automatic `h*delta` shift |
|---|---|---|
| `Sdelta` | \(0\leq t\leq\delta\) | \(X\leq\beta_r-r\delta\) if \(r>0\), and \(X+Y\leq\min(\eta-r\delta,\alpha-(r+1)\delta)\) |
| `Stotal` | \(0\leq t\leq\alpha-U\) | same shared cap, \(\alpha-(r+1)\delta\leq X+Y\leq\eta-r\delta\) |
| `Ltotal` | \(\delta\leq t\leq\alpha-U\) | \(Y\geq\alpha-\beta_{r+1}\), and \(X+Y\leq\min(\eta-r\delta,\alpha-(r+1)\delta)\) |
| `Lbig` | \(\delta\leq t\leq\beta_{r+1}-r\delta-X\) | \(Y\leq\alpha-\beta_{r+1}\), \(X\leq\beta_{r+1}-(r+1)\delta\), and \(X+Y\leq\eta-r\delta\) |

Here \(\beta_0\) is never requested.  In the large branches no separate
shared \(\beta_r\) cap is missing: from \(t>\delta\) and
\(\beta_{r+1}\leq\beta_r+\delta\), the total large-coordinate cap implies
the shared one.  Lines 471--535 implement precisely this table.  Lines
1275--1305 of the radial backend subtract the `h*delta` shift from total and
Y bounds and add it to affine constants with Y coefficient; this changes
(5) back to the literal coordinates with the correct sign.

The two large upper bounds agree when
`Y+h*delta = alpha-beta[r+1]`.  This is a null hypersurface unless there is no
small shared variable.  In that degenerate case the radial backend assigns
the coincident fiber to `Lbig` only.  The value is unchanged because the two
upper bounds are then identical; the independent test includes this exact
case to detect double counting.

Lines 556--577 subtract the low endpoint from the high endpoint and multiply
the result by `k` once.  The frozen runner passes `alpha_high=alpha2` and
`alpha_low=alpha1`, so it represents the positive outer band
`S(alpha2)-S(alpha1)` rather than its negative.

### Outer I norm

Lines 345--359 form the exact residual-orbit square, retaining the factor two
on unequal term pairs.  Lines 580--624 integrate each total-large-count
stratum at the two endpoints and return high minus low.  There is no
Definition-5 cutoff in I.  Its cap is \(X\leq\beta_r-r\delta\), and its
residual affine is exactly

\[
 1-r\delta-X-h\delta-Y.
\]

The independent literal I oracle agrees stratum by stratum, including orbit
multiplicity.

## Frozen dilation, scales, and active strata

The target runner uses

\[
 \alpha_1=\frac{103}{400},\qquad
 \alpha_2=\frac{9500917}{36000000},\qquad
 d=\frac{\alpha_1}{\alpha_2}=\frac{9270000}{9500917}.
\]

For \(L=1-\sum t_i\),

\[
 1-d\sum t_i=(1-d)+dL,\qquad
 P_\lambda(dt)=d^{|\lambda|}P_\lambda(t),
\]

so lines 48--71 implement the exact natural dilation
`H(t)=F_D14(d*t)`.  The direction is \(\alpha_1/\alpha_2\), not its
reciprocal.  Independent named-monomial evaluation in the hostile test checks
this without calling the production evaluator.

The exact input coefficient LCMs are \(10^{87}\) for F and \(10^{38}\) for
H.  Hence each cross shard is scaled by \(10^{125}\), each outer-I shard by
\(10^{76}\), and

\[
 \frac{b_{\rm scaled}^2}{A_{\rm scaled}}
   =10^{174}\frac{b^2}{A},
\]

matching the \(10^{174}\) scale of the inner deficit.  The hostile test uses
these actual powers, not small proxy powers.

For the frozen schedule, \(\beta_r-r/60>0\) for every
\(1\leq r\leq12\); the last margin is \(2917/250000\).  With the plateau
extension, \(\beta_{13}-13/60=-3749/750000<0\).  Therefore common shared
counts `0..12` are complete and `13` is empty.  The cutoff alone would permit
larger counts, so this cap check is essential.

## Independent adversarial tests

The file `agents/audit/test_symmetric_cutoff_cross_independent.py` contains a
separate exact oracle.  It does not call the production support branches,
orbit multiplication, marginal recurrence, radialization, or polygon
integrator on its expected-value path.  For \(k=2\), it:

1. expands every named monomial of each symmetric orbit;
2. integrates the inner distinguished variable symbolically;
3. clips the literal four large/small cells in the original `(u,t)` plane by
   the total, cap, and Definition-5 cutoff inequalities;
4. integrates arbitrary polynomial moments over the resulting rational
   polygons using an independently expanded Green formula.

The test suite checks:

- all 64 ordered pairs from an eight-element basis containing constants,
  residual powers, repeated exponents, distinct exponents, and length-two
  partitions;
- 16 deterministic random rational linear-combination pairs;
- 12 deterministic random rational geometries with varying delta, eta,
  endpoints, and nonuniform compatible schedules;
- every `Sdelta`, `Stotal`, `Ltotal`, and `Lbig` branch separately at both
  endpoints and both possible shared counts `r=0,1`;
- exact high-minus-low orientation, a deliberately detectable cutoff change,
  and a coincident-upper-bound case;
- outer I endpoint and band values separately for all `r=0,1,2`;
- the actual target rationals, natural dilation, and exact scales
  \(10^{87},10^{38}\);
- a separate \(k=4\) brute-force named-monomial identity for the globally
  collected kernel, including repeated/distinct orbit multiplicities.

Both commands passed:

```sh
python3 agents/audit/test_symmetric_cutoff_cross_independent.py -v
python3 -O agents/audit/test_symmetric_cutoff_cross_independent.py -v
```

The normal run reported 7/7 tests in 20.138 seconds and the optimized run
reported 7/7 in 20.796 seconds.

The production suite also passed 7/7 in normal and optimized modes against
the audited engine snapshot.  Unlike the hostile oracle, its strongest cross
comparison uses the existing face engine, so it is corroboration rather than
the basis of this verdict.

## Required re-audit before theorem status

The final audit must still reject the certificate unless all of these hold:

1. there are exactly thirteen immutable cross shards with unique
   `common_r={0,...,12}` and identical pinned source hashes;
2. each shard's producer hash is the audited runner hash and its exact value
   is recomputed or replayed, not copied from an unpinned matrix;
3. high and low branch values add to the serialized shard value with the
   factor 48 exactly once;
4. the independently produced outer-I shards agree with the band-I routine;
5. the D19 deficit is multiplied by exactly \(10^{174}\);
6. the assembler verifies exactly \(A>0\) and
   \(b^2-A D_{\rm scaled}>0\), then reports the unreduced integers/rational
   margin without decimal rounding;
7. normal and `python3 -O` reconstruction outputs are byte-identical.

Until that re-audit, this report authorizes the exact shard computation but
does not certify its result.
