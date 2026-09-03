# Active-25 outer B4 numerator/cross staging plan v1

Status: disabled exact-arithmetic implementation plan.  This package contains
no target `J` value, quotient, or sieve claim.  A complete `k=48` traversal
requires a separately frozen external authorization.

## Bound target

The support is the independently audited active-count set `0..25`, with
`delta=361/50000`, total cutoffs `alpha_H=3211/12000` and
`alpha_L=103/400`, common marginal cutoff `eta=3031/12000`, and the exact
26-entry schedule in the pinned active-25 arithmetic core.  The exact 10 by 10
even-B4 shell denominator is artifact
`active25_outer_even_b4_shell_i_exact_v2.json`; its fresh normal and `-O`
110-call reconstructions are byte-identical and scoped `AUDIT PASS`.

For ordinary even-B4 coordinates `G_i`, the missing outer numerator is

```
B48_ij = 48 * (J_HH(G_i,G_j) - J_HL(G_i,G_j)
               - J_HL(G_j,G_i) + J_LL(G_i,G_j)).
```

The transpose in the third term is mandatory.  The ordered mixed block need
not be symmetric.  The fixed radial-D16 cross uses its exact two amplitudes:

```
B48_0j = 48 * [a_R (J_RH - J_RL)_j
               + (a_inner-a_R) (J_VH - J_VL)_j].
```

No polarization factor is present in a matrix entry; the factor 2 appears only
when a later quadratic form contracts an off-diagonal entry.

## Exact cap-aligned pilot

The cheaper first route uses

```
C_(R,d)(t) = 1_{#large=R}
             ((B_R-R*delta-z_R)/(B_R-R*delta))^d,
z_R = sum_{t_i>delta}(t_i-delta),   d=0,1,2.
```

Count zero has only degree zero, giving 76 shell coordinates.  If the
distinguished coordinate is small, the marginal is its literal branch length
times `((gamma_R-z)/gamma_R)^d`.  If it is large, it is the exact
antiderivative of `((gamma_R+delta-z-t)/gamma_R)^d`.  The implementation has a
separate derivation and checks it against the pinned cap-slack producer and
literal rational antiderivatives through degree three.

In a common-`r` J face only counts `r` and `r+1` occur.  Therefore the shell J
matrix has exact block bandwidth one in count.  The fixed-D16 marginal is
lifted through the common angular density once per orbit, then all four signed
`R/V` against `H/L` contributions are combined by `(coordinate, exact domain)`
before integration.  A stage is one complete common count, never one
uncheckpointed all-count traversal.

## Exact work inventory

- common counts: 26;
- inclusion-exclusion faces: 585;
- natural even-B4 outer J: 55 `HH`, 100 ordered `HL`, 55 `LL` entries, with
  `LH=HL^T`; 1,965,600 literal entry/branch terms before exact-domain grouping;
- natural D16/B4 cross: 10 entries and 93,600 weighted branch-column terms;
- cap-slack degree 0--2: 76 entries, 151 nonzero I upper entries, 370 nonzero J
  upper entries, and 27,280 weighted D16-cross branch-column terms.

Thus the cap pilot reduces the expensive D16-side term inventory by a factor
`93600/27280`, about 3.43.  It does not claim that the cap space contains the
natural B4 space.

## Measured resource calibration and gates

Six already frozen exact D16-by-constant one-face probes take 3.98--5.69 s
(mean 4.6622 s) and at most 38,160 KiB RSS.  Scaling the 585 faces gives
2,727.4 s for degree zero.  A deliberately conservative 3x bound for degrees
0--2 is 8,182.1 s (2.27 h), versus 27,273.7 s (7.58 h) for ten natural B4
columns.  The separate exact cap shell blocks completed in 21.10, 56.95, and
110.03 seconds for maximum degrees 0, 1, and 2, at at most 44,640 KiB RSS.

Before a complete cross is authorized, the frozen successor must run the
single `(common_r,h)=(10,10)` face.  Required gates are wall time at most 20 s,
peak RSS at most 262,144 KiB, projected complete wall time at most 10,800 s,
and one worker.  Every common-r stage must be a fresh O_EXCL artifact with a
strict exact schema and complete source closure.

After the exact cap cross, natural B4 or a higher cap degree is continued only
if an exact particular-vector reconstruction has either quotient at least
`1.002` or gain at least `1e-4` over the same inner-only coordinate.  This is a
computational continuation rule, not a mathematical upper bound: failing it
retires this outer-polynomial family only.

The cap shell-only quotients (at most about 0.07135) do not determine the
combined quotient; no sign is inferred before the exact inner cross.

## Reproduction

```
python3 agents/structural-basis/tests/test_active25_outer_b4_j_cross_plan_v1.py
python3 -O agents/structural-basis/tests/test_active25_outer_b4_j_cross_plan_v1.py
python3 agents/structural-basis/code/active25_outer_b4_j_cross_plan_v1.py --preflight-only
python3 -O agents/structural-basis/code/active25_outer_b4_j_cross_plan_v1.py --preflight-only
```

The two preflight JSON streams must be byte-identical.  `--stage-r` always
fails in this revision.
