# Result

Status: active research; **the target is not closed**.

## Exact `R<=9` one-band campaign update (2026-09-03 13:32 CEST)

All thirteen exact base `A=I(H)` shards are complete and independently
audited.  Their strict full-direction aggregate has SHA-256
`e00feb75871e9a4f9be34e9042283f0eda1aa16d139fe27dd2c5deb044865c44`;
the current symmetric `R<=9` direction selects the already-audited counts
`0..9`.

The exact mixed form is still incomplete.  Fixed-polygon v8 shards `r=8`
and `r=9` are complete and have independent result-level passes, with
SHA-256 hashes
`ffbeb7f3cbc13c279a8c89b561d93af36fafed8d2442c90d22bb6c244e531631`
and
`e9397f72f78f9ad53716d61bb3f10854a640081f81632028904836d6c6778d88`.
The durable r8/r9 audit report has SHA-256
`00de4af6856e1b81425f875b829eabd526c35968ecb172ea3cd7804d63c69531`.
Shard `r=7` has also published and passed its independent result audit
(report SHA-256
`2383a1f46c2f4fc243736b5248fccdf5c3c99e6753ed32bdc042d7404549ca00`),
v8 `r=6` is running, and `r=0..5` are missing.  The `R<=9` branch inventory requires
all four branches for `r=0..8`, only the two small-distinguished-coordinate
branches for `r=9`, and no higher counts.

The Green-formula v9 implementation has a scoped source-level
**PRE-CERTIFICATE AUDIT PASS** (report SHA-256
`22eeabeba62a15dd0509e0b2b9215198e2056418dbc8f5a5c2b906d531ba34af`),
pinned to core/runner/checker SHA-256 hashes
`019fecc00727bfdeb62fc3a02277298c6d08543db4d71ce47f049a73bc1d7a0c`,
`ad38951dadecdb5a5c51d1221b0a078bc9f804e9c4ec8d434706fca55a11935a`,
and
`7dbb352011d840a5bddf8f6f101f864d0a1b1e436ff4ebb5533ef1137217b4a7`.
This is an implementation/formula verdict only: no v9 target result, exact
mixed-form aggregate, sign computation, compact certificate, or final
certificate audit exists yet.  Therefore no theorem is claimed.

## Historical exact one-band checkpoint (2026-09-03 11:58 CEST)

The complete exact outer norm is now reconstructed and independently
audited.  All counts `r=0..12` agree between the primary paired engine and a
separate radial checker; the strict aggregate
`d14_one_band_a_aggregate_exact_v2_strict.json` has SHA-256
`e00feb75871e9a4f9be34e9042283f0eda1aa16d139fe27dd2c5deb044865c44`,
and its scaled value is
`5.827639719675758042725284281148949297939045992...e-68`.  The hostile
aggregate audit is `PASS` (report SHA `ab227302...`, result SHA
`9c846bb1...`).

The exact mixed form `b=48J(F,H)` remains the only scalar blocker.  A cached
fixed-denominator engine with independently tested equality to the prior
engine is running the two most expensive high-count shards under hard
30-minute caps; no partial sum is being promoted.  In parallel, hostile
testing of the full replay checker has already found and repaired malformed
shard-hash acceptance, Python Boolean/float integer aliases, host-specific
inode hashing, and stale-bytecode exposure.  The checker is not frozen until
that audit terminates cleanly and will then be repinned to the final exact
mixed engine.

## Historical exact one-band checkpoint (2026-09-03 09:20 CEST)

The theorem-strength blocker remains the exact scalar inequality
`b^2-A*D>0`; no target quotient is claimed yet.  The frozen cross formula now
has two independent pre-certificate audits.  V1 (report SHA `ebcd39d0...`)
was checked against a named-monomial rational-polygon oracle over all four
Definition-5 branches, random geometries, both endpoint orientations, target
scales, and orbit multiplicities.  Fast v2 (report SHA `6d7326c6...`) was
separately checked coefficient by coefficient for both common-denominator
integer maps, affine collection, inclusion--exclusion shifts, and exact
denominator restoration.  Both hostile suites pass normally and under `-O`.
These are source/formula verdicts only; all thirteen target cross shards still
require a result-level audit.

For `A=I(H)`, the paired high/low exact engine matches the older separate
engine bit-for-bit on count 6 and is 2.01 times faster.  The count-6 scaled
value is exactly represented and has decimal display
`1.5760446813246890208618525619e-69`; it is exactly `10^76` times the
preserved unscaled value.  Its artifact/source/test SHAs are
`46132be3...`/`2e91dbd8...`/`4d5402a8...`.  Immutable count shards are now
being produced.  The first target cross benchmark is still running, so this
checkpoint does not promote the Monte Carlo projection signal to a proof.

## Current checkpoint (2026-09-03 08:38 CEST)

No exact capped `k=48` quotient above one has yet been obtained, so
`H_1<=236` is **not proved**.  The first strongly positive combined signal on
an analytically viable single-band route is now reproducible, however.

The complete canonical degree-19 inner vector has exact quotient

```text
48J(F,F)/I(F) = .9867930836956087556586707101860344621...,
deficit/I(F)  = .0132069163043912443413292898139655379....
```

The repaired standalone checker `verify/check_bv_rational_vector_direct_v2.py`
(SHA `ff2046ce...`) reconstructs all 13,955 polynomial-square and
marginal-square orbit terms directly, reads no cache or serialized matrix,
and reproduces the exact forms byte-identically in normal and optimized
Python.  Its result SHA is `8b0d47b2...`.  V2 pins the original arithmetic
engine but rejects noninteger basis fields and noncanonical rational strings;
this repairs a hostile v1 float-to-integer coercion counterexample.  A fresh
independent mathematical/software audit now gives `PASS` (report SHA
`6a4623ec...`): it reproduced both modes byte-for-byte, matched the forms with
a separate scan-free contraction, checked the complete 568-label basis and
single factor 48, and exercised ten additional malformed-record attacks.

The matching sorted-removal support keeps one outer band only, so the valid
one-band Riesz lemma applies without the indefinite multiband kernel.  Its
exact checker/result/test SHAs are
`fff28057...`/`c9be4426...`/`9b0e1409...`; the rational parameters are

```text
delta=1/60, A2=9230917/36000000,
alpha2=9500917/36000000, eta=8960917/36000000,
B1..B12=(140375,157041,168544,174338,185488,190375,
         193097,197146,202047,207090,211668,211668)/10^6.
```

The support gate covers 1,500 fixed cases, 19,182 IIb records, and 43,008
IIc cells exactly.  The changed support now has a scoped hostile `AUDIT PASS`
(checker/result/report SHAs `b4e889ab...`/`fea750c7...`/`652f1b16...`).  The
independent oracle found 2,522 ordinary-prefix IIb affine roots omitted by the
generic producer, but checked the complete 24,226-root inventory and proved
that no omission changes a frozen minimum or gives a counterexample.  It also
reconstructed all IIc cells and the direct-Heath--Brown/Proposition-1
interface.  Thus the exact tuple is analytically cleared; the generic producer
must not be reused for a new tuple without repair.

On this support, two calibrated natural-D19 finite-projection runs estimate

```text
b^2/(A I(F)) = .03680472098 +/- .00054888164,
                .03629520584 +/- .00049266945,
A=I(H), b=48J(F,H),
```

against the exact `.01320691630...` threshold.  The naive two-run combination
is `.0365225449 +/- .0003666378`, an excess about `.0233156`; it is still
heuristic because the standard errors are empirical.  A separate frozen-run
checker passes.  The lower-degree screen selected the 195-label degree-14
polynomial: its two-run estimate is `.02218605411 +/- .00053100096`, with a
three-standard-error lower value `.02059305124`, still above the exact
threshold.  Rounding that vector to common denominator `10^38` changes its
exact full-simplex quotient by only `1.8761e-21`; a common-random-number capped
screen measures proposal-weighted relative L2 change `1.97e-12` and no
resolved projection loss.  Fine-grid and capped-screen result SHAs are
`72208259...` and `6c2349a1...`.  This grid-38 vector is now in the exact
one-band `A,b` reconstruction.  Only an exact rational or outward-rounded
inequality `b^2/A > I(F)-48J(F,F)` will promote the result.

The full degree-20 source-bound matrix build also remains active.  The older
active25 D16-plus-count-shell calculation has completed both normal and
optimized independent replays and is rigorously negative on its entire
27-dimensional space; it is retained only as an obstruction/regression.

## Previous checkpoint (2026-09-03 04:40 CEST)

No exact capped `k=48` quotient above one has yet been obtained.  The
theorem-critical active25 D16 calculation has not been launched: staged
revisions v3--v5 each failed a concrete independent prelaunch check, most
recently because v5 accepted fabricated preexisting future-dated stages even
when its ledger was genuine.  A distinct no-resume v6 is being frozen and
reviewed; it must begin with exactly one externally anchored ledger leaf, and
its final arithmetic will still be reconstructed by an independent checker.

Two new exact finite-block facts are durable:

- the active25 outer even-`B4` denominator block has an independent
  normal/optimized scoped `AUDIT PASS` (artifact/checker/result/report SHAs
  `ffe98de8...`/`aa8b8cdb...`/`9888d319...`/`8a2a2040...`), proving exact
  rank 10 and ten positive LDL pivots; its J block is still missing;
- a new count-specific cap-slack shell basis gives exact rational particular
  quotients `.06838699356113082`, `.07092104797623179`, and
  `.07134554581738625` through degrees 0, 1, and 2.  The diminishing
  shell-only gain is far below one, so this family is retained only for its
  cross with the strong inner D16/D18 coordinate.  These new forms are tested
  but not independently audited.

The D18 natural outer polynomial remains a useful uncapped relaxation at
`1.0094665456455...`, not a proof.  A target-density sampler estimates that
only about `.0010`--`.00136` of its outer I mass lies in the active25 cap;
the stricter run fails its own calibration ESS gate and makes no rigorous J or
quotient claim.  It motivates the cap-slack basis rather than authorizing or
retiring an exact calculation.

The strongest analytically certified wide support is now the independently
audited nonuniform rising-tail outer schedule

```text
(597/5000,633/5000,669/5000,141/1000,737/5000,773/5000,
 1553/10000,809/5000,81/500,3329/20000,.1690,.1695,.1718,
  .1737,.1752,.1762,.1764,.1774,.1782,.1790,.1796,.1801,
  .1806,.1811,.1815,.1815,...).
```

It retains the full BV D16 inner support, has active outer counts `0..25`,
and pointwise dominates the preceding plateau supports.  Exact normal and
optimized reconstructions are byte-identical (checker/artifact/report SHAs
`c96b1d1c...`/`111a48a2...`/`0c89e776...`).  The least dynamic-IIc margin is
`549979/120000000000`, count 26 is strictly empty, and a simultaneous
25-parameter radius-`1/1000000` box remains admissible.  Its exact constant
shell volume is 1.3222099457551302 times that of the audited `.16605` support.
This is an analytic support result only: the exact capped `k=48` quotient is
still missing.

## Current theorem-critical campaigns (2026-09-02)

The analytic C10 direct-Heath--Brown route and the 48-tuple implication have
independent `AUDIT PASS EXCEPT CERT`; the only missing theorem-strength item is
a positive capped `k=48` finite-dimensional certificate.  The complete C10
D12 transfer of the exact D4 quadratic stratum multiplier is now finished and
negative at
`0.9555961622099513236283020204477523519713...` (result SHA-256
`7e9f62fd5fa0040c2e9c184319f90e5278ec9f21912bd9198610bc7823544978`).
All 312 I faces and 1,200 J branch domains were traversed, and the independent
static result checker passes in normal and optimized modes.  This is a
Decimal100 discovery value, not a rigorous integral or an upper bound on the
degree-two D12 multiplier space.

The exact D4 degree-three stratum-moment construction and its independent
finite-space audit have now completed.  Its producer artifact (SHA
`c9cce84c...`) agrees entry-for-entry between the fused and unfused
implementations, reproduces the complete exact degree-two oracle, and passes
its time/RSS gates.  The frozen consumer (report SHA `4f92ffd4...`)
reconstructs the 160-by-160 matrices from canonical moment rows, proves exact
denominator rank 154 with precisely the six predeclared common zero rows, and
gives two discovery solves

```text
p=120: 0.9657718400877050661680622450967395128750070397885660...
p=200: 0.9657718400877050661680622450967395128750070397885660...
```

with relative disagreement `1.055e-114` and residuals below `3.3e-192` at the
higher precision.  Both are below one, so no vector was rationalized.  More
strongly, canonical obstruction SHA `ace35d91...` now certifies every one of
the 154 outward 768-bit LDL pivot lower endpoints of `M1-M2` as positive.  Its
exact midpoint residual is at most `2^-725`, while the perturbation base is at
least `2^-388`, a strict 337-bit separation.  A separately written stdlib
verifier (SHA `5df6955c...`) reconstructs `I`, `48J`, the six null rows, rank,
residuals, and all pivots in normal and optimized modes.  Audit report SHA
`824d78ee...` gives `AUDIT PASS`.  Thus every nonzero vector in this pinned
D4 degree-at-most-three quotient space is rigorously below one; no conclusion
about a richer D12 multiplier space is implied.

The v5 conditional importance-Ritz calibration also finished in both normal
and optimized modes.  Result SHAs `5a7a05f3...` and `f2080946...` were replayed
by separately frozen completed-output consumers; audit SHAs `db1b7b74...` and
`9c3169f6...` both return `IMPLEMENTATION_REJECTED` with the exact diagnostic
`active denominator matrix is numerically rank deficient`.  The repaired
normal/optimized comparator (SHA `16f13738...`, after a preserved `k=47`
false-accept regression) proves identical records core `1bc61ef8...` and
analysis core `70ade593...`; comparison artifact SHA is `fe6625bf...`.  No
Ritz matrix, quotient, or D12 continuation was produced by v5.

A read-only postmortem supplies a materially new reopening invariant.  Exact
rational LDL congruence followed by power-of-two scaling keeps all 93 active
coordinates and makes the exact transformed denominator diagonally
conditioned by less than four.  Under the unchanged `1e-12` rank threshold,
all 128 leave-one-chain reconstructions have ranks `16/47/93`; the worst
degree-two condition number is below 69, whereas the original failing deletion
had condition about `1.5e12`.  The first three direct-transform calibration
implementations have nevertheless failed hostile prelaunch review and were
never authorized: v6 omitted the stratum-specific J second-moment bound
(report SHA `2c2b3ec5...`), v6.1 inherited unit-scale tolerances that erase the
tiny stratum-15 raw and Jensen discrepancies (report SHA `3e86f5b7...`), and
v6.2 still permits a minimum-subnormal raw total to underflow after division
(report SHA `3105d232...`).  Each counterexample is frozen as a permanent
regression.  V6.3 then closed all three attacks but accepted positive
`2^-537` first moments with zero seconds because the one-ULP Jensen gap was
absorbed (report SHA `9b65083f...`).  V6.4 then allowed a nonzero weighted
first moment to square-underflow to zero (report SHA `aea310d5...`), and v6.5
allowed a finite near-maximum input to square-overflow to infinity, making
the comparison tolerance infinite (report SHA `6dc01442...`).  All five
counterexamples are permanent regressions.  Frozen v6.6 has now passed a
fresh independent hostile prelaunch audit (report/verifier/regression SHAs
`6ff06457...`/`4d3698a2...`/`36084f03...`).  Normal and optimized verifiers
return identical `AUDIT PASS`; both hostile and producer suites pass 8/8 in
both modes.  The scope is deliberately only the fail-closed arithmetic,
runtime binding, and record-validation package: no chain, sampled matrix, or
quotient exists yet.  A fresh D4 production calibration is queued as the next
light-memory sampling lane after the active exact D18 build releases its CPU
slot.

The selected seven-dimensional capped-gradient Ritz tier is conclusively
negative at
`0.9709744682406191224647138320022804861960...`; its exact serialized-form
denominator matrix has seven positive LDL pivots, and an independent solver
reproduces every entry and the root.  This retires that selected tier only, not
the full polynomial space.

A multiplier-independent stratum moment table now reproduces all 96-by-96 D4
quadratic `I` and `48J` entries exactly.  The first implementation takes
460.515 seconds; a fused structure-of-arrays implementation independently
reproduces the same oracle in 449.480 seconds.  A source-bound D12 face
benchmark has a frozen launch gate, but it is waiting for memory headroom and
does not authorize a full degree-three run by itself.

The exact C722 support port remains prepared but unlaunched: all 625 ordered
count pairs in each analytic branch pass.  Its reusable fixed-vector kernel
has a scoped formula audit, and a resume-safe scheduled driver now passes its
low-dimensional and D4 regressions.  A source-bound one-worker production gate
is still required before a possible 3.8-hour D12 transfer.  The scalar launch
is not authorized merely because transient free memory exceeds the old
threshold.

A distinct full-global-coefficient route is now frozen at the algebraic-design
stage in `CAPPED-D12-GLOBAL-RITZ-SAMPLER.md` (SHA `058b2b78...`).  It replaces
the inherited vector by an exact rational basis coordinate and samples the
bounded envelopes `sum_i G_i^2` and `sum_i m_i^2`, so it can estimate the full
272-dimensional capped pencil without dividing by the base polynomial at its
zeros.  No global sampler, matrix, or quotient exists yet; an exact D4 global
oracle and a two-hour/1-GiB cost gate are mandatory before a D12 screen.

A second general-support mechanism has exact finite-form calculations after
replacing the published outer caps that failed the mixed IIc test.  Use bands
`(-3/400,1/4)` and `(1/4,253/1000)`, inner cap `103/400`, and outer schedule

```text
(43/500,43/500,57/500,71/500,71/500,71/500).
```

The former v4 source-level checker and its replacement v5 are both withdrawn
as analytic PASS claims.  V5 repaired the omitted near-square cases, but a
fresh hostile audit found an interior outer/outer above-square point at
`omega=3/1000`, `gamma=4536000001/10^10` where the lower endpoint supplied
to Partition Lemma 2 is
`-4285714453/5000000000000<0`.  This violates the lemma's explicit
`(0,1/2)` premise.  Failure report/verifier/artifact SHAs are
`971f328f...`/`801c7f85...`/`848c190a...`.  The prospective replacement
`d=delta+h/4` fixes the exhibited endpoint but has not yet undergone a full
v6 regeneration and independent audit.

The first exact finite blocks on this support are negative.  Adjoining all
even orbit polynomials through degrees 4, 6, and 8 on the outer-band `R=0`
shell to the certified BV D16 vector gives exact particular-vector quotients
`0.9812865300598505...`, `0.9812875379474277...`, and
`0.9812888865905127...`.  The D8 gain over the radial BV benchmark is only
`0.0000029969809572...`, missing its predeclared `0.005` continuation gate by
about 1,668.  These exact matrices are producer results pending an independent
cache-free reconstruction, and they do not bound the full outer schedule.

The separate full-outer constant coordinate has also completed exactly.  Its
two-dimensional optimized quotient is
`0.981286468456766056460947337041221578...`, a gain only
`5.788472105153e-7` over the radial BV vector and about `6.1603e-8` below the
independently checked `R=0` D4 correction.  Artifact SHA `4a4d94f2...` and
independent contraction/by-count checker SHA `0d661870...` pass normally and
under `-O`.  This retires the constant full-shell direction, not the full
outer-band correction space.

A wider, incompatible hybrid family has now passed standalone exact producer
geometry checks.  It uses

```text
delta=361/50000, epsilon=3/400,
A=(-3/400,1/4,3121/12000),
inner B_m=103/400.
```

The inner band is exactly the full support of the certified BV D16 vector and
the outer shell has width `121/12000`.  Two incomparable outer schedules are
retained.  The high-plateau schedule
`B_m=min(11/200+(m-1)delta,43/250)` has active counts `0..23`; its 147,200
outer dynamic cells have least exact prefix margin
`2449991/60000000000`.  The volume-ramp schedule
`B_m=min(49/625+(m-1)delta,1599/10000)` has active counts `0..22`; all 3,308
ordered mixed fixed branch checks per orientation, 2,112 outer fixed checks,
and 135,168 outer dynamic cells pass, with least displayed margins
`3049959149/45000000000000`, `24199986563/15000000000000`, and
`629999/8000000000`.  The added outer-near `omega=0` IIa/IIb/III cover has
least margins `75949999/2500000000` (volume ramp) and
`15449999/2500000000` (high plateau).  Its exact producer-side constant shell mass is about
`6.5006809721e-90`, 17.52 times the independently reconstructed high-plateau
mass.  Repaired generic script SHA is `ffe1904e...`; volume/high-plateau
artifact SHAs are `3517533f...`/`e71f5411...`, byte-identical in normal and
optimized runs.  The preceding `732495cd...` artifacts are superseded because
they lacked the explicit outer-near range and retained the nonuniform IIb C3.
Independent hostile audits now give **ANALYTIC AUDIT PASS** for both supports.
They reconstruct the disjoint band/range assignment, weighted prime minorant
with `c1=c2=0`, corrected uniform IIb capacity, fixed prefix cases, and every
dynamic cell without importing the producer.  High-plateau report/verifier/
artifact SHAs are `2948b4c0...`/`b0a972af...`/`5f43cbf3...`; volume-ramp
SHAs are `f6c3eb4d...`/`f6882dd2...`/`88b6e1ae...`.  Normal and optimized
audit outputs are byte-identical.  The analytic route is therefore complete
for either wide support; no quotient on either support exists yet.

There is now a strong exact search signal for this wide route.  Dilating the
certified BV D16 polynomial by
`F_1(t)=F_0((3090/3211)t)` preserves the 307-dimensional graded-even basis.
At the matching rescaled cutoff, exact change of variables reproduces
`I_1=c^-48 I_0` and `(48J)_1=c^-49(48J)_0` and gives quotient
`1.0197035633110845...`.  At the actual wide cutoff `3031/12000`, direct
exact orbit integration gives `1.0207823750831113...`.  Script/artifact SHAs
are `3219047b...`/`27a893e9...`.  These are uncapped full-simplex particular
forms, not a Proposition-1 certificate and not a bound on the capped optimum;
their role is to justify the pending exact contraction of this explicit
polynomial on the analytically audited volume-ramp support.

Definition 5 does not, however, use the outer cutoff for the inner/inner
block.  Reconstructing the correct uncapped two-band pencil with cutoff
`97/400` for inner/inner and `3031/12000` for mixed and outer blocks gives
exact unit-amplitude quotient `0.99986151078506524...`.  Exact rationalization
of its stationary outer amplitude
`1.0263209135536035058233619047794...` improves this to
`0.99987975146175168...`, with exact negative margin and shortfall about
`1.2024854e-4`.  Script/artifact SHAs are
`85c4847c...`/`9a75380b...`.  This corrects any target-like interpretation of
the one-band `1.02078...` value: it remains an exact looser search signal,
whereas the capped Definition-5 contraction is the decisive pending form.

The strongest exact `k=48` rational-vector quotient currently reconstructed on
the narrow two-band finite forms is the D8 `R=0` shell result

```
0.981288886590512757488713567968224188...
```

Its exact shortfall is
`0.018711113409487242511286432031775812...`, so this is not a
bounded-gaps certificate.  Artifact SHA `79dc2c11...` contains the exact
41-by-41 matrix and exact rational particular-vector contraction.  Analytic
v5 failed its independent hostile audit, so this exact quotient has no
current Proposition-1 implication.  The strongest result carrying an
independent end-to-end analytic audit remains the two-piece radial correction
of the degree-16 direct Bombieri--Vinogradov polynomial.  It uses amplitudes
`1` on `sum(t)<=97/400` and
`0.98700279610351133526471897542473812763044719082939` on the outer
shell.  The exact shortfall is
`0.0187141103904444588737074464348991693...`, so this is not a
bounded-gaps certificate.  Exact inner/outer denominator and marginal forms,
the unchanged baseline marginal, and the all-ones recombination are checked
in artifact SHA-256
`33fe5d555e736fe5ea3826d569477414fadd2d8a9defc2eaa35718a4f06f82ca`.

The underlying polynomial is the 307-dimensional even-orbit degree-16 vector
on the direct Bombieri--Vinogradov support
`A=1/4`, support epsilon `3/400`, hence
`alpha=103/400`, `eta=97/400`, with every `B_m=103/400`.  It uses the
baseline quotient `0.981278109819760620341348914562469789...`.  That stored
rational vector has an exactly negative target margin, and its shortfall from 1 is
`0.0187218901802393796586510854375302109...`; this is not a bounded-gaps
certificate.  Its exact matrix hash is
`989b60a96521fcc92e4dfc2b463b907072c22a9bd19c111bd89aa0e2238c1220`.
A read-only fail-closed checker verifies the source, basis, cache completeness,
matrix hash, vector, and exact quadratic forms in normal and optimized modes.
For comparison, the complete 272-label no-ones basis through degree 12 has
also been rebuilt under the current source.  Its exact rational-vector value
is `0.96817894300169423596856336389768355...`, so odd signatures improve the
same-degree even basis but do not overtake even D16.  A minimal D16-plus-odd-P3
residual screen gives only `~9.3e-16` per added direction.  Exact deletion of
the numerator-invisible dead core removes only
`2.4209735209838010e-8` of `I`; a fixed-vector epsilon scan peaks at
`epsilon=19/2500` with quotient `0.9812847277203191...`; and forty
outer-shell even directions through degree 8 give a complete 41-dimensional
exact rational-vector quotient `0.9812804927852196...`, a gain of only
`0.0000023829654590...`.  These are negative particular-vector or screening results,
not upper bounds on richer finite spaces.  Independent scripts in `verify/`
reconstruct the dead-core and radial forms and pass four exact tests in normal
and optimized modes.

The hostile audit also passed a specialized direct Heath--Brown decomposition
for the paper's support and the exact `B_m=889/5000` enlargement.  A stronger
rational frontier has since passed two exact support checkers.  At C16,
`(A,epsilon,delta)=(77147/300000,1/200,2/125)` with
`(B_1,B_2,B_{m>=3})=(3/20,769/5000,849/5000)`, the exact degree-4 quotient is
`0.8920052899993396`.  At C10,
`(A,epsilon,delta)=(77747/300000,1/200,1/100)` with
`(B_1,B_2,B_{m>=3})=(3/20,3/20,97/625)`, a 55-digit recurrence gives the
discovery value `0.8963676783427826`.  Interpreting its recorded finite-decimal
vector as exact rationals and reconstructing the capped forms gives the same
displayed quotient exactly for that particular vector, with negative margin;
it is not a target certificate.

At the published C10 values `(A,epsilon,delta)=(253/1000,3/400,7/250)`, an
exact support frontier raises `B_1=B_2` to `159999999/10^9` and every later
cap to `889/5000`.  Exact geometry and direct-Heath--Brown checkers cover all
27 active unordered self-pairs; the critical strict margin is
`C1-2B1=5521/(5*10^12)`.  A fresh current-source D4 matrix and a cache-free
grouped contraction give the exact particular-vector quotient
`0.871199930807925510967654679560...`, versus
`0.871199930548528066751704376649...` for the prior `B_1=B_2=3/20`
schedule.  The gain is only `2.593974442159...e-10`, so cap motion of this
size is not being pursued as a blind high-degree campaign.

Keeping the same C10 `A,delta,B` data but reducing the support epsilon to
`7/2000` gives an independently reconstructed degree-4 rational-vector
quotient

```text
0.896837259628928073309820817264039399...
```

Its exact shortfall is `0.103162740371071926690179182735960601...`, while
the exact gain over the `epsilon=1/200` degree-4 vector is only
`0.000469581286145444498206554633419052...`.  Pair-matrix and grouped exact
contractions agree bit-for-bit, all Definition-1 margins pass, and the checker
passes in normal and optimized modes.  This retires epsilon motion as a
standalone low-degree lever; it supplies no degree-12 sign or finite-space
upper bound.

For scale only, the analytically infeasible full-simplex relaxation of C10 has
an exact rational-vector degree-12 quotient
`1.0030189929241073`, with exact matrix hash
`b882098bd6889ff251195b45153a2204e4df1c4ef843a2ae85dcc1b2fd3e041d`.
This is a genuine exact quadratic crossing for the relaxed support, but it is
not a sieve certificate because its `B_m=alpha` caps do not have the required
equidistribution proof.  The corresponding fixed rational polynomial has now
been evaluated on the actual C10 caps at 100 decimal digits.  The result is

```
0.9709698476337895741123900041395560037415645658885284
```

with heuristic shortfall
`0.0290301523662104258876099958604439962584354341114716`.
This is a non-rigorous multiprecision discovery result, but the negative gap is
far too large to justify an expensive exact rerun of the same vector.  The
fixed-vector transfer route is retired.  Active work is re-optimizing directly
on the capped support in the exact 20-function D4-plus-degree-band space, with
the C662 support frontier and richer capped bases retained as alternatives.
The negative-run artifact is
`agents/exact-integrator/results/c10_capped_fullD12_vector_grouped_mp100.json`
(SHA-256
`02e1a6676a68380592fd272845f7714d583574bd74f73b9a96727171751281d9`).

The first capped reoptimization line in the exact 20-function
D4-plus-degree-band space has also completed.  A fresh Decimal100 traversal of
the independently audited near-20 endpoint gives

```text
48J/I = 0.9668265520464799881755466130613854373448... < 1.
```

The frozen scalar-result auditor passes on output SHA-256
`feb5e858a7e74a17ca9a60c79b21f079571ac9a4fabb7e3c0001ebb2efffc03f`
and I-stage SHA-256
`db9caca00ecd24ab36bdfcaeb5839af69d0a668d3c546e62af498052a983c5bb`.
Exact rational polarization relative to the serialized Decimal100 base
action and endpoint forms gives the line maximum

```text
0.9719315175173559790681685240042962772477...,
```

at line parameter `0.04381087220633408248824...`, a heuristic gain
`0.00096166988356640495578...` over the base but still short of one by
`0.02806848248264402093183...`.  The endpoint itself misses the independently
derived crossing threshold `0.97847852790172937299688...` by
`0.01165197585524938482134...`.  The quadratic artifact SHA-256 is
`bf227a7f76bc6e54194b2e225291efde917a951b9b0958871e44a651fecfedb1`.
An independent raw-direction reconstruction (SHA-256
`6046a35ccdee0e10f7e81303e984024deab0fd1b4fe23c9a39c3b02eebfc1464`)
gives the same finite maximum to 61 decimal places.  Its apparently different
value at ``infinity`` is a coordinate-chart effect: the two affine parameters
are related by an exact Möbius transformation and send different projective
points to infinity.  The exact serialized-data reconciliation, including the
`3.84383e-62` stationary-value difference caused by the MP100 Euler residual,
is checked by `agents/structural-basis/code/reconcile_near20_charts.py`.
These are reproducible discovery forms, not exact capped integrals.  This
particular line is retired; it is not an upper bound on the full 20-function
space.

The next sparse contingency evaluates only the `H6` coordinate selected by the
stored capped action.  `H6` expands to 11 labels, so its self-form traversal
uses the complete 11-label square and marginal closure rather than the
272-label base polynomial.  The run completed in 64.507 seconds and gives the
Decimal100 self quotient

```text
0.3971939385982346476993650859241703076370... .
```

Combining those two self-forms with the stored cross forms yields the
two-dimensional discovery maximum
`0.9709699403308764355082616430885453266122...`, a gain of only
`9.2697086861e-8` over the base and a shortfall of about `0.02903005967`.
The raw self-form output SHA-256 is
`0ee7813d37284e3fc5a18193610685958cfa9e2934ad2b1fbceaecf9610e5f3f`.
The first consumer correctly stopped before writing because it demanded exact
Fraction identities between separately rounded Decimal100 `J`, `48J`, and
quotient strings; those identities differ by about one last Decimal unit.
Repaired consumer SHA-256
`f2462e9688bf0f426856ff81f7354476a762e1617c1fd8c81b7b67a17098b797`
reproduces the evaluator's operation order exactly in a 100-digit Decimal
context; a one-final-unit mutation is rejected.  Its 4/4 tests pass in normal
and optimized modes, and its frozen line artifact SHA-256 is
`58e700ae18dd2dd799b05fa9d305c025986d1fe9158bc1b224cf4a9e5ec11087`.
The line is decisively negative and is not an upper bound on the remaining
band coordinates.

Two independent fallback mechanisms are now exact at the low-degree or
analytic level.  Multiplying a fixed degree-4 polynomial by a rational
amplitude depending on the number of coordinates above `delta` raises its
exact quotient from `0.8963160512159082...` to
`0.9002830597452611...`, an exact gain of `0.0039670085293529...`;
block, direct branch-scaled, and pairwise reconstructions agree.  This does not
determine the degree-12 gain.  The corresponding 272-term D12 traversal has
now completed after 7,426.042 seconds.  Its all-ones blocks reproduce the
known Decimal100 capped baseline, and a deterministic 16-by-16 Decimal120
solve gives `0.9759647938310049211572412673...`, heuristic gain
`0.0049949461972153...` and shortfall `0.0240352061689951...`.  Block SHA is
`7bc4f1a2...`; deterministic solve script/result SHAs are
`7b700f47...`/`2c743ef4...`.  Because the integrated blocks are Decimal100,
this remains heuristic.  It is already below the stronger exact BV result,
so no fresh exact reconstruction of this negative candidate is launched.

A substantially stronger exact correction lets the multiplier be polynomial
in the total large- and small-coordinate masses `L` and `Z` separately on each
stratum.  On the capped-optimal C10 D4 polynomial, the 48-coordinate affine
space `1_R F0 span{1,L,Z}` (47 after exact removal of the null `(R=0,L)`
direction) contains a rational vector with

```
48J/I = 0.9348269207174672858115632780638459199717
```

and exact shortfall `0.0651730792825327141884...`.  This gains
`0.038459242374684657...` over the same unmodified polynomial.  Exact block
forms and a fresh multiplier-inserted traversal agree bit-for-bit over all 312
`I` faces and 1,200 `J` domains; root reran all five normal and optimized unit
tests.

The completed total-degree-two multiplier space
`1_R F0 span{1,L,Z,L^2,LZ,Z^2}` has 96 nominal coordinates and 93 after exact
removal of the three dependent `R=0` directions.  Its rational vector gives

```text
48J/I = 0.9539674388485507785778746586710282622062
```

with exact shortfall `0.0460325611514492214221253413290...` and exact gain
`0.0191405181310834927663113806072...` over the affine correction.  Decimal
100/160 discovery agrees and the exact block and fresh traversals coincide
bit-for-bit over 31,980 channel integrals.  Root reran all three tests in
normal and optimized modes.  This remains a negative finite-basis result, but
the observed correction is large enough that its pruned analogue on the D12
core is now the primary closing experiment.

An explicit nonconstant C10 cap schedule equals the old schedule for `m<=3`,
is strictly larger for `4<=m<=17`, and has first empty count 18.  The corrected
minimal-prefix proof checks every count pair with the literal inward-shrunk
capacities from the audited distribution argument.  Its least IIc margin is
exactly `499995341/15000000000000`, and its least maximal-omega Type-III
margin is `899021332939/5600000000000`.  This is an analytically valid support
enlargement, not a monotonicity theorem for the quotient.  Its exact
12-dimensional degree-4 optimum is
`0.8986948736808947779503198417994740524393`; independent pairwise and grouped
matching-vector reconstructions agree exactly.  Reoptimization gains only
`0.00000089594546042` over the transferred degree-4 vector, so this schedule is
a weak low-degree lever.

A corrected scan of the small-`delta` direct-HB frontier found that earlier
short bounds lists had understated this route.  A source-rebuilt exact audit
now passes at the refined C722 point
`delta=361/50000`, `A=3121/12000`.  With support epsilon `1/250`, an exact
count-dependent cap schedule has feasible counts 0--24, first-empty margin
`1/100000`, and checks all 625 ordered count pairs in each of seven repaired
branches.  Its least global inward reserve is `3/350000000000`; its worst
prefix margin is `56499669613/285000000000000`.  Normal and optimized
fail-closed audit runs pass.

The former scheduled L/Z proxies have now been replaced through degree 4 by
exact Fraction matrices and rational-vector contractions.  The attained
quotients in the `1_R L^a Z^b`, `a+b<=D`, spaces are

```text
D=2 (150 labels): 0.89660694768491289...
D=3 (250 labels): 0.919288303984479267146145223927...
D=4 (375 labels): 0.929761624569573128254855163296...
```

The D4 exact shortfall is
`0.0702383754304268717451448367036...`.  For each stored rational vector the
cache-free checker rebuilds every matrix entry, matches an independent
sum-first/square-second contraction bit-for-bit, and verifies the exact
positive `I-48J` margin.  In particular, the completed D4 reconstruction does
not trust its 375-by-375 serialized matrix.  These are rigorous achieved lower
bounds for their finite-space optima, not rigorous upper bounds; the pure L/Z
ladder is therefore narrowed, not mathematically excluded.  A robust
cross-precision exact-matrix discovery on constant C70 also supplies an
exact-checked global no-ones D4 vector at
`0.80379100835794699...`.  It is not a certified upper bound for that finite
space, but together with the poor transferred vector it shows why this
geometry must be tested with a stratum-adapted or mixed basis.

The general-minorant route has one new exact geometric clarification but no
analytic closure.  At the rational point
`A=521/2000`, support epsilon `37/10000`, `delta=7/1250`, constant
`B_m=21/2500`, and `c2=24`, an exactly-one-large-coordinate symmetric core
has `K=0` pointwise while its J fiber genuinely extends beyond C10.  Thus
support enlargement does not by itself force a positive K penalty.  The
singleton quotient is nevertheless only `.266...<133/500`, and the route
remains theorem-blocked by the high-gamma Type-I Siegel--Walfisz gap and the
unrepaired signed `c2>0` Proposition-1 implication.  This is an exact
geometric counterexample/diagnostic, not a sieve result.

The active high-degree computation is the sparse 20-channel capped gradient at
100 decimal digits.  Its operator has passed exact dense/sparse, pairwise,
Euler, serial/fork, parameter, count, and dependency-hash gates.  No quotient
from that run exists until its complete artifact is emitted.

A transferred-affine D12 scalar probe has now completed.  It applies the
already exact C10-D4 `1/L/Z` multiplier (with `L,Z` zeroed above count 11) to
the exact integer-scaled 272-term D12 polynomial and recomputes the capped J
integral at Decimal100.  All 695 marginal components, 1,200 J domains, and
serialized consistency gates pass, but the result is negative:

```text
48J/I = 0.9671692127936067321469619048809532704997...
48J-I = -3.08767153188892494880953499203069744...e310.
```

The output SHA-256 is
`e83d3610b8130d743757a5f01aacc6ff2d2b2acd3128e5ff21b9a01cfa53d8da`.
An independent fail-closed output audit re-contracts the pinned I stage and
reproduces its denominator, numerator, quotient, and margin.  The run remains
explicitly discovery-only because its migrated I-stage provenance predates
one transitive hash gate; in any event its margin has the wrong sign.  The
transferred-affine candidate is therefore retired, without claiming an upper
bound for the optimized D12 affine space.

The proof-to-checker identity for that candidate has independently passed a
static audit. All 272 ordered base coefficients, all 16 cutoff-adjusted
affine triples, the support, R/L/Z conventions, and both I/J multiplier
insertions agree exactly; the report SHA-256 is
`839d7dfbf5568c35fa6f83d6ec35b788da69e9b45071219821b998e60e4c53ef`.
It is a candidate-identity audit only; the separate completed evaluation above
supplies the negative discovery sign.

The stronger, already audited total-degree-two multiplier transfer is now
running end to end at Decimal100.  It uses
`1_R F0 span{1,L,Z,L^2,LZ,Z^2}`, pins the exact D4 multiplier at SHA-256
`fbc8c38d2cf4241fdba03beb4251e2692e96af01ad4918c9a3a1075af2ed6e86`,
and will remain discovery-only until any positive candidate is rebuilt by an
independent exact or outward-rounded checker.

A separate proof-wide source rereading now has verdict **AUDIT PASS EXCEPT
CERT** at report SHA-256
`a5928d97ea7e0fc53ae7fc7807d47d783b0b0e323d2bdbab24696ffe40303ac5`.
It retraces all four Proposition-1 hypotheses for the weighted/truncated
minorant, the repaired distribution chain, boundary/subsequence and liminf
logic, and the tuple.  It excludes exactly `[CERT-C10-48]` and therefore is
not a theorem verdict.

Two rigorous reconstruction backends are now prepared without assuming that
sign.  The independent cache-free exact affine core (SHA `9c21d73a...`) agrees
with a literal ordered-branch oracle on signed low-dimensional cases.  The
integer-directed dyadic ring/grouped backend (SHAs `f6f1730f...` and
`1dae2001...`) has a scoped hostile audit pass after six concrete defects were
found, repaired, and converted to regressions.  The integer-scaled exact D4 I
cost calibration finished in 22.77 seconds at 42,556 KiB and matched the
separate exact matrix contraction after the declared square scaling.  Its J
phase then finished in 1,294.77 seconds at 65,928 KiB and reconstructed
cutoff-10 quotient
`0.934812656645828990698336238450542021055045412...` exactly; scaled I and
`48J` again match the independent matrix contraction bit-for-bit.  The output
SHA-256 is
`25bda4a816c2752fa70815302914eeab5cf8f939de26cc8fa2fad949c8c30537`.
The 695-versus-19 marginal-component count alone gives a conservative
unbatched D12 projection near 20 serial days before higher-degree radial
costs, so that implementation remains a correctness oracle and will not be
the primary theorem run.  None of these implementation results supplies a
D12 sign.

An additional cache-free exact path is now prepared without changing the
frozen correctness core.  On each face it radializes the four ordered
small/large affine-product families in one batch and then reuses those exact
immutable transforms across the corresponding branch intersections; all 16
ordered branch slots and their domains remain separate.  Its SHA-256 is
`d824ab8ebb59da4cd94da7b17350c36ba5888bc2260fdeb8e976f4f825405ee8`.
Eight deterministic signed random `k=2,3` cases and the fixed signed oracle
case agree exactly in both face orders and both worker modes, under normal and
optimized Python.  A strict staged D12 exact driver (current SHA-256
`5514f63159ad74e54142cf1db2d88a9c69f552cad3d253cd50ca66452cf2784e`)
pins both the original rational vector and the 272-term integer input,
reconstructs their 714-bit least common denominator and all scaled
coefficients, pins the cutoff-11 affine source and every arithmetic
dependency, and consumes no matrices or persistent cache.  It has not been
launched and is not final-audit accepted.

The primary rigorous enclosure driver is also prepared, not launched.  It
uses the audited integer-directed dyadic backend to recompute the direct
affine-weighted I form, stage its outward endpoints under a byte SHA, and then
recompute all J branch domains.  Its only acceptance test is exact integer
comparison of `I.lo>0` and `(48J-I).lo>0`; it reads no matrix or persistent
moment cache.  Hostile audit found that its first version trusted rather than
reconstructed the integer input's source metadata.  The repaired driver pins
the original and scaled files, reconstructs all 272 coefficients, requires
primitive integer content and exactly 5,929 orbit products, and rereads both
files after each stage.  Its current SHA-256 is
`bf0ad4b3c1288c1d2df67e92f9ebe9e63613b9dcd2892c3f96522217d920677b`.
On a signed `k=3` fixture, both forward and reverse count orders enclose the
independent exact literal-oracle I and `kJ` in normal and optimized Python.
An independent six-test mutation/algebra suite now gives this driver a
**pre-launch scoped audit pass** (report SHA
`7315f5dcde8d171eb56aeaf129cefbe2f66f4bc88ab2ac755983c9055af3567a`).
It checks the exact 312/1,200 target traversal counts, the single factor 48,
reverse ordering, serialization, protected paths, and a straddling interval
that must fail.  The pass covers no D12 integration or sign; any positive
output still needs a second reconstruction and output-specific audit.

A second unlaunched interval driver (SHA-256
`7e2ed20a68e3c3e95a9566b32cae3d403949a79a3a81adfa61b8dab833b640b9`)
encloses the coefficients first and evaluates them through the separately
implemented tagged partition-radial algebra rather than the grouped Decimal
face/marginal code.  Its signed `k=3` adapter test encloses the literal exact
oracle under normal and optimized Python.  A seven-test hostile suite now
gives it a pre-launch scoped pass (report SHA
`5c42829e3d412a903f987057b67322ef389468894ab6f6c282eafb3eb0ea3a85`),
including intervals crossing zero, all 16 target active counts, provenance,
stage/sign gates, and the single factor 48.  This supplies a potential second
reconstruction path, not a target result.  A D4 cost calibration was stopped
without output when host swap increased; no target-sized run will start while
the two decisive production jobs overlap.

The independent ordered-branch checker has completed and persisted a
cache-free C10 degree-4 reconstruction.  Its exact `I`, `J`, `M2`, margin and
quotient match the producer bit-for-bit, it exits with the expected failure on
the negative margin, and all 43 tests pass in normal and optimized modes.  This
is a formal scoped plumbing audit, not a degree-12 sign claim.

The universal printed Proposition 3 route is not being treated as established:
the audit found a missing Siegel--Walfisz hypothesis in the high-`gamma` Type I
swap.  The specialized route bypasses that failed lemma.  See `AUDIT.md`.

Verified now:

```sh
python3 prime-gap-236/verify/check_tuple.py
python3 -m unittest prime-gap-236/verify/test_tuple.py
python3 -m unittest discover -s prime-gap-236/agents/exact-integrator/tests -v
python3 prime-gap-236/agents/hostile-analytic-audit/audit_exact.py
python3 prime-gap-236/agents/hostile-analytic-audit/direct_hb_exact.py
python3 prime-gap-236/verify/check_hb_support.py
python3 prime-gap-236/agents/hostile-analytic-audit/c10_audit_exact.py
python3 prime-gap-236/agents/structural-basis/code/verify_c10_nonconstant_schedule.py
python3 prime-gap-236/agents/small-delta-frontier/verify_c722_all.py
python3 prime-gap-236/agents/small-delta-frontier/verify_c722_lz.py
python3 prime-gap-236/agents/small-delta-frontier/verify_bv_vector.py \
  prime-gap-236/agents/small-delta-frontier/bv_aquarter_B16_vector_exact.json \
  prime-gap-236/agents/exact-integrator/results/aquarter_fullsimplex_k48_B16_current.json \
  --cache prime-gap-236/agents/exact-integrator/cache/bv_aquarter_sourcebound_v2.sqlite3
python3 -m unittest prime-gap-236/verify/test_exact_capped_certificate.py
```

The first command proves directly that the supplied 48-tuple has diameter 236
and is admissible.  No theorem `H_1<=236` follows until an exact quotient exceeds
1 and the corresponding full route receives final `AUDIT PASS`.
