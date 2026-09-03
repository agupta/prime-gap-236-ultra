# Frozen adaptive support at delta = 1/60

## Scope and result

This checkpoint freezes a new rational analytic support for the specialized
direct Heath--Brown route.  The exact gate passes.  It is **not** a sieve
quotient, a projection lower bound, or an `H_1` theorem claim.

The theorem-facing Type-IIb proof is deliberately the smaller empty-third
correlated two-bin argument.  A stronger literal three-bin breakpoint oracle
is preserved in a separate diagnostic artifact and cannot affect the support
gate's PASS.

The frozen parameters are

```text
k                  = 48
h                  = 1/10^10
varepsilon          = 3/400
delta               = 1/60
A_0,A_1,A_2         = -3/400, 1/4, 231241/900000
A_2-A_1             = 6241/900000
omega_cross         = 6241/1800000
omega_outer         = 6241/900000
alpha_1,alpha_2     = 103/400, 237991/900000
```

Thus the tight direct-HB face is kept at

```text
3(A_2-A_1)+delta = 3747/100000 < 3/80,
reserve = 3/100000.
```

The outer schedule through its first empty column is

```text
B1,...,B12 =
138360,155020,158662,171688,177684,180588,
183402,185486,187011,188221,189137,189137  divided by 10^6,
```

and `B_m=189137/10^6` thereafter.  Counts `0,...,11` are active and
count 12 is first empty, with exact margin `10863/10^6`.  The inner band is
the uncut simplex schedule `B_m=103/400`; its active counts are `0,...,15`.
Definition 1 permits the displayed plateau equalities.

## Exact proof boundary

`verify_adaptive_support_v1.py` imports no optimizer, arithmetic producer,
frozen-v6 module, previous support checker, previous support result, or
heuristic proxy.  In particular, neither
`correlated_iib_lift_independent_audit.json` nor
`adaptive_projection_proxy_v2.json` is in its pinned dependency closure.
The old correlated-lift point is accepted only after the new checker
reconstructs all of its scalar and support-dependent cases from its explicit
rationals.  Its earlier audit is regression context, not inherited proof.

The specialized route excludes the printed universal Proposition-3 Type-I
tuple branch and its known role-swap defect.  The checker records the printed
Type-I scalar substitutions but does not use them.  The direct Heath--Brown
classification has Type 0, a central Type-II aggregate, and corrected
fixed-factor Type III; it has no Type-I aggregate.  Therefore this checkpoint
does not assert the flawed universal Proposition 3.

## Correlated Type-IIb lemma used by the gate

Fix one ordered band pair and write its two count caps and counts as
`B_L,B_R` and `n_L,n_R`.  Every tuple coordinate is at least `delta`, and
the two group sums are at most their respective caps.  Put

```text
S = B_L+B_R,
C(gamma) = gamma-3 zeta-r_0,
D(gamma) = 1/2-gamma-2 omega-6 zeta-r_0,
K = C(gamma)+D(gamma) = 1/2-2 omega-9 zeta-2r_0,
W = K-S.
```

Here `zeta=h/1000`, `r_0=h/10`, and

```text
G_b = 1/3+8 omega+(7/3)delta+3h
 <= gamma <=
G_a = 2/5+(24/5)omega+(7/5)delta+2h.
```

The gate proves `W>0`.  Let `L(gamma)=S-C(gamma)`.  If `L<0`, all entries
fit strictly in the first bin.  Otherwise let

```text
r = max(1,ceil(L/delta)).
```

For every integer `r` attained on the whole gamma interval, the checker
selects one of the left, right, or combined pools, of count `n` and cap `B`,
and proves

```text
r=1:  B/n < W,
r>=2: (B-(r-1)delta)/(n-r+1) < W.                 (1)
```

This finite crossing-number test is a continuum proof.  For an actual tuple
of total `T<=S`, set `ell=max(0,T-C(gamma))`.  Sort the selected pool and, if
`ell>0`, take its least prefix of sum `U>=ell`.  Since each entry is at least
`delta`, the prefix ends at some `j<=r`.  If its preceding sum is `p`, then
`p<ell<=L`; all entries following the last chosen entry are at least that
entry, so

```text
U <= p+(B-p)/(n-j+1)
  < L+(B-(r-1)delta)/(n-r+1)
  < L+W = D(gamma).
```

For `r=1`, the same argument gives `U<=B/n<W`.  Its complement has sum
`T-U<=C(gamma)`.  Put the prefix in bin 2, the complement in bin 1, and
leave bin 3 empty.  When `L=0`, moving one smallest entry gives the recorded
strict reserve rather than relying on the permitted weak all-first equality.
This proves the partition for every real tuple and every real gamma, not a
sampled grid.

For the candidate, the exhaustive ordered-pair inventory is

```text
mixed       191
transpose   191
outer       143
outer-near  143
total       668
```

It includes `m=0` and `m'=0` separately (48 cases of each kind across the
four fixed families).  There are 767 exact Type-IIb crossing-number checks.
The least uniform Type-IIb reserve is

```text
53930026073/90000000000000
```

at outer-near counts `(7,10)`.

## Other exact branches

The same sorted-prefix construction, at fixed capacities, checks Type IIa
and corrected Type III.  It performs 1,336 checks and has least reserve

```text
43599493/7200000000000
```

at the mixed Type-III pair `(1,3)`.

For Type IIc, only outer/outer above-square-root blocks are nonempty.  The
mixed and near ranges are empty with exact margins

```text
mixed: 99999/2500000000
near:  624999991/22500000000.
```

The nonempty rectangle is divided into `16 x 16` cells.  On a cell
`gamma in [g_l,g_u]`, `omega_0 in [w_l,w_u]`, the checker uses

```text
g_l-2delta-8w_u-h,
1/2-g_u-2w_u-h,
4w_l+delta-h,
8w_l.
```

These are coordinatewise lower bounds for the four literal capacities at
every point of the closed cell.  Consequently each exact fixed-prefix
certificate covers the full cell.  All `143*256=36,608` cells pass; the
least reserve is

```text
800009/180000000000
```

at counts `(5,8)`, omega-cell 5, gamma-cell 10.

All direct Type-0, prime-power, IIa/IIb/IIc/III source inequalities are also
substituted exactly.  The smallest source reserve is the intentional IIc
width reserve `1/200000000000`.  The tight outer direct-II scalar margin,
after its `2h` inward reserve, is `149999/5000000000`.

As an explicit support-interior witness, translate every outer cap by a
common rational `t` with `|t|<=1/10^6`.  Definition-1 cap differences are
unchanged, both endpoint schedules retain active counts `0,...,11`, and
packing monotonicity reduces the whole interval to the exactly checked upper
endpoint.  At that endpoint the least fixed, correlated-IIb, and dynamic-IIc
reserves remain respectively

```text
36399493/7200000000000,
53750026073/90000000000000,
440009/180000000000.
```

## Proposition 2 and the prime weight

At

```text
xi_1=19/50, xi_2=xi_3=2/5,
```

the four strict scalar reserves in Proposition 2 are

```text
1/25, 1/50, 4/25, 1/5.
```

The `xi_2=xi_3=2/5` specialization makes both discarded configurations
empty in the pinned prime-minorant proof, hence

```text
rho(n;x)=(log n/log(3x))*1_P(n) on [x,2x], zero outside,
c_1=c_2=0.
```

It satisfies `0<=rho<=1_P`.  Take `beta=1/2`; a prime in `[x,2x]` has its
only prime factor greater than `x^beta`, while

```text
max_j B_{j,1}=103/400 < 1/2,
margin=97/400.
```

## Separate three-bin design diagnostic

`diagnose_three_bin_iib_v1.py` is not read, imported, or hashed by the
support gate.  It proves the following stronger construction for future
schedule searches.

Choose `q_L` and `q_R` smallest entries of the original pools for bin 3.
The average-of-the-smallest inequality gives

```text
U_3 <= q_L B_L/n_L + q_R B_R/n_R.
```

The residual counts are `n_i-q_i`, and because the removed entries are each
at least `delta`, valid residual caps are `B_i-q_i delta`.  Apply the
correlated two-bin lemma above to those residual pools.  For any fixed
action `(q_L,q_R)`, its truth value can change only at:

1. `E(gamma)=U_3`, where
   `3gamma=7U_3+1+10omega-63zeta+7h`;
2. `L=0`; or
3. `L=j delta`, equivalently
   `gamma=S_res+3zeta+r_0-j delta`.

The diagnostic includes all these rational points.  On each intervening
open interval, the third-bin sign, the crossing number, and the selected
pool inequality are constant, so one midpoint-selected strategy is valid on
the entire interval; every breakpoint endpoint is checked separately.
This proves the continuum statement for the reported schedules.

For the frozen candidate it checks 668 ordered pairs and 4,618 endpoint or
open-interval records.  A nonempty third bin is selected in 196 max-margin
records, always with `q_L+q_R<=1`; the first such pair is mixed `(1,5)`.
However, the empty-third gate already accepts every frozen-candidate pair,
so the honest enabling mechanism here is the larger-delta correlated
two-bin argument.  The three-bin result is retained only as a nontrivial
future cap-optimization lever.

## Geometry diagnostic versus heuristic ranking

The exact constant-function outer-shell Lebesgue volume of this candidate is

```text
0.664817253072246897936749... times
```

that of the audited correlated-lift support.  This is a proved geometry
diagnostic, not a performance ordering for the D18 direction.

The separate discovery record `adaptive_projection_proxy_v2.json` estimated
retained `int_V G_F^2` fractions `0.515666...` for this candidate and
`0.00108333...` for the audited lift.  That record labels itself
`HEURISTIC ONLY`; its chains are noisy, it is not an exact integral or a
projection lower bound, and it is not in the analytic gate's dependency
closure.  Its only role was candidate ranking.

## Replay and hashes

```bash
python3 agents/analytic-new-lever/verify_adaptive_support_v1.py
python3 -O agents/analytic-new-lever/verify_adaptive_support_v1.py
python3 agents/analytic-new-lever/diagnose_three_bin_iib_v1.py
python3 -O agents/analytic-new-lever/diagnose_three_bin_iib_v1.py
python3 agents/analytic-new-lever/test_adaptive_support_v1.py
python3 -O agents/analytic-new-lever/test_adaptive_support_v1.py
```

Normal and optimized JSON outputs are byte-identical, and all seven hostile
regression tests pass in both modes.

```text
exact checker       b8abaa8fec6f992c1071b4e550e666946444ff7c559b850960dc633836ce2c6d
exact result        b7070c2677815b22a86b5a55ce41b3a2477d593495062256356a5df2a37befa7
three-bin checker   24fa0665794cb6fa8cdf644cfae37b0302a9c838039cf550d00e992dffe80c67
three-bin result    627d2a3c4ae5c331ffb771e77836920bb7d14c0a9962cb69a90e07d367132ca2
test source         b2fd1817d3ffcfef126e8390a07cc940f1dc01e24f7a497621cf8674b5c6541a
```
