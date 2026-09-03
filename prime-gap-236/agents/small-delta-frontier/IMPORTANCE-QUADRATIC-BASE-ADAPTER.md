# Post-transfer importance adapter for a quadratic base

Status: finite design only; no sampling and no target integration.  The
intended base is

`F_*(t)=F_0(t) Q_R(L,Z)`, `R=#{i:t_i>delta}`,

where the exact rational `Q` is the 96-channel D4 multiplier in artifact
`c10_stratum_quadratic_cappedopt_D4_exact.json` (SHA
`fbc8c38d2cf4241fdba03beb4251e2692e96af01ad4918c9a3a1075af2ed6e86`).
The completed D12 transfer, when present, supplies discovery normalizers only.

## 1. Exact channel convolution

Put `ell=L/alpha`, `zeta=Z/alpha`.  Convert the raw exact quadratic
coefficients once by

`qhat_R[c,d] = qraw_R[c,d] alpha^(c+d)`, `c+d<=2`,

so that `Q_R=sum qhat_R[c,d] ell^c zeta^d`.  For a correction

`H_R=sum h_R[a,b] ell^a zeta^b`, `a+b<=e`,

the combined multiplier has normalized coefficients

`phat_R[u,v] = sum_(c+a=u,d+b=v) qhat_R[c,d] h_R[a,b]`.       (1)

This is an exact rational convolution.  For the tagged monomial coordinate
`H_(s,a,b)=1_(R=s) ell^a zeta^b`, it is merely the shifted six-term quadratic
row

`phat_s[c+a,d+b]=qhat_s[c,d]`.

A selected rational correction vector is serialized for fresh recurrence as
raw coefficients `praw_R[u,v]=phat_R[u,v]/alpha^(u+v)`.  This conversion is
part of the candidate manifest and is reconstructed, not trusted.

The multiplicative space `Q*H` is deliberately narrower than the complete
degree-`2+e` stratum-polynomial space.  No result in it is an upper bound for
the latter.

## 2. One marginal channel table

At a common point `u`, let `(L0,Z0)` be its common large/small sums and let
`M^S_j(u)` and `M^L_j(u)` denote the exact one-variable moments

`integral F_0(u,x) x^j dx`

over the feasible small and large distinguished intervals.  For normalized
monomial degree `p`, define

```
T^S_(a,b) = alpha^(-a-b) L0^a
            sum_(j=0)^b binom(b,j) Z0^(b-j) M^S_j,

T^L_(a,b) = alpha^(-a-b) Z0^b
            sum_(j=0)^a binom(a,j) L0^(a-j) M^L_j.
```

For common large count `r`, only two total strata can contribute:

```
m_*(u) = sum_(c+d<=2) qhat_r[c,d]     T^S_(c,d)
       + sum_(c+d<=2) qhat_(r+1)[c,d] T^L_(c,d),

m_(s,a,b)(u)
       = sum_(c+d<=2) qhat_s[c,d] T^S_(c+a,d+b),  if s=r,
       = sum_(c+d<=2) qhat_s[c,d] T^L_(c+a,d+b),  if s=r+1,
       = 0 otherwise.
```

Thus one table `T^(S/L)_(a,b)`, `a+b<=2+e`, produces the base marginal and
every correction marginal.  The 272-term symmetric polynomial is expanded as
a polynomial in the distinguished coordinate only once.  For the natural
first screen `e=1`, moments `j=0,1,2,3` suffice: at most eight interval-moment
evaluations, 20 normalized `T` channels (ten per branch), two six-term dots
for `m_*`, and at most six active correction marginals, each a shifted
six-term dot.  All other tagged correction marginals are exactly zero at that
common point.

The J envelope should be built from these correction marginals:

`g=sum_i m_i^2`, `y_ij=m_i m_j/g`, `z=m_*^2/g`.

The two constant tagged corrections sum to `m_*`, so `z<=2`.  This retains
the finite-variance repair in `IMPORTANCE-STRATIFICATION.md`.

## 3. Degree and cost table

Let `e` be the correction degree and `p=e+2` the combined degree.  The only
identically null tagged corrections are the positive-`ell` monomials at
`R=0`.

| `e` | nominal/effective H dimension | `p` | T channels per branch | required `M_j` | active H marginals per common point | structural I/J upper entries |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 16 / 16 | 2 | 6 | 3 (`j=0..2`) | at most 2 | 16 / 31 |
| 1 | 48 / 47 | 3 | 10 | 4 (`j=0..3`) | at most 6 | 96 / 231 |
| 2 | 96 / 93 | 4 | 15 | 5 (`j=0..4`) | at most 12 | 336 / 876 |
| 3 | 160 / 154 | 5 | 21 | 6 (`j=0..5`) | at most 20 | 880 / 2,380 |

The structural counts use 16 diagonal I/J blocks and 15 adjacent J blocks:
for `n=(e+1)(e+2)/2`, I has `16*n(n+1)/2` upper entries and J has that many
diagonal entries plus `15*n^2` adjacent entries.  Start with affine
corrections (`e=1`): this reaches total degree three while keeping the
stochastic matrix at 47 effective coordinates.  Escalation to `e=2` is
allowed only after the complete D4 conditional calibration passes.

The exact grouped producer still has its fixed 1,575 square groups, 695
marginal components, 312 I faces, and 1,200 J branch domains.  Those costs are
paid once to obtain the base normalizers; pointwise sampling does not rerun
the 695-component recurrence for each correction coordinate.

## 4. Required transfer binding and factor 48

The adapter must take a caller-supplied byte SHA for the completed quadratic
transfer and require all of the following before sampling:

1. status `multiprecision-transferred-quadratic-candidate`, `complete=true`,
   `gates_passed=true`, `theorem_ready=false`, Decimal precision at least 100;
2. exact C10 parameters, dimension 272, multiplier dimension 96, counts
   `1575/312/695/1200`, and the pinned original/scaled base plus exact-Q SHA;
3. exactly 16 finite positive `i_by_r` and 16 finite positive
   `j_by_common_r` values;
4. `sum_r i_by_r = denominator` within the producer's explicit Decimal
   rounding allowance;
5. **`48*sum_r j_by_common_r = numerator`**, again within an explicit
   Decimal allowance.

The last condition is essential: `stratum_quadratic_transfer_decimal.py`
stores unscaled `J_r` and inserts 48 only in the numerator.  The schema for
this adapter is therefore fixed as

```
j_values_semantics = "unscaled conditional J_r"
sieve_numerator_factor = 48
wJ_r = j_by_common_r[r] / sum(j_by_common_r)
```

It must not reuse the existing generic weight-loader assumption that every J
list sums directly to the factor-48 numerator.  `wI_r=i_by_r[r]/denominator`.
Both are discovery weights, not exact certificate data.

The exact rational Q artifact is loaded independently and its SHA must equal
the transfer's `multiplier_sha256`.  The vector/source hashes and all adapter
dependencies are checked before and after sampling.  No Decimal coefficient
is silently promoted to the exact Q.

## 5. Finite algorithm

1. Strict-load and byte-pin `F0`, exact rational `Q`, and the completed
   transfer.  Reconstruct (1), both stratum-weight sums, and the factor-48
   identity.
2. Normalize all exact `F0*Q` coefficients by one global positive scale for
   floating point.  Per-stratum rescaling is forbidden because it changes
   the base function and its J cross terms.
3. For an I state, evaluate `F0`, `Q_R`, and the at-most-`n` nonzero H
   features in its fixed stratum.  Target log density is
   `2log|F0 Q_R|`.
4. For a common-J state, expand `F0(u,x)` once, form the `M_j` and T table,
   then all active `m_i`, `m_*`, `g`, `y`, and `z`.  Target log density is
   `log g`, not `2log|m_*|`.
5. Run separately stratified reversible chains with the frozen exact mixture
   weights.  Reconstruct each J matrix entry through the joint ratio
   `E_nu_r[y_ij]/E_nu_r[z]` and then the weighted stratum sum.
6. Require the full D4 constant/affine/quadratic oracle calibration,
   simultaneous bands, chain-deletion gate, and exact constant reconstruction.
7. Only a candidate passing the existing discovery thresholds is converted
   by (1) to a finite rational raw multiplier and sent to a fresh grouped
   scalar recurrence.

## 6. Conditioning blockers

- The convolution can suffer cancellation even when its individual T
  channels are moderate.  Use compensated sums or higher precision, retain
  raw antisymmetry, and make the exact D4 oracle the acceptance test.
- If `E_nu_r[z]=J_r/Z_r` is very small in any material-weight stratum, the
  ratio estimator is ill-conditioned despite bounded pointwise `y,z`.
  Predeclare a lower effective-sample/ratio-denominator gate; increasing the
  chain count after seeing a small denominator is not allowed.
- Zeros of `Q_R F0` or `m_*` can slow mixing.  The envelope removes the
  direct-ratio singularity, but it does not guarantee useful between-mode
  transitions.  Separate interior starts and leave-one-chain-out agreement
  remain mandatory.
- The exact Q coefficients may have a large dynamic range.  Only a single
  global rescaling is invariant.  Any underflow of a nonzero coefficient or
  marginal is a hard failure.
- A negative or mediocre transferred base quotient does not invalidate the
  sampling identities, but it makes the narrow multiplicative `Q*H` space a
  poor rescue prior.  No sampling launch is justified until the completed
  transfer sign and the resource gate are recorded.
