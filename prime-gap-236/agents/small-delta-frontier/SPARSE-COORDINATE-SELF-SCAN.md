# C10 D12 sparse coordinate self-form scan

Date: 2026-09-02 (Europe/Berlin)

## Status

**PRELAUNCH PACKAGE PASS; NO NEW SELF-FORM VALUES IN THIS ARTIFACT.**  The
complete 20-coordinate compressed band model uses coordinate 19 (`H12`) as a
fixed projective gauge.  This package expands each of the other 19 signed unit
coordinates into a standalone exact no-ones orbit polynomial, records its
known cross action against the serialized Decimal100 base, and reconstructs
the exact grouped-evaluator cost counts without integrating a form.

The full manifest is
`results/c10_D12_sparse_coordinate_scan_manifest.json`, SHA
`967a004ed5f02dc08d07bd9ab8f5af1050b345427327935b96d0979ae531787f`.
The 19 inputs are under `results/sparse_coordinate_scan_all/`.

The already-evaluated `+H6` line is omitted from the adaptive launch queue.
The next two exact relative-residual directions are:

- `-H7`, 15 labels, SHA
  `22f643231c8c44a22674622371ff84ba164e923ad57090afd1ac89157c2cde84`;
- `-H5`, 7 labels, SHA
  `f6aec9b2fae2a3edce726c95582019a6b1481dfe0146b39f1cbc83e69d3674d1`.

These bytes also appear in the early two-direction tranche manifest SHA
`2e8ca8abda06b1763c1a449372677e79acec1a05d288eda20c68b75c4c64e004`.

Both leading self-form runs subsequently completed and their full lines are
negative:

| direction | self quotient | complete base-direction line maximum | maximizing `s` |
|---|---:|---:|---:|
| `-H7` | `.4016135443959186579...` | `.9709699455402759047905961341880613...` | `1.4326303820525102e-23` |
| `-H5` | `.3927862580226604282...` | `.9709699354783650309824573762640712...` | `1.3599870296023066e-23` |

The H7 result/stage SHAs are `4b47730d...`/`0ac25784...`; the H5 SHAs are
`0aa72739...`/`ced65a77...`.  The fail-closed reconstructions are
`c10_D12_H7_line_reconstructed.json` (SHA `b937daf2...`) and
`c10_D12_H5_line_reconstructed.json` (SHA `e7810374...`).  Consumer SHA
`032387cb...` and test SHA `5ff3dce5...` pass three hostile tests in normal and
optimized modes, including final-Decimal-unit, count, stage, and alias
mutations.  These are two failed coordinate lines, not an upper bound for any
larger coordinate span.

## Exact direction and ranking semantics

Let `theta` be the serialized Decimal100 20-vector, and let `a=A theta`,
`b=(48J) theta` be the exact Fraction halves recovered from the serialized
gradient.  For coordinate `i`, choose `sigma_i` in `{+1,-1}` so

```text
R_i = D0*(sigma_i*b_i) - N0*(sigma_i*a_i) > 0.
```

The emitted polynomial is the exact band-map expansion of
`d_i=sigma_i e_i`.  Thus its future evaluator fields have the unambiguous
semantics

```text
A11 = I(d_i,d_i),  B11 = 48*J(d_i,d_i),
a01 = I(theta,d_i), b01 = 48*J(theta,d_i).
```

Factor 48 occurs once.  The launch ranking uses the scale-invariant relative
coordinate score

```text
2*abs(theta_i)*R_i/D0^2.
```

Its exact first three entries are `+H6,-H7,-H5`; after retiring H6, the launch
queue begins `-H7,-H5,+H8,...`.  This is only a first-order scheduling rule,
not an assertion about any finite quotient or the full compressed optimum.

## Per-line algebra and exact crossing tests

Once a direction's two self forms have been freshly evaluated, its complete
projective line is

```text
D(s)=D0+2*s*a01+s^2*A11,
N(s)=N0+2*s*b01+s^2*B11.
```

The stationary polynomial (up to a factor two) is

```text
R_i + (D0*B11-N0*A11)*s + (B11*a01-A11*b01)*s^2.
```

First require the exact or rigorously enclosed positivity condition
`D0*A11-a01^2>0`.  Put
`h0=N0-D0<0`, `h1=b01-a01`, and `h2=B11-A11`.  Then the line crosses one
exactly under the following exhaustive test:

- `h2>0`; or
- `h2=0` and `h1!=0`; or
- `h2<0` and `h1^2-h0*h2>0`.

Equivalently, after an endpoint I-stage at nonzero `tau` has recovered A11,
the endpoint quotient must strictly exceed

```text
q_tau_star = 1 + (h0+tau*h1)^2/(h0*D_tau).
```

No manifest entry supplies A11 or B11, so every entry explicitly remains
`rigorous=false`, `theorem_ready=false`, and requires a fresh scalar
reevaluation.

## Reconstructed cost counts

The builder uses the frozen grouped evaluator's exact orbit products,
square-residual grouping, distinguished-coordinate split, and branch-domain
gates, but deliberately stops before moment integration.  Every direction has
312 I faces and 1,200 J branch domains.  The leading two costs are:

| direction | labels | orbit keys/terms | I groups/terms | marginal components/orbits | J domains |
|---|---:|---:|---:|---:|---:|
| `-H7` | 15 | 225 / 689 | 129 / 502 | 34 / 15 | 1200 |
| `-H5` | 7 | 49 / 102 | 38 / 134 | 14 / 7 | 1200 |

All remaining exact counts and byte SHAs are carried next to the corresponding
input in the manifest.

## Reproduction and tests

- builder SHA `82ee455d319b770c114428fe98dfc5b76d0dd7ca1d3c095729c60ac2c23fb344`;
- tests SHA `33a7ec31f1f673ab78a617f8968630fd37998730c76ebe938205151d65b224e2`.

Run from `prime-gap-236/`:

```bash
python3 agents/small-delta-frontier/test_sparse_coordinate_scan.py
python3 -O agents/small-delta-frontier/test_sparse_coordinate_scan.py
```

Both tests pass in both modes.  They independently reconstruct all signed
block labels and weights, all 20-to-272 owners, every D0/N0/a/b/R/derivative
identity, factor 48, the exact ranking and gauge omission, bind all 19 files,
and rerun the H7/H5 tranche byte-for-byte.  The full generation took 160.54 s
wall at 32,552 KiB peak RSS; the H7/H5 tranche took 12.53 s at 25,276 KiB.

The launch template is stored in the manifest.  Any completed discovery
output needs an independent Decimal-operation replay and full projective-line
reconstruction before it affects route selection.
