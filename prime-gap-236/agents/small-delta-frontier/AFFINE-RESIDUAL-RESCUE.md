# Matrix-free D12 affine-residual rescue

## Verdict

**CONDITIONAL GO for the five-coordinate boundary screen; NO-GO for all 39
effective coordinates.**  The target traversal must not start until the
ongoing transferred-vector result has completed, its byte SHA is known, its
sign has been inspected, and root gives a resource go.

This is a discovery/residual calculation.  It is not an exact D12 certificate,
does not prove an affine-space optimum, and does not imply a D12 sign.

## Bilinear formulas

Fix the 272-term D12 polynomial `F0`.  Write

\[
 \phi_0=1,\qquad \phi_1=L,\qquad \phi_2=Z,
 \qquad H_{r,p}=1_{R=r}\phi_pF_0.
\]

For an affine multiplier vector `c`, put

\[
 F_c=\sum_jc_jH_j,qquad D=I(F_c,F_c),\quad N=48J(F_c,F_c),
 \quad q=N/D.
\]

The matrix-free data for coordinate `j` are

\[
 a_j=I(F_c,H_j),\quad b_j=48J(F_c,H_j),\quad
 d_j=I(H_j,H_j),\quad e_j=48J(H_j,H_j).
\]

Thus the exact Rayleigh residual is

\[
 r_j=b_j-q a_j,
\]

and every two-vector screen is obtained from

\[
 \frac{N+2tb_j+t^2e_j}{D+2ta_j+t^2d_j}.
\]

No entry with two distinct rescue coordinates is needed.

On an I face `(r,h)`, let `z` and `w` be the shifted large/small aggregate
variables.  The fixed multiplier is

\[
 C_{r,h}(z,w)=c_{r,0}+c_{r,1}(r\delta+z)
                         +c_{r,2}(h\delta+w).
\]

If `W_{r,h}` denotes the already grouped density of `F0^2`, one vector-valued
face integral gives simultaneously

\[
 a_{r,p}=\int W_{r,h}C_{r,h}\phi_p,qquad
 d_{r,p}=\int W_{r,h}\phi_p^2.
\]

For J, let `M_{sigma,p}` be the channel-p marginal on branch `sigma`, and

\[
 C_\sigma=\sum_pc_{R(\sigma),p}M_{\sigma,p}.
\]

For a same-branch domain, the cross and diagonal lanes are

\[
 \langle M_{\sigma,p},C_\sigma\rangle,qquad
 \langle M_{\sigma,p},M_{\sigma,p}\rangle.
\]

For two distinct unordered branches `sigma,tau`, the scalar quadratic contains
`2<C_sigma,C_tau>`.  Its bilinear cross lanes are exactly

\[
 \langle M_{\sigma,p},C_\tau\rangle,qquad
 \langle C_\sigma,M_{\tau,p}\rangle;
\]

there is no additional factor two.  Contracting these two lane families with
`c` recovers `2<C_sigma,C_tau>`.  This identity is the factor check that most
directly guards the small/large distinguished-branch convention.

The implementation packs all local lanes into one vector polynomial before
the radial/domain integral.  Consequently it performs one geometric integral
per retained branch domain and never materializes the 47-dimensional
untruncated affine Gram matrix.  With cutoff 11 the effective dimension is

\[
 16+2(12)-1=39;
\]

the subtraction is the exact null coordinate `(R=0,L)`.

## Exact D4 validation

The producer is
`affine_residual_matrixfree.py`, SHA-256
`49dd0a934d011e67200653248d8442e6d6f6b1bbe98a08e6be26bb3afc12ed98`.

Against the stored exact 48-coordinate D4 blocks, the all-effective run checks
all 39 vectors `Ac`, `Bc`, and every requested diagonal `A_jj,B_jj` exactly:

- artifact SHA `097cae2a07fb782fb3092535e6e2d8e9071678259ce30c76eb35efec52c4dfac`;
- 312 I faces and 1,200 J domains;
- 318.71 seconds total (304.59 J seconds);
- peak RSS 40,848 KiB.

The exhaustive artifact was produced by an immediately preceding source
revision whose integration core is byte-for-byte the same; the only later
producer edit strengthened the target baseline-result loader.  The current
source is separately bound to the exact boundary artifact below and to the
low-k literal matrix test.

The proposed boundary set is

\[
 \mathcal S=\{(11,1),(11,L),(11,Z),(12,1),(13,1)\}.
\]

It is a rigorously valid five-dimensional rescue space: any achieved quotient
in `span(F_c,{H_j:j in S})` is also achieved in the full affine function space.
A negative result would not bound the omitted directions.

The exact D4 coordinatewise diagnostic

\[
 \sum_j\frac{r_j^2}{D A_{jj}}
\]

assigns the subset the share

\[
 0.9999981141878653561628485706209519072\ldots
 >\frac{999998}{1000000}
\]

by exact Fraction comparison.  This diagonal proxy ignores Gram correlations
and is only a selection heuristic; validity of the subspace does not depend on
the percentage.  The checker is `select_affine_residual_boundary.py`, SHA
`c1d51aff55c82336cd56f7e963813bf2fa0117ab7d315641026e3a3e90dbad38`.

Current-source boundary calibration:

| arithmetic | I seconds | J seconds | total seconds | peak RSS |
|---|---:|---:|---:|---:|
| Fraction exact | 2.03 | 29.35 | 31.37 | 39,364 KiB |
| Decimal100 | 0.78 | 9.42 | 10.20 | 39,760 KiB |

Both reconstruct 45 I faces, the four common counts `10,11,12,13`, and 222 J
domains.  The exact and Decimal artifacts have SHAs
`22523e10881ab5b4bddcda4f8f20c01dbc14f6f341e10f8cbb7e4e874029fe9f`
and
`369065fbe81c2c12285501c4c362e8e527e694f53d257b8c69a5f0ca957734fe`.

The low-k test independently builds the complete k=3 affine matrices and
compares every selected cross and diagonal entry to the matrix-free result.  It
also checks the current-source-bound D4 artifact, the two-vector formula, and
baseline count mutation rejection.  Five tests pass under normal and `-O`:

```sh
python3 -m unittest prime-gap-236/agents/small-delta-frontier/test_affine_residual_matrixfree.py
python3 -O -m unittest prime-gap-236/agents/small-delta-frontier/test_affine_residual_matrixfree.py
```

Test SHA:
`1c359cd8bd72816f31960b611df0ecd7cfeb621cfc7da493171c0ec382e98ec7`.

## Cost projection and gate

The D4-to-D12 residual-orbit count changes from 5 residual orbit labels
(`5^2=25` ordered products) to 77 (`77^2=5929`), a factor `237.16`.
An empirical, more conservative factor comes from the completed scalar grouped
runs: D4 transferred J took 29.73 seconds, while the D12 fixed scalar J took
4,654.30 seconds with two workers, hence at most 9,308.60 serial-equivalent
seconds, a ratio about `313.1`.

Applying that ratio to the boundary Decimal100 J calibration gives about
`0.82` hours.  Multiplying the whole estimate by three for degree-dependent
packed-polynomial and cancellation overhead gives **2.46 hours**.  The I phase
is smaller; the conservative end-to-end launch budget is **2.6 hours**.

The existing D12 grouped child peak is 317,904 KiB.  Scaling by the observed
D4 packed/scalar memory ratio and then doubling gives a conservative bound of
about **0.68 GiB**, below the 0.8-GiB gate.

By contrast, the all-39 D4 J phase is about 9.7 times the boundary phase.  Its
conservative D12 projection is roughly 24 hours.  Therefore:

- **GO, conditionally:** one serial Decimal100 boundary run after the baseline
  is complete, the host has at least 1.4 GiB available, and root explicitly
  gives the sign/resource go;
- **NO-GO:** an all-39 D12 traversal;
- if a boundary direction gives material gain, rerun only that direction at a
  second precision before rationalization;
- if every two-vector gain is immaterial, retire this boundary rescue without
  claiming an affine-space upper bound.

## Launch command (prepared, not executed)

The pending baseline path is
`agents/exact-integrator/results/c10_D12_stratum_linear_decimal100_cut11.json`.
After it exists, replace `BASELINE_SHA_AFTER_COMPLETION` by its byte SHA.  The
loader requires the caller-supplied SHA and checks status, completion, gates,
272/48 dimensions, 695 marginal components, 1,200 J domains, source and
multiplier SHAs, cutoff, parameters, precision, finite forms, and the quotient
reconstruction.  It rereads every dependency and input at the end.

```sh
python3 prime-gap-236/agents/small-delta-frontier/affine_residual_matrixfree.py \
  prime-gap-236/agents/exact-integrator/results/hb_c10_fullsimplex_noones_D12.json \
  prime-gap-236/agents/exact-integrator/results/c10_stratum_linear_cappedopt_D4_exact.json \
  --expect-input-sha256 719c656e6e45388273b4c27f51f7a18b33e9ed1abb5f883e6fcc5de5d6d64a87 \
  --expect-multiplier-sha256 ffa607e0f2a8a3b6648f248efb13dc7ac2f1e7ef5809771f31c5f04b30f53158 \
  --alpha 79247/300000 --delta 1/100 --eta 76247/300000 \
  --beta1 3/20 --beta2 3/20 --beta3plus 97/625 \
  --linear-cutoff 11 --coordinates boundary --decimal-dps 100 \
  --baseline-result-json prime-gap-236/agents/exact-integrator/results/c10_D12_stratum_linear_decimal100_cut11.json \
  --expect-baseline-sha256 BASELINE_SHA_AFTER_COMPLETION \
  --progress \
  --output prime-gap-236/agents/small-delta-frontier/c10_D12_affine_residual_boundary_decimal100.json
```

This command remains deliberately unlaunched.
