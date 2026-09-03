# Active25 cap-slack/D16 cross pilot v2 prelaunch audit

Status: **SCOPED PRELAUNCH PASS** for the count-specific cap-slack geometry,
the three frozen shell-only exact forms, and the disabled pruned-cross plan.
This is not authorization for a target cross.  The cap-pilot `(r,h)=(10,10)`
wall/RSS gate has not been run, `launch_authorized` remains false, and no cross
value or combined quotient was computed in this audit.

## Frozen inputs

- cap-slack producer `scripts/active25_count_cap_slack_shell.py`:
  `bf460e36c0cc1586b82b6563464dab52773ca8895a87a930ad970b6b4935339b`
- producer tests:
  `d119c246c9483bb5416d40bc860b683281f89130ea66ac22134a4fba93a6b815`
- exact shell outputs for maximum degrees 0, 1, and 2:
  `6e97c4b35d27e40f40e258dd00726d84f2dfc3c910ef9542250d45be9624e195`,
  `3d6532fdf9f641583598d45bae55b9d40641391136e0498748f446d783030b68`,
  and `c66cd86055385dc372d948d2f209f84fb850136120d21b55554806ba25d73d63`
- pruned pilot source:
  `cd20a85e51d623476b5433626ec4ce35d242e8a00a5f706db1af05509b59d913`
- pilot tests:
  `8f16fdc5a72f8e26ffc5c7b2a0ee5f0e8fc734a4383edeb3a2d414a97df94a1f`
- pilot specification:
  `ce965d905274af92a3c64496369ffdb5cd97bf5c75a088432428f5707d032851`
- disabled pilot artifact:
  `3a07078ca5b480b0d8d554019b42e05b7fb732a1225d97ff761d5b5231abd31c`

The checker also pins the v1 cross-plan package, the active25 arithmetic core,
its five transitive exact/analytic inputs, and all six cost probes.  Their
complete path/hash map is in the audit JSON.

## Definition-1 derivation

On the exact-count `R` cell write every large coordinate as
`t_i=delta+x_i`, put `z=sum(x_i)`, and set

```text
gamma_R = B_R-R*delta.
```

Definition 1 gives `z<=gamma_R`.  Therefore the normalized coordinate

```text
C_(R,d) = 1_{#large=R} ((gamma_R-z)/gamma_R)^d
```

is well-defined for every active positive count and vanishes at its own cap.
Count zero has only degree zero, consistently with the convention `B_0=0`.

For the `I` moment of power `p`, let `s=k-R`, inclusion--exclude `h` small
upper faces, and put

```text
L_h = alpha-(R+h)*delta,
U_h = min(gamma_R,L_h).
```

Angular integration followed by expansion of `(gamma_R-z)^p` and
`(L_h-z)^s` gives

```text
C(k,R)/(gamma_R^p*(R-1)!*s!)
 * sum_h (-1)^h C(s,h)
 * sum_i sum_j (-1)^(i+j) C(p,i) C(s,j)
     gamma_R^(p-i) L_h^(s-j) U_h^(R+i+j)/(R+i+j).
```

Here the outer sum is over `0<=h<=s` with `L_h>0`, while
`0<=i<=p` and `0<=j<=s`.

This is exactly the producer recurrence.  The shell Gram entry for degrees
`d,e` is the high-support moment of power `d+e` minus its low-support
counterpart.  An independent literal checker also used two `k=2` rational
examples: one with a binding cap and inactive total face, and one with a
binding total simplex and inactive cap.  Powers 0 through 4 agreed exactly in
both examples.

For a marginal, let the other `k-1` variables have `r` large coordinates,
`h` translated small upper faces, shifted masses `z,w`, and
`u0=(r+h)delta`.  Direct integration over the distinguished coordinate gives
all four formulas:

```text
Sdelta: delta * (gamma_r-z)^d/gamma_r^d

Stotal: (alpha-u0-z-w) * (gamma_r-z)^d/gamma_r^d

Lbig:   (gamma_(r+1)-z)^(d+1)
        / ((d+1)*gamma_(r+1)^d)

Ltotal: ((gamma_(r+1)-z)^(d+1)
          -(B_(r+1)-alpha+h*delta+w)^(d+1))
         / ((d+1)*gamma_(r+1)^d).
```

The first two are literal small-fiber lengths.  The last two are the endpoint
evaluation of
`((gamma_(r+1)+delta-z-t)/gamma_(r+1))^d` from `t=delta` to respectively the
cap or total upper endpoint.  Twenty exact branch-valid literal evaluations,
covering every branch and degrees 0 through 4, equal the producer polynomial.

## Factors, orientation, and count sparsity

For shell coordinates the numerator matrix is

```text
48*(J_HH-J_HL-J_HL^T+J_LL).
```

The ordered mixed block is not assumed symmetric.  A deliberately asymmetric
two-by-two exact fixture gives `[[432,-192],[-192,528]]`; replacing the two
orientations entrywise by `2*HL` gives a different off-diagonal value.  The
fixed-inner cross is

```text
48*(a_R*(J_RH-J_RL)
    +(a_inner-a_R)*(J_VH-J_VL)).
```

The exact vector fixture is `[432,672]`.  There is no polarization factor in a
matrix entry; a factor 2 appears only when a later quadratic contraction sums
the two off-diagonal orientations.  The grouped pilot kernel accumulates the
raw signed `J` cross, so an authorized successor must apply the factor 48
exactly once when forming its numerator matrix.

`I` is count-diagonal because two distinct exact-count indicators have
disjoint support.  On a common-`r` marginal face a small distinguished
coordinate has total count `r`, while a large one has total count `r+1`.
Consequently `J_(R,S)=0` when `|R-S|>1`.  Every stored nonzero in the three
exact shell forms obeys these rules, and all exact sparse contractions
reproduce the published denominators, numerators, margins, quotients, and sign
flags.

The exact schedule has

```text
B_25=363/2000 > 25*delta=361/2000,
B_26=363/2000 < 26*delta=4693/25000.
```

Together with all earlier exact cap checks, the active counts are precisely
`0..25`.

## Pruning and exact denominator share

The pilot retains degree zero on every active count and degrees one and two
only on counts `9..14`, for 38 coordinates.  Independent recontraction of the
frozen D2 sparse `I` form ranks the first eight count blocks as

```text
12, 11, 13, 10, 9, 14, 8, 15.
```

Thus `9..14` are exactly the top six blocks.  Their exact share of this
particular vector's denominator is stored in full in the audit JSON.  Its
canonical rational has 34,973 characters and SHA-256
`8d510aba21c67f3be1b146551c69e39c44b88e10e04530aeb993c764108e9d68`;
to 50 decimal digits it is

```text
0.99311280996698630218517416729409976553775244824133.
```

The independently serialized complete contribution record has SHA-256
`3a15843d88e138f4e33a8f16d11f07f689a6cabeaa3ba4b3e42f9a71d5d310be`,
matching the disabled plan.  This is only a denominator-mass heuristic for one
frozen D2 vector; it is not a finite-space upper bound.

## Work inventory and runtime gates

Since `floor(eta/delta)=34`, common count `r` has `35-r` faces and counts
`0..25` give 585 faces.  If `n_r` is the retained label count on stratum `r`,
the syntactic work per face is independently

```text
4 signed R/V-by-H/L tags * (2*n_r + 2*n_(r+1)).
```

Summing gives exactly 13,888 weighted branch-column terms for the pilot,
27,280 for full D2, and 93,600 for ten natural B4 columns.  These are
pre-pruning syntactic inventories, not measured integration counts.

The six pinned constant-cross face probes take
`3.9815, 4.6843, 5.6919, 4.2799, 5.1085, 4.2270` seconds, with exact binary64
mean `4.662175950788272` seconds and peak RSS 38,160 KiB.  The plan's declared
two-times calibration gives `5454.745862422278` seconds, or
`1.5152071840061885` hours, below its 7,200-second projected-completion gate.
The frozen gate also requires one worker and at most 262,144 KiB.

That arithmetic is correct, but it is only a projection.  The already-frozen
constant probe at `(10,10)` is not the required cap-pilot face.  Before any
complete run, an authorized successor must execute the cap-pilot `(10,10)`
face and demonstrate at most 20 seconds and 262,144 KiB.  V2 correctly rejects
`--stage-r` in both normal and optimized modes.

## Audit artifacts and replay

- independent checker `verify_active25_cap_slack_cross_pilot_v2.py`:
  `881622f7bb8e189f240e76c8a31750ef0fb2db42b1561d9e03e06dc1124348fe`
- audit result
  `results/active25_cap_slack_cross_pilot_v2_prelaunch_audit.json`:
  `bbda024a64b32bca96c76cc7b77917b4779daa3c1c108f3a2ff163200249112d`

Run:

```text
python3 agents/audit/verify_active25_cap_slack_cross_pilot_v2.py
python3 -O agents/audit/verify_active25_cap_slack_cross_pilot_v2.py
```

The checker itself runs the cap producer, v1 cross-plan, and v2 pilot tests in
both modes: 5+5+4 tests per mode, 28 test cases total.  It also requires the
normal and optimized preflight streams to be byte-identical and semantically
equal to the frozen minified artifact.  The normal and optimized checker
outputs are byte-identical, with the audit-result hash shown above.  No
target-sized integration was launched, and no file under `attempt_001` was
changed.
