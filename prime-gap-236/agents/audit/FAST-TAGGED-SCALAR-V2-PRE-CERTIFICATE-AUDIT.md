# Incremental hostile audit of fast tagged-scalar v2

## Verdict

**PRE-CERTIFICATE AUDIT PASS** for the frozen fast-v2 snapshots below.

This is an incremental verdict over the v1 cross-engine audit in
`SYMMETRIC-CUTOFF-CROSS-PRE-CERTIFICATE-AUDIT.md`.  It certifies that fast v2
performs the same exact linear contraction after denominator clearing and
restores every cleared denominator exactly.  It does not certify a target
shard which has not finished, the final sum over shards, or the positivity
inequality needed for \(H_1\leq236\).

No counterexample was found.

## Frozen bytes

| role | path | SHA-256 |
|---|---|---|
| fast-v2 shard runner | `agents/exact-projection-engine/d14_grid38_scaled_b_shard_fast_v2.py` | `4613b0fb117bf58c732e9bdeb22fa9d847a1152cc1bcac3b8b92f584231709d3` |
| fast backend | `agents/exact-projection-engine/fast_tagged_scalar.py` | `5d9d82ae7b097a40b852a8471e281d5bd5ad69d08240e1a73d3928e21a40aaa2` |
| pinned producer tests | `agents/exact-projection-engine/test_symmetric_cutoff_cross.py` | `d2898ef57898e1a3dc5b752a842bcc1b04bd234a4575342a804b0dcf1f44be26` |
| independent hostile fast tests | `agents/audit/test_fast_tagged_scalar_independent.py` | `4be6e1ee886395ae287ab9d157666be8f249896cc323d5437639f3c2f240598f` |
| inherited v1 runner | `agents/exact-projection-engine/d14_grid38_scaled_b_shard.py` | `deceb6c6248fa97e65c9ce5a604081f3b05f0b7c838dea2f1d1c525a59bea905` |
| inherited cross engine | `agents/exact-projection-engine/symmetric_cutoff_cross.py` | `d3aa9c1793a6c1d7e9ad2b71cb2d81dee690e7d9aaaea56134c428a752967726` |

The v2 runner pins the first three local dependencies.  The pinned v1 runner
in turn pins the cross engine, radial backend, frontier code, support result,
D19 result and audit, D14 vector, and their checkers.  V2 snapshots both
levels and rejects any replacement before writing output.  Its own hash is
supplied externally and recorded as the producer hash.

## Denominator-clearing proof

Let \(c_{f,t,\nu}\) be a coefficient in one primitive family and let

\[
 D=\operatorname{lcm}_{f,t,\nu}\operatorname{den}
      (c_{f,t,\nu}).
\]

Lines 23--43 of `fast_tagged_scalar.py` replace every coefficient by the
integer

\[
 C_{f,t,\nu}=D c_{f,t,\nu}.                             \tag{1}
\]

For a fixed common-large count, let \(R_{\nu,h,a,b}\) be the exact radial
transform coefficient of orbit \(\nu\), after dropping only shifts beyond
the global Definition-5 cutoff.  Lines 46--113 choose

\[
 E=\operatorname{lcm}_{\nu,h,a,b}
      \operatorname{den}(R_{\nu,h,a,b})
\]

and replace the transform by the integer
\(S_{\nu,h,a,b}=E R_{\nu,h,a,b}\).  Every accumulated packed coefficient is
therefore

\[
 \sum_\nu C_{f,t,\nu}S_{\nu,h,a,b}
   =DE\sum_\nu c_{f,t,\nu}R_{\nu,h,a,b}.                \tag{2}
\]

The remaining affine powers and polygon moments stay exact Fractions, and
integration is linear in the packed coefficient.  Thus each integer endpoint
returned by lines 330--337 is \(DE\) times the reference endpoint.  Lines
339--346 divide every total and branch value by exactly `D*E` before the sole
factor \(k\) is applied at line 347.  There is no un-restored family,
per-branch, affine, or moment denominator.

Zero coefficients do not affect either LCM.  If every retained radial
transform is empty, \(E=1\), the packed result is empty, and both exact paths
return zero.  Python integers have arbitrary precision, so (1)--(2) involve
no overflow or rounding.

## Collected affine proof and shifts

For a tag `(p,q)`, the reference integrand multiplies

\[
 (f_0+f_xX+f_yY)^p(s_0+s_xX+s_yY)^q.                   \tag{3}
\]

When the two slope pairs agree, lines 124--142 first collect powers of the
common linear form \(L=f_xX+f_yY\):

\[
 (f_0+L)^p(s_0+L)^q
 =\sum_{i=0}^p\sum_{j=0}^q
   {p\choose i}{q\choose j}f_0^{p-i}s_0^{q-j}L^{i+j}.
\]

The following binomial expansion of \(L^{i+j}\) is exact.  When slopes
differ, lines 144--152 multiply the two exact affine maps directly.  These
are exhaustive cases; the optimization changes only collection order.

On an inclusion--exclusion shift \(Y_{\rm literal}=Y+h\delta\), lines
219--236 replace each affine constant by
`q0 + qy*h*delta`.  Lines 155--205 simultaneously replace total and Y bounds
by their old values minus \(h\delta\).  The signs therefore agree with the
literal identity, including target slopes \((-1,-1)\).  No X bound is shifted
because only small coordinates participate in this inclusion--exclusion.

The cases `r=0`, `s=0`, and `r=s=0` evaluate forbidden aggregate powers as
zero.  The zero-small case assigns equality of the two large fiber bounds to
the cap-limited branch only, just as the audited v1 radial backend.  At the
equality the two fiber endpoints coincide, so this convention partitions the
domain without changing its value.

## Runner comparison with v1

Lines 85--176 of the v2 runner reconstruct the same pinned rational vectors,
bases, natural dilation, inner marginal, global orbit kernel, and primitive
families as v1.  Lines 178--181 are the sole mathematical substitution: v2
calls `band_cross_r_integer` instead of the v1 Fraction radial contraction,
with exactly the same

```text
k=48
alpha_high=9500917/36000000
alpha_low=103/400
alpha_f=103/400
eta=8960917/36000000
delta=1/60
schedule and common_r
```

The output keeps the exact branch values after denominator restoration and
records denominator sizes and work counts.  It does not read serialized
moments or matrices.

## Adversarial executable checks

`test_fast_tagged_scalar_independent.py` obtains expected values from the
separate literal polygon oracle.  It does not accept equality with v1 as its
only oracle.  It checks:

- all 64 ordered pairs of an eight-element residual/orbit basis against the
  literal high and low polygon integrals, branch by branch, through both fast
  Fraction and fast integer paths;
- 16 deterministic random rational coefficient pairs and random rational
  geometries, including changing delta, eta, endpoints, and nonuniform cap
  schedules;
- exact coefficient-by-coefficient restoration of (2), before scalar
  integration, for every family and both `r=0,1`;
- a closed-form \(k=1\) test with no shared variables:
  \(J_{\rm band}=\alpha_F(\min(\alpha_H,\beta_1)
  -\min(\alpha_L,\beta_1))\), through both fast paths.

The frozen backend passed:

```sh
python3 agents/audit/test_fast_tagged_scalar_independent.py -v
# 4/4 PASS in 7.644 s
python3 -O agents/audit/test_fast_tagged_scalar_independent.py -v
# 4/4 PASS in 7.527 s
```

The frozen producer suite also passed 7/7 in normal mode (0.704 s) and 7/7
under `python3 -O` (0.713 s).  It compares fast Fraction and fast integer
branch values with the older exact radial and face paths on a nonuniform
all-four-branch fixture.

## Required result-level re-audit

Fast-v2 output may be used in the theorem certificate only after a separate
result audit verifies:

1. its producer hash is
   `4613b0fb117bf58c732e9bdeb22fa9d847a1152cc1bcac3b8b92f584231709d3`;
2. all nested source hashes equal the table and inherited v1 pins;
3. each branch total is a canonical exact rational and recombines to
   `scaled_b_shard` with exactly one factor 48;
4. if the capped v1 `r=0` run lands, fast-v2 `r=0` is exactly equal to it;
5. all thirteen unique common counts are present before summation;
6. the final scalar inequality is reconstructed independently.

## Frozen target result audited so far

The common-count `r=0` shard subsequently landed and passed the scoped
result-level checks above:

| object | SHA-256 |
|---|---|
| `agents/exact-projection-engine/results/d14_grid38_scaled_b_fast_v2/common_r_00.json` | `6594f8a5e4079907a065e5fae434cf4ecb2710ffb72de7e1af451d60676f50ea` |
| `agents/audit/verify_fast_v2_cross_shard.py` | `43a46b6adbdc9a3275a7b4ab2abcef3b7e5c4d214f15b8790f0dc8c4dfdede78` |

The checker strictly decoded canonical JSON, verified all live and serialized
source pins, derived the four active branch sets independently from the
rational geometry, parsed every branch value as a reduced rational, restored
and checked the 515-bit family and 487-bit radial denominator metadata, and
verified exactly

\[
 b_0=48\left(\sum_{u\in\mathcal B_{\rm high}}u
                  -\sum_{u\in\mathcal B_{\rm low}}u\right)>0.
\]

The recorded producer time was 543.726 seconds and peak RSS was 537,396 KiB.
The frozen v1 `r=0` attempt was resource-capped before producing an output, so
there is no theorem-size v1/v2 result equality for this shard.  The result
verdict therefore rests on the source-level algebra proof, independent literal
low-dimensional tests, and the exact serialized recombination; it does not
pretend that the aborted replay existed.  All remaining common counts and the
final exact sum remain outside this scoped verdict.
