# Reusable fixed-base stratum moment table through degree three

## Result

One fixed-base traversal contains enough information to assemble the complete
per-stratum multiplier pencil for every polynomial in `L,Z` of total degree at
most three.  The denominator is block diagonal in the large-coordinate count
`R`; the numerator is block tridiagonal.  No candidate-specific expansion is
mathematically necessary.

An exact prototype is frozen at
`agents/small-delta-frontier/stratum_moment_table.py`, SHA-256
`fcc471d8a0c8dce01147b6984f981ae5f40ef08a943d2f05ecbe1ec3b0eadccd`.
It passed:

- a signed `k=3`, degree-two, all-entry comparison with the independently
  written six-channel evaluator;
- literal hand integration of every degree-three `I` and `J` entry at `k=1`;
- normal and `python -O` test runs, 3/3 each; and
- a fresh exact C10 D4 degree-two traversal whose entire 96 by 96 `I` and
  `48J` matrices equal the frozen D4 oracle entry for entry.

The low-k test is
`agents/small-delta-frontier/test_stratum_moment_table.py`, SHA
`fe9ceb7767231751275931f1ea395fb910fa9f6c61e6c3cb6ccbabbc7e7d863b`.
The D4 oracle driver has SHA
`e9438c2a15f2fbffca181a3cc8febd5cd4bdcf448dac212b557223ae358cbdee`.
Its result is
`agents/small-delta-frontier/results/c10_D4_stratum_moment_table_oracle.json`,
SHA `25a054b526a43e9c1e0c042383722bd49257c57fc5b932c3d3f5393f5e54f598`.

This is implementation evidence, not a D12 quotient and not a sieve
certificate.  No degree-three production traversal was launched.

## Exact denominator table

Put

```text
P_d = {(a,b): a>=0, b>=0, a+b<=d},
E_(r,a,b)(t) = 1_{R(t)=r} F0(t) L(t)^a Z(t)^b.
```

For `u+v<=2d`, define

```text
U_r[u,v] = integral_{R=r} F0(t)^2 L(t)^u Z(t)^v dt.
```

Then, exactly,

```text
I(E_(r,a,b),E_(s,c,e))
    = 1_{r=s} U_r[a+c,b+e].
```

Thus degree three needs only 28 scalar moments per active stratum, rather than
55 separately expanded channel pairs.  On a face with `r` large shifted
coordinates and `h` small shifted coordinates, the implementation inserts

```text
L = r*delta + X,    Z = h*delta + Y
```

before exact polygon/interval integration.  This is the same aggregate
convention as the independently audited affine and quadratic evaluators.

## Exact marginal table

Fix the distinguished coordinate used in `J`.  Let `B` be one of the four
audited fiber branches

```text
Sdelta, Stotal, Ltotal, Lbig.
```

Write `sigma(B)=0` on a small branch and `sigma(B)=1` on a large branch.  If
the other 47 coordinates contain `r` large coordinates, a small branch belongs
to total stratum `r`, while a large branch belongs to stratum `r+1`.

For `0<=j<=d`, define the fixed-base distinguished moments

```text
M_(B,j)(x) = integral over branch B of t^j F0(x,t) dt.
```

For a multiplier monomial `(a,b)`, its branch marginal is

```text
small B: sum_{j=0}^b binom(b,j) L0^a     Z0^(b-j) M_(B,j),
large B: sum_{j=0}^a binom(a,j) L0^(a-j) Z0^b     M_(B,j).
```

The reusable table is

```text
W_r^(sigma,tau)[j,k,u,v]
  = sum over ordered B,C with sigma(B)=sigma, sigma(C)=tau
      integral_{D_(B,C)} L0^u Z0^v M_(B,j) M_(C,k) dx.
```

Here `D_(B,C)` is the exact audited branch-intersection domain.  Keeping the
branch sum ordered is important: it incorporates both cross-branch terms and
prevents either a missing factor two or an extra factor 48.  `W` is a `J`
table; the assembled numerator matrix is `k W`, with `k=48` applied exactly
once.

For `p=(a,b)`, `q=(c,e)`, define

```text
m_sigma(p) = b if sigma=0, else a,
rem_sigma(p,j) = (a,b-j) if sigma=0, else (a-j,b).
```

The matrix contribution of a common count `r` is

```text
J[(r+sigma,p),(r+tau,q)]
 = sum_{j<=m_sigma(p), k<=m_tau(q)}
     binom(m_sigma(p),j) binom(m_tau(q),k)
     W_r^(sigma,tau)[j,k,
         rem_sigma(p,j).L + rem_tau(q,k).L,
         rem_sigma(p,j).Z + rem_tau(q,k).Z].
```

Since `sigma,tau` are only zero or one, this connects only equal or adjacent
strata.  That is a direct proof of block tridiagonality, not a numerical
observation.

## Data structure

For degree three there are ten channel powers, in canonical order

```text
1, L, Z, L^2, LZ, Z^2, L^3, L^2 Z, L Z^2, Z^3.
```

A compact production representation is:

```text
I[r][u,v]                         u+v <= 6
J[r][SS][j,k,u,v]                 j<=k, u+v <= 6-j-k
J[r][SL][j,k,u,v]                 u+v <= 6-j-k
J[r][LL][j,k,u,v]                 j<=k, u+v <= 6-j-k
```

`LS` is the exact transpose of `SL`.  This is 28 `I` moments and at most
`115+180+115=410` canonical `J` moments per common stratum.  At C10 there are
16 `I` blocks; the upper storage bounds are therefore 448 denominator moments
and 6,560 marginal moments.  The assembled degree-three matrix has dimension
160 before removing the six identically zero `R=0` channels containing a
positive power of `L`.  Its nonzero upper-block storage is only

```text
16 * 55 diagonal entries + 15 * 100 adjacent entries = 2380.
```

The prototype retains both transposes internally to make hostile symmetry
checks immediate.  A production serializer should use the canonical layout
above and reconstruct the transpose.

## Exact operation counts

The frozen degree-two C10 artifact has 748 same-branch and 452 different-
branch domains.  These counts follow exactly from

```text
N_same + N_cross = 1200,
21 N_same + 36 N_cross = 31980.
```

The relevant per-domain counts are:

| quantity | degree 2 | degree 3 |
|---|---:|---:|
| channels | 6 | 10 |
| independent channel products, same branch | 21 | 55 |
| channel products, cross branch | 36 | 100 |
| distinguished-moment orbit products, same branch | 6 | 10 |
| distinguished-moment orbit products, cross branch | 9 | 16 |
| scalar aggregate moments, same branch | 41 | 115 |
| scalar aggregate moments, cross branch | 60 | 180 |
| C10 J channel products | 31,980 | 86,340 |
| C10 J moment orbit products | 8,556 | 14,712 |
| C10 J scalar aggregate integrations | 57,788 | 167,380 |
| C10 I scalar aggregate integrations | 4,680 | 8,736 |

Thus degree three reduces the expensive marginal orbit-product contractions by
a factor `86340/14712 = 5.87...`.  It replaces them with more scalar polynomial
integrations, but polygon construction and every polygon monomial are cached;
those scalar evaluations are materially cheaper.

The fresh D4 degree-two run confirms that cost model.  It used exactly 8,556
marginal moment products and 57,788 scalar J moment evaluations, reconstructed
all 312 I faces and 1,200 J domains, and completed in 460.515 seconds with peak
RSS 49,252 KiB.  The frozen channel-pair construction took 1,988.494 seconds on
the same D4 base, so the present unvectorized prototype is 4.318 times faster.
Every exact matrix entry and the stored particular-vector contraction agree.

## Can one fixed-base traversal build the full matrix?

Yes, with one qualification about what “one traversal” means.

The 272 base coefficients need be expanded only once into:

1. the grouped square-residual payload used by all 28 `I` moments; and
2. the four vector-valued marginal payloads `(M_B,0,...,M_B,3)` used by every
   `J` entry.

An outer traversal over a pair of marginal orbit keys can emit all 16 `(j,k)`
tags simultaneously.  Radialization and domain integration can likewise carry
the `(j,k,u,v)` tag as a structure-of-arrays payload.  Therefore a single
*batched tagged* base-product traversal assembles the full table.  It does not
mean that only one scalar integral remains: the 167,380 aggregate moments are
genuine outputs, although their polygon geometry and monomial primitives are
shared.

The frozen prototype already shares base moments across all multiplier channel
pairs, but loops separately over its 14,712 marginal-moment products.  The
next implementation step is to fuse those products into a vector-valued
orbit multiplication.  This is the remaining combinatorial bottleneck.  A
D12 runtime cannot be inferred responsibly from D4 alone because the D12
fixed base has 1,575 grouped I terms and 695 marginal components.  The safe
launch gate is a source-bound timing of a few D12 faces with the fused SoA
payload, followed by a projection below the requested resource limit.  No
degree-three D12 production command is authorized by this report.

## Reproduction

Low-k and hand tests:

```bash
python3 agents/small-delta-frontier/test_stratum_moment_table.py -v
python3 -O agents/small-delta-frontier/test_stratum_moment_table.py -v
```

The already-completed D4 oracle can be regenerated at a new output path with

```bash
python3 agents/small-delta-frontier/check_stratum_moment_d4_oracle.py \
  /tmp/c10_D4_stratum_moment_table_oracle.json
```

It fails closed unless the fixed D4 input SHA is `2b11a18c...`, the frozen
quadratic oracle SHA is `fbc8c38d...`, all matrix entries match exactly, both
face/domain counts match, and the particular rational-vector contraction is
identical.
