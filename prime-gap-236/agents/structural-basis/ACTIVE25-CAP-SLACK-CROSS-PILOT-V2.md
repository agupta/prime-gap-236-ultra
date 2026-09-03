# Active-25 cap-slack/D16 cross pilot v2

Status: frozen, disabled implementation plan.  No target cross, quotient, or
theorem value is present.  Full execution requires a distinct authorized
successor after an independent implementation audit and a one-face resource
gate.

V1 is preserved verbatim and pins the active-25 support, exact 10 by 10 B4
denominator audit, the ordered mixed-block formula
`48*(HH-HL-HL^T+LL)`, the radial-D16 inclusion formula, six exact one-face cost
probes, and the complete degree-0--2 cap-shell forms.

This successor prunes only the expensive *cross pilot*.  It retains:

- degree zero for every count `R=0..25`;
- degrees one and two for `R=9..14`.

Thus the pilot has 38 coordinates.  The selection is derived by exact Fraction
recontraction of the pinned D2 shell vector and I matrix.  Counts 12, 11, 13,
10, 9, and 14 are the six largest denominator contributions and collectively
carry more than 95% of that particular vector's denominator.  This is a search
heuristic, not an upper bound and not permission to discard the other counts
from a later certificate.

The exact coordinate remains

```
C_(R,d) = 1_{#large=R}
          ((B_R-R*delta-z_R)/(B_R-R*delta))^d.
```

On a common-`r` marginal face only counts `r` and `r+1` occur.  The fixed
radial D16 marginal is lifted once per orbit; all signed `R/V` against `H/L`
terms are grouped by coordinate and exact rational domain before integration.
The 38-coordinate pilot has 585 faces and exactly 13,888 syntactic weighted
branch-column terms before density/domain zero pruning.  For comparison, the
full 76-coordinate D2 cross has 27,280 and the natural even-B4 cross has
93,600.

Pinned exact D16-by-constant probes average 4.6622 seconds per face and peak at
38,160 KiB.  The conservative pilot projection is twice the full constant
cross: 5,454.75 seconds (1.52 hours), with a 262,144 KiB memory gate.  Before
any full run, `(common_r,h)=(10,10)` must finish within 20 seconds and below the
memory gate; the projected complete run must remain below 7,200 seconds.

Stages are one complete common count (`0..25`), one worker, exact Fractions,
fresh O_EXCL outputs, strict source closure, and deterministic merge.  This v2
rejects `--stage-r` unconditionally.

After an exact pilot cross, expansion to degrees 1--2 on all counts requires an
exact particular-vector gain of at least `1e-4` over the same inner-only
coordinate.  The natural B4 numerator/cross is attempted only if that expanded
particular quotient is at least `1.002`.  These are computational continuation
rules, not finite-space upper bounds.

Reproduction:

```
python3 agents/structural-basis/tests/test_active25_outer_b4_j_cross_plan_v1.py
python3 -O agents/structural-basis/tests/test_active25_outer_b4_j_cross_plan_v1.py
python3 agents/structural-basis/tests/test_active25_cap_slack_cross_pilot_v2.py
python3 -O agents/structural-basis/tests/test_active25_cap_slack_cross_pilot_v2.py
python3 agents/structural-basis/code/active25_cap_slack_cross_pilot_v2.py --preflight-only
python3 -O agents/structural-basis/code/active25_cap_slack_cross_pilot_v2.py --preflight-only
```

Normal and optimized preflight JSON must be byte-identical.
