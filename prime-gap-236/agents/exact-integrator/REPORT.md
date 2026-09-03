# Exact-integrator report

Status date: 2026-09-01 (Europe/Berlin).  This directory is an independent
integration/matrix-construction workstream.  It is **not** by itself a proof of
`H_1 <= 236`; no quotient on an analytically usable capped support currently
recorded here reaches one.  A full-simplex reference quotient exceeds one, but
that support deliberately drops the indispensable `B_r` caps.

## Sources actually used

* Julia Stadlmann, *Bounded gaps between primes*, arXiv:2608.31126v1,
  submitted 2026-08-31.  Local TeX archive SHA-256
  `77b09473ece2a81fc0dc144ca604eadc3d876dd9125f9e095d3ef7ec6ff442a5`;
  PDF SHA-256
  `4296e63a3028fcff62725c7e751811679cbfea78e4d4213486b2f9a3e81ee994`.
* D. H. J. Polymath, *Variants of the Selberg sieve, and bounded intervals
  containing many primes*, DOI 10.1186/s40687-014-0012-7, especially the
  monomial-orbit basis and beta-integral construction in Section 7.

Section 5 of Stadlmann v1 only sketches its recurrence and says the author's code
will be uploaded later; no code or coefficient vector occurs in the source
archive.  The TeX literally calls

`{p(t)^2 (1-P_(1))^b : p symmetric, deg p=a, 2a+b<=D}`

a basis, which is not a literal finite linear basis until a coordinate convention
for `p`/the span of squares is specified.  Polymath's general coordinate basis is
`(1-P_(1))^a P_lambda` with `lambda` containing no part 1.  Its all-even-signature
subfamily is a useful speed restriction, but is smaller.  Every JSON result here
therefore stores the explicit list of `(a,lambda)` labels.  The introduction's
degree-at-most-21 statement and Section 5's `B_19` statement are genuinely
different in the v1 TeX; the source does not resolve that discrepancy.

There are also harmless but real Section 5.2.2 TeX slips: the displayed
`T_{b,s}` condition says `v_1+...+v_r<D` although there are `s` v-variables, and
nearby coefficient formulas interchange/range-mismatch some `a,b,k,r,s`
indices.  The implementation below is derived from the region definition, not
those typo-prone indices.

## Independent exact reduction

For the one-stratum support put

* `alpha=A_1+epsilon`,
* `eta=A_1-epsilon` (the common-variable cutoff in `J`),
* `beta_r=B_{1,r}`.

On a piece having `r` large coordinates, write `x_i=delta+z_i`.  For the `s`
small coordinates, inclusion-exclusion over their upper faces writes
`y_j=w_j+delta` for a selected set `H`.  Expanding monomial powers leaves terms
with

`Z=sum z_i`, `W=sum w_j`, `Z<=beta_r-r*delta`, and
`Z+W<=alpha-(r+|H|)*delta`.

For fixed expanded exponents `q_i,p_j` and residual power `c`, angular Dirichlet
integration gives

```
prod(q_i!)/(Q+r-1)! * prod(p_j!)*c!/(P+s+c)!
  * integral_0^min(gamma,L) Z^(Q+r-1) (L-Z)^(P+s+c) dZ,
```

where `gamma=beta_r-r*delta` and `L=alpha-(r+|H|)delta`.  The final one-variable
integral is a complete beta integral when `gamma>=L`; otherwise expanding the
second factor gives the exact finite sum

```
sum_{j=0}^v (-1)^j binom(v,j) L^(v-j) gamma^(u+j+1)/(u+j+1).
```

The grouped dynamic programs `_large_shift_dp` and `_small_box_dp` sum all
expansions by `(Q)` and `(|H|,P)`.  This is a closed-form version of the paper's
piecewise-polynomial `C_{m,i},D_{m,i}` construction and avoids enumerating any of
the 48-dimensional subsets.

For `J`, fix the `k-1` common variables and split each distinguished coordinate
at `delta`.  Each marginal has four polynomial branches:

| branch | distinguished interval upper endpoint | aggregate branch condition |
|---|---|---|
| `Sdelta` | `delta` | `alpha-U >= delta` |
| `Stotal` | `alpha-U` | `alpha-U <= delta` |
| `Ltotal` | `alpha-U` | small sum `Y >= alpha-beta_(r+1)` |
| `Lbig` | `beta_(r+1)-X` | `Y <= alpha-beta_(r+1)` |

The intersection of two marginal branches is a rational polygon in `(Z,W)`.
All its edges are horizontal, vertical, or slope `-1`; Green's theorem evaluates
every monomial exactly with only a short one-binomial expansion.  A tie at
`beta=alpha,Y=0` must be assigned to one branch.  An independent shortcut-vs-
generic test found this otherwise hidden double count and the implementation now
assigns it to `Ltotal`.

If every `beta_r>=alpha`, the support is the full simplex.  In that case both `I`
and `J` reduce directly to beta sums, bypassing all branch geometry.  Tests force
the shortcut and generic branch implementations to agree exactly in low
dimension.

## Symmetry compression

`P_lambda` is the sum over distinct permutations of `lambda` padded with zeros.
For products, a contingency table `n_(a,b)` records how many parts `a` and `b`
occupy the same coordinate.  Its labeled partial-matching count, corrected by
the automorphism factors of `lambda`, `mu`, and the resulting `nu`, gives the
integer structure constant in

`P_lambda P_mu = sum_nu c_(lambda,mu,nu) P_nu`.

This is stable in `k` once there are enough coordinates and is tested against
literal labeled-variable expansion.  The distinguished-coordinate identity

`P_lambda(u,t) = sum_e t^e P_(lambda minus e)(u)`

(one term for every distinct part `e`, plus `e=0`) reduces `J` to the same orbit
algebra.

## Verification

From this directory run:

```
python3 -m unittest discover -s tests -v
```

The 23 exact tests include:

* orbit structure constants versus literal small-variable expansion, including
  every no-part-1 signature through total degree six;
* all monomials of degree at most four on a rational triangle;
* a clipped rectangle;
* the full-simplex Dirichlet identity;
* published-support `k=1` moments;
* an independently decomposed published-support `k=2` area;
* a nonmonotone beta schedule whose feasible large-coordinate count reopens
  after an earlier impossible stratum;
* constant and arbitrary nonconstant `k=2` `J` moments from direct univariate
  antiderivatives;
* full-simplex shortcut versus the generic branch decomposition.

Eight additional fail-closed tests cover the integer-scaled D12 input,
including strict schema/token checks, source hashes, the common-denominator
identity, primitive content, and hostile metadata mutations.  The separately
authored grouped-evaluator audit runs another 12 exact tests:

```
cd ../structural-basis
python3 tests/test_grouped_evaluator_audit.py -v
```

They compare grouped and pairwise constructions on mixed odd and repeated-part
orbits, check serial/fork equality, enumerate the C10 branch-domain counts, test
zero-dimensional boundary assignments, and verify that rigorous stage resume
rejects stale script or integrator hashes.  Both suites passed on the hashes
recorded below.

The experiment driver reconstructs exact entries from the formulas, uses
ordinary floating point only as a diagnostic, computes a high-precision Decimal
generalized power iteration, rationalizes the vector, and finally checks the two
quadratic forms with `fractions.Fraction`.  Floating generalized eigenvalues are
often wildly false for these ill-conditioned Gram matrices and are never used as
evidence.  SQLite entries are only an experiment cache; tests and `--no-cache`
reconstruct from source.

## Selected exact results

All quoted quotients are exact rational-vector quotients (shown here in decimal),
not unverified eigenvalues.  Complete vectors, exact margins, parameters, basis
labels, matrix hashes, and code hashes are in `results/*.json`.

| support / basis | dim | exact quotient |
|---|---:|---:|
| published A, even `B_3`, k=48 | 6 | 0.8283001277650814 |
| enlarged `beta_(r>=3)=889/5000`, no-ones D4 | 12 | 0.8711999305485281 |
| same enlarged support, no-ones D5 | 19 | 0.8970523259661483 |
| same enlarged support, length(lambda)<=1 D6 | 16 | 0.8933002803104199 |
| A=1/4, epsilon=.0075, full simplex, even B8 | 40 | 0.9337624627813782 |
| same, no-ones D8 | 67 | 0.9366148430706379 |
| same, even B12 | 120 | 0.9662589904055093 |
| same, even B14 | 195 | 0.9752059238904460 |
| full simplex, epsilon=.0065, even B12 | 120 | 0.9664853277774192 |
| full simplex, epsilon=.0065, even B14 | 195 | 0.9751285849911197 |
| direct-HB C16 support, no-ones D4 | 12 | 0.8920052899993396 |
| direct-HB C10 parameters but full simplex, no-ones D12 | 272 | 1.0030189929241073 |

The last row is an exact positive full-simplex discovery result, not yet the
required capped-support result.  Its exact matrix hash is
`b882098bd6889ff251195b45153a2204e4df1c4ef843a2ae85dcc1b2fd3e041d`.
The explicit rational vector has been decomposed coefficient-for-coefficient as
12 degree-at-most-four terms plus eight total-degree bands, giving a
20-dimensional representation of exactly the same polynomial.  An independent
fail-closed check is:

```
python3 verify_degree_bands.py \
  results/hb_c10_fullsimplex_noones_D12.json \
  ../structural-basis/results/c10_D12_degree_bands.json
```

It verifies the source SHA-256 and every one of the 272 rational coefficients;
the current source hash is
`719c656e6e45388273b4c27f51f7a18b33e9ed1abb5f883e6fcc5de5d6d64a87`,
and the checker hash is
`1ec07fe1b1f80f07606b6d8e411d0c04c7091acc528cc72637b35554f0b7cb10`.

`grouped_fixed_vector.py` supplies a second capped-support evaluation path that
never trusts matrix entries: it first contracts the complete polynomial into
orbit/residual groups, then reconstructs one exact bivariate density on every
inclusion-exclusion face and marginal branch intersection.  Its 60-digit
Decimal regression on the C20 no-ones D4 exact vector gives
`0.887273520064345754675253407883144755761078452297139624169825`,
matching the independently reconstructed exact quotient.  The revised evaluator
clears all face-local density, marginal, and polygon caches after contraction;
this prevents the unbounded cache growth observed in exploratory D10 work.  The
current evaluator SHA-256 is
`47167e92a0f346e969706dc282ccb2dfd4ac31a0a75b654938ffbe8423cf4a4a`;
its imported recurrence SHA-256 is
`941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52`.
An exact final-hash C20 D4 run gives the same quotient and exact margin bit for
bit as the independent fixed-vector reconstruction in 12.42 seconds.

The full-simplex D12 vector was then evaluated on the actual C10 capped support
with the identical finite formulas at 100 decimal digits.  This discovery run
is decisively negative:

```
I       = 2.7875288276306926821592230624135828356785417338265857e-134
J       = 5.6387634188320203220629728487036345961414452711331005e-136
48 J/I  = 0.9709698476337895741123900041395560037415645658885284
shortfall from 1 = 0.0290301523662104258876099958604439962584354341114716
```

This is explicitly non-rigorous multiprecision evidence, not a certificate;
the large negative separation makes an exact run of that *fixed* vector
unproductive.  The self-contained artifact is
`results/c10_capped_fullD12_vector_grouped_mp100.json`, SHA-256
`02e1a6676a68380592fd272845f7714d583574bd74f73b9a96727171751281d9`.
It records 3,144.41 seconds for `I`, 4,654.30 seconds for `J`, all 312 `I`
faces, all 1,200 positive-measure `J` branch intersections, and separate parent
and maximum-child RSS values.

As a same-geometry exact regression, the capped evaluation of the D4
full-simplex rational vector has quotient
`0.8963160512159083` and artifact SHA-256
`51b1e6b36e289a69f7d52401ed9db7714e014a0182826f0e2d20a1f04b494874`.
This does not conflict with the earlier capped D4 discovery
`0.8963676783427826`: that number used a different, cap-optimized Decimal55
vector.  Treating its 12 finite decimals as exact rationals and rerunning the
exact grouped formulas reproduces `0.8963676783427826`.  Thus the discrepancy
is vector choice, not recurrence drift.

At even B8 the epsilon optimum is near `0.00515`; at even B12 it has moved near
`0.0065`; at even B14 the published `0.0075` beats `0.0065`.  Thus an epsilon
optimized at low degree should not be frozen for a higher-degree calculation.

The standalone command

```
python3 verify_result.py results/aquarter_fullsimplex_k48_B4.json
```

reconstructs every exact matrix entry without SQLite, compares the canonical
matrix hash, and evaluates the stored rational vector.  Add `--expect-above 1`
for a fail-closed positive certificate once one is found.

## Support-stratum basis

`src/stratum_integrator.py` adds the symmetric indicator that exactly `R`
coordinates exceed `delta` to any polynomial label.  These functions are
square-integrable despite their jumps.  Their matrix has the exact sparsity

```
I_(R,S)=0 for R!=S,       J_(R,S)=0 for |R-S|>1.
```

Indeed, removing the distinguished coordinate preserves the large-coordinate
count or lowers it by one.  The implementation filters the four exact marginal
branches accordingly.  Tests sum every tagged block back to the original global
`I` and `J` for nonconstant odd-signature polynomials, providing an exact
decomposition check.  `run_stratum_basis.py` reconstructs these sparse matrices
and emits the same kind of rational-vector certificate as `run_basis.py`.

Current implementation SHA-256 (after the recurrence audit) is
`941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52`
for `src/exact_integrator.py`.  Every JSON embeds an integrator hash and, more
importantly, a canonical exact-matrix hash that `verify_result.py` reconstructs.

## Explicit schedules and fixed-vector stratum amplitudes

`scheduled_fixed_vector.py` is a separate schedule-capable path; it does not
modify the pinned grouped evaluator.  It accepts canonical rational
`B_1,...,B_M` and uses the declared constant extension `B_m=B_M` for `m>M`.
The output binds the raw schedule file, a path-independent canonical schedule
hash, and a canonical hash of the complete support geometry.  Its exact C10 D4
constant-table regression reproduces the pinned three-cap denominator, `J`,
numerator, and all traversal counts bit for bit.  A nonmonotone schedule (with
an impossible `r=2` but feasible later strata) agrees with the independent
pairwise moment recurrence, and serial/fork results agree.  A direct `k=2`
constant-polynomial case checks `I=1/25` and `J=31/4000` by hand.  The script
SHA-256 is
`a2127b5edb1fd4287f2e105884dee9db7fcd13a5fc36b7016f01680cbb381928`;
the four-test SHA-256 is
`2b1de4cc3c84d00767ea7364c75febe79e02990c7ee8baab229adb8064cd6116`.

On the analytically checked nonconstant C10 schedule, the fixed full-simplex
D4 vector has exact quotient
`0.8986939777354343577044294966728082932988` (artifact SHA-256
`83baf24074e989bdd3bd6fd7e7b0ac866fb7e8bdcd6b55c0f05893e62f59202e`).
The exact 12-by-12 pairwise matrix has SHA-256
`6513e3835540b14037ffc8c62219083742e02c0b67e255ee85af0311c5e6250d`;
a Decimal120-discovered vector rationalized with denominator at most `10^12`
has exact quotient
`0.8986948736808947779503198417994740524393`.  Its independent grouped
matching-vector reconstruction is bit-for-bit equal (artifact SHA-256
`73fa22176730b9a443582df46cea5c0737798e9ebea6fb7a9a0ce534e522ba05`).

`stratum_amplitude.py` implements the cheaper fallback
`F(t)=a_{R(t)}F_0(t)`, where `R(t)` counts coordinates above `delta`.  In one
exact traversal it retains diagonal `I_R` and the three common-stratum branch
forms `(S_r^2,2S_rL_r,L_r^2)`, hence constructs the diagonal/tridiagonal
generalized problem.  Its direct mode inserts rational amplitudes into every
branch before squaring, so it independently reconstructs a selected vector
without trusting the block entries.  Four exact tests compare all entries to
the tagged pairwise recurrence, signed amplitudes to both block and direct
forms, serial to fork, and the exceptional `k=1` boundary convention.  The
implementation/test SHA-256 values are respectively
`d23d42315d7b518ae5d3f200a6192f47f3500d6eebd3a73fb6aa4ce7a23c7887`
and
`37f6da2d7bd229d6dbf895e3c4e5bb1118da191c4a69296a0919f05d4e319acb`.

Two C10 D4 calibrations selected amplitudes by a floating scaled eigensolve,
rationalized them, and then checked their quotients exactly in both the block
form and a fresh branch-scaled traversal:

| fixed polynomial | all-one quotient | exact rational-amplitude quotient | exact gain | artifact SHA-256 |
|---|---:|---:|---:|---|
| full-simplex D4 vector | 0.89631605121590824577 | 0.90028305974526119354 | 0.00396700852935294777 | `09ecb794833417e56537a43b65957ee70fc4d4c7bc17b944d9e02d12847dc87a` |
| cap-optimized D4 vector | 0.89636767834278262881 | 0.90009969268302918355 | 0.00373201434024655474 | `362b2b58938e3fdfdf0afd6916ddabce17cce71aa856795866f5d51f26dcb043` |

Thus stratum amplitudes give a real exact low-degree gain of about `0.004`, but
the D4 values remain well below one.  No D12 stratum-amplitude claim follows
without a new high-degree traversal.

`stratum_linear.py` implements the distinct multiplier space
`1_{R(t)=R} F_0(t) span{1,L,Z}`, with
`L=sum_{t_i>delta}t_i` and `Z=sum_{t_i<=delta}t_i`.  It builds exact
3-by-3 diagonal `I` blocks and block-tridiagonal `kJ`, then verifies a selected
rational vector by a fresh traversal after inserting the multiplier before
branch squaring.  Because `L F_0` is identically zero on the `R=0` stratum,
the discovery Gram matrix is not assumed invertible: exact per-stratum
principal minors select a positive-definite coordinate subset, zero Schur
directions are discarded, and a negative minor fails closed.  The selected
candidate is embedded back into the full coordinate vector before both exact
checks.  Its five exact tests include: reduction of all three
small/small, small/large and large/large constant-channel branch classes to
`stratum_amplitude.py`; a hand-integrated `k=2` switching example; a signed
block/direct comparison; exact symmetry and sparsity; and a `k=1` signed
counterexample whose ordinary marginal cancels while its first-u moment does
not; and exact null-`L` pruning with positive retained principal minors.  The
implementation/test SHA-256 values are respectively
`7400369a2e0e321ed032374f1e45f35785b0f0c53a085af18bf5ec2cb3c80162`
and
`6e08cd597be5c6a03138a434215909bde918df5f7f0f467d836e26c56fc4a8d6`.
These supersede the pre-pruning four-test hashes.
This driver is explicitly serial-only; no fork equivalence is claimed for the
new multichannel cache lifecycle.

On the capped-optimal C10 D4 polynomial, the exact degree-one multiplier
calculation has full coordinate dimension 48 and exact discovery dimension 47;
the only discarded Gram-null coordinate is `(R=0,L)`.  A rational vector has

```
48 J / I = 0.9348269207174672858115632780638459199716764033839710,
1 - 48 J / I = 0.0651730792825327141884367219361540800283235966160290.
```

This is an exact gain of `0.0384592423746846569999490154332` over the same
unmodified capped-optimal D4 polynomial and
`0.0347272280344381022596879355119` over its best rational scalar-stratum
amplitudes.  The block contraction and a fresh multiplier-inserted traversal
agree bit for bit over all 312 `I` faces and 1,200 `J` branch domains.  The
artifact SHA-256 is
`ffa607e0f2a8a3b6648f248efb13dc7ac2f1e7ef5809771f31c5f04b30f53158`.
The result remains below one, but the large exact correction justifies the
separate total-degree-two multiplier experiment in `stratum_quadratic.py`.

That total-degree-two experiment is now complete.  It uses the 96-coordinate
space
`1_{R(t)=R} F_0(t) span{1,L,Z,L^2,LZ,Z^2}`.  Exact Gram elimination retains
93 coordinates and discards precisely `(R=0,L)`, `(R=0,L^2)`, and
`(R=0,LZ)`, all identically zero because `L=0` on the zero-large-coordinate
stratum.  A Decimal100/160 all-spectrum Cholesky--Jacobi solve selected a
rational vector whose independently recomputed exact forms give

```
48 J / I = 0.9539674388485507785778746586710282622062114917575629,
1 - 48 J / I = 0.0460325611514492214221253413289717377937885082424371.
```

The exact gain over the degree-one multiplier result is
`0.0191405181310834927663113806071823422345350883735919`.  The serialized
96-dimensional block contraction agrees bit for bit with a fresh traversal
after inserting the selected quadratic multiplier, over all 312 `I` faces and
1,200 `J` branch domains.  The implementation and test suite SHA-256 values
are `62dad8c96005bdb06945552a36b6dc35cecea6633daa5f3cf06e514a6aa77234`
and `213dc2c61d92020d0f9c93ed934b7adf94171ae1cecd6201a249282d5de4017d`;
the three independent exact regression tests pass.  The result artifact is
`results/c10_stratum_quadratic_cappedopt_D4_exact.json`, SHA-256
`fbc8c38d2cf4241fdba03beb4251e2692e96af01ad4918c9a3a1075af2ed6e86`.

For the high-degree port, `stratum_linear_decimal.py` batches all affine
channel moments and pins every imported arithmetic dependency plus the input
coefficient hash.  On the exact D4 reference, separate Decimal100 and
Decimal160 traversals (with the same two-worker fork path intended for D12)
were checked entry by entry against the Fraction forms: 71 retained `I`
entries and 168 retained `J` entries.  The worst relative discrepancies were
`1.36e-60` and `4.89e-120`, respectively, both in the negligible `R=15`
diagonal `J` entry.  The exact small-problem suite also proves serial and
fork-two equality.  Driver/test/checker SHA-256 values are
`ba3ff83b186e7784634a97bf82f13ae3abdd4a4e753b226f0eaed23d659dfbc0`,
`737c765fa3a5dbd27deff469ef7de5c173a7098c7fcced11c0dfa64c8d108e6c`,
and `dc16f9da596f4d88f5e7e7464ab067855208aa8ea5d344f65ec06a9361e806c9`.
The Decimal100/160 artifacts have SHA-256 values `af9d1ff2...` and
`96e0655e...`.  These are discovery calibrations, not exact D12 certificates.

The direct high-degree transfer of the exact D4 affine multiplier to the
integer-scaled 272-term no-ones D12 polynomial is also complete.  With affine
channels retained through `R=11`, its Decimal100 forms are

```
I   = 9.404805046184364933993801445964141570663344888014190056715425272135294022457997898153502271689941759e311,
48J = 9.096037892995472439112847946761071826521884812110357334729191462324513650889701137458593316040739739e311,
48J/I = 0.9671692127936067321469619048809532704996719782235687810561380108925883953316516260403891506696291930,
48J-I = -3.08767153188892494880953499203069744141460075903832721986233809810780371568296760694908955649202020e310.
```

Thus this particular transferred vector is negative and cannot certify the
target.  It is not the D12 affine-space optimum.  All serialized dependency,
input, staged-I, count, positivity, and finiteness gates pass, but the artifact
is explicitly `theorem_ready=false` because it is a Decimal discovery run and
the historical I-stage producer lacked one transitive dependency hash.  The
result is `results/c10_D12_affine_transfer_decimal100_cut11.json`, SHA-256
`e83d3610b8130d743757a5f01aacc6ff2d2b2acd3128e5ff21b9a01cfa53d8da`;
the J traversal used 1,200 branch domains in 15,305.696 seconds and peaked at
335,768 KiB RSS.  The denominator agrees digit for digit with the independently
contracted frozen I-stage value.

The C70 global D4 matrix also exposed a discovery-algorithm pitfall.  The old
Decimal power iteration is not a largest-algebraic-eigenvalue algorithm when
`A^{-1}B` has a negative eigenvalue of larger magnitude.  Its exact rational
vector result is retained as a failed experiment, not an optimum claim.
`robust_generalized_solve.py` instead applies exact-diagonal scaling, Decimal
Cholesky reduction to a symmetric standard problem, and an all-spectrum Jacobi
solve at two precisions.  For C70 its Decimal160/240 Rayleigh values agree
through 158 digits, with residual bounds `5.19e-243` and `6.67e-310`; the
rationalized vector has exact quotient
`0.8037910083579469922003509212227199556346340151173167`.  Solver/test
SHA-256 values are respectively
`2086244acb674e5bd92e4880fb38d32d6dd981cd0272db595de2578554da257e`
and
`bf30d04d38af7a64e9b0adfbeabd45388f9de12335099a879970c3d506c4d2ef`;
the tests include the indefinite pencil with eigenvalues `-10,2` that defeats
largest-magnitude power iteration.
