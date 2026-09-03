# Certificate status

Checkpoint 2026-09-03 13:32 CEST: all thirteen exact base shards for
`A=I(H)` are complete and have an independent all-count radial audit.  The
strict full-direction aggregate SHA-256 is
`e00feb75871e9a4f9be34e9042283f0eda1aa16d139fe27dd2c5deb044865c44`.
For the current symmetric `R<=9` direction, the exact `A` contribution will
select counts `0..9` from those already-audited shards.

The exact `b=48J(F,H)` inventory is incomplete.  Fixed-polygon v8 shards
`r=8` and `r=9` are complete, immutable, and independently result-audited;
their SHA-256 hashes are
`ffbeb7f3cbc13c279a8c89b561d93af36fafed8d2442c90d22bb6c244e531631`
and
`e9397f72f78f9ad53716d61bb3f10854a640081f81632028904836d6c6778d88`.
Shard `r=7` has also published and passed an independent result audit; `r=6`
is running and `r=0..5` are missing.  For the `R<=9` direction, all
four branches are used for `r=0..8`, only the two
small-distinguished-coordinate branches are used for `r=9`, and higher
counts contribute zero.  The r8/r9 result audit is recorded in
`agents/audit/FIXED-POLYGON-V8-R08-R09-RESULT-AUDIT.md` (SHA-256
`00de4af6856e1b81425f875b829eabd526c35968ecb172ea3cd7804d63c69531`),
and the r7 audit report has SHA-256
`2383a1f46c2f4fc243736b5248fccdf5c3c99e6753ed32bdc042d7404549ca00`.

The Green-formula v9 implementation has a scoped source-level
**PRE-CERTIFICATE AUDIT PASS**, but no v9 target shard or certificate is
claimed.  Its frozen core/runner/checker SHA-256 hashes are
`019fecc00727bfdeb62fc3a02277298c6d08543db4d71ce47f049a73bc1d7a0c`,
`ad38951dadecdb5a5c51d1221b0a078bc9f804e9c4ec8d434706fca55a11935a`,
and
`7dbb352011d840a5bddf8f6f101f864d0a1b1e436ff4ebb5533ef1137217b4a7`;
the audit report SHA-256 is
`22eeabeba62a15dd0509e0b2b9215198e2056418dbc8f5a5c2b906d531ba34af`.
The repaired standalone `R<=9` replay driver also has only a scoped
pre-certificate audit: it has not completed an end-to-end target replay and
no compact certificate exists.

No positive `k=48` certificate exists yet, and no candidate has passed final
adversarial audit.  The current theorem-facing candidate consists of a
cache-free exact degree-19 inner vector plus one sorted-removal outer band,
but the required outer finite-projection inequality is still numerical only.

The assembled analytic proof has received a proof-wide **AUDIT PASS EXCEPT
CERT** (report SHA-256
`a5928d97ea7e0fc53ae7fc7807d47d783b0b0e323d2bdbab24696ffe40303ac5`).
That verdict deliberately excludes the two certificate inequalities
`I>0` and `48J-I>0`; it changes neither this file's negative status nor the
need for an output-specific independent audit.

The current best cache-free exact inner rational-vector evaluation is
`0.9867930836956087556586707101860344621... < 1`, with exact normalized
deficit `0.0132069163043912443413292898139655379...`.  Repaired checker/result
SHAs are `ff2046ce...`/`8b0d47b2...`; the checker rebuilds 13,955 square and
marginal-square orbit terms without reading a cache or serialized matrix and
strictly validates the mathematical wire types.  This is an
inner component, not a capped one-band quotient.  Two calibrated runs for the
explicit natural-D19 capped test polynomial estimate the finite-projection
energy `b^2/(A I(F))` as `.03680472098+/- .00054888164` and
`.03629520584+/- .00049266945`, far above the exact inner deficit.  Those
errors are empirical, however: neither run is an exact or outward-rounded
integral, so this remains discovery evidence and not a certificate.
The hardened inner checker has now received an independent `PASS` (report SHA
`6a4623ec...`).  For the outer exact stage, the selected 195-label D14 vector
has been rounded to common denominator `10^38`; its exact full-simplex
quotient differs from the unrounded rational vector by only `1.8761e-21`
(artifact SHA `72208259...`).  Neither discovery fact supplies the still-
missing complete exact `b=48J(F,H)` sum or its sign; the exact base `A`
reconstruction has since been completed and independently audited.

The exact reconstruction uses scaled integer coefficient vectors: `F` is
multiplied by `10^87`, `H` by `10^38`, so the comparison is against the inner
deficit multiplied by `10^174`.  The cross engine and its faster
common-denominator implementation have independent pre-certificate audit
reports with SHAs `ebcd39d0...` and `6d7326c6...`.  For `A`, the paired
engine's count-6 value first matched a separate high/low calculation exactly
and verified `A_scaled=10^76 A_unscaled`; the subsequent run completed and
independently audited all thirteen base counts and their full-direction sum.
For `b`, only fixed-polygon v8 `r=7,8,9` have passed an output-specific
independent audit at this checkpoint.  These facts do not replace the missing
complete mixed-form sum, aggregate inequality, compact certificate, or final
output-specific audit.

The previous best complete exact rational-vector evaluation on an
analytically justified support is
`0.9812858896095555411262925535651008306690... < 1`.  It is the
two-amplitude radial correction of the 307-label direct-BV degree-16
polynomial: the amplitude is `1` on `sum(t)<=97/400` and
`0.98700279610351133526471897542473812763044719082939` on the outer
shell.  Its exact shortfall is
`0.0187141103904444588737074464348991693310...`.  The exact piecewise
artifact is
`agents/small-delta-frontier/bv_D16_radial_two_amplitudes_exact.json`
(SHA-256
`33fe5d555e736fe5ea3826d569477414fadd2d8a9defc2eaa35718a4f06f82ca`).
It is retained as a negative regression target, not as a proof certificate.
Its particular quadratic margin is exactly negative; no
positive-definiteness or matrix-invertibility claim is being substituted for
the required inequality.

The underlying direct-BV D16 vector has exact quotient
`0.9812781098197606203413489145624697891350...`, exact matrix SHA-256
`989b60a96521fcc92e4dfc2b463b907072c22a9bd19c111bd89aa0e2238c1220`,
and compact vector SHA-256
`59715ddffa483c696c035634a81c3cc8ffe882e9d6eaceec74bea23996b72d62`.
A read-only fail-closed checker reconstructs its matrices and exact forms in
normal and optimized modes.  Independent exact/Decimal scripts under
`verify/` separately reconstruct the radial correction and the much smaller
dead-core correction, with four exact low-dimensional tests passing in both
modes.

The C10 full-simplex relaxation crossed 1 exactly at degree 12:
`1.0030189929241073`, matrix hash
`b882098bd6889ff251195b45153a2204e4df1c4ef843a2ae85dcc1b2fd3e041d`.
It is explicitly excluded from certificate status.  On the analytically valid
C10 caps, the same stored rational polynomial has multiprecision quotient
`0.9709698476337895741...<1`; this negative discovery result is not worth an
exact rerun and cannot be a certificate.  The 20-function degree-band
representation has independently passed an exact coefficient-by-coefficient
containment check.  Its first audited capped line is negative: the fresh
near-20 endpoint has Decimal100 quotient
`0.9668265520464799881755466130613854373448...` (output SHA-256
`feb5e858a7e74a17ca9a60c79b21f079571ac9a4fabb7e3c0001ebb2efffc03f`),
and exact rational polarization relative to the serialized discovery forms
has maximum `0.9719315175173559790681685240042962772477...`, shortfall
`0.02806848248264402093183...` (quadratic artifact SHA-256
`bf227a7f76bc6e54194b2e225291efde917a951b9b0958871e44a651fecfedb1`).
An independent raw-coordinate reconstruction is bound by SHA-256
`6046a35ccdee0e10f7e81303e984024deab0fd1b4fe23c9a39c3b02eebfc1464`;
the two finite maxima differ by only `3.84383e-62`.  The exact affine-chart
reconciliation is executable at
`agents/structural-basis/code/reconcile_near20_charts.py` and explains why
their coordinate-dependent points called infinity have different values.
This retires only that line, not the full degree-band space, and supplies no
certificate because the underlying capped forms are multiprecision discovery
values rather than exact or outward-rounded integrals.

A sparse 11-label evaluation of the next selected coordinate `H6` is also
negative.  Its raw Decimal100 self quotient is
`0.3971939385982346476993650859241703076370...` (SHA-256
`0ee7813d37284e3fc5a18193610685958cfa9e2934ad2b1fbceaecf9610e5f3f`),
and the resulting two-dimensional line maximum is
`0.9709699403308764355082616430885453266122...`.  The first postprocessor
failed closed before output because it incorrectly required exact Fraction
equality across independently rounded Decimal100 fields.  Repaired consumer
SHA-256
`f2462e9688bf0f426856ff81f7354476a762e1617c1fd8c81b7b67a17098b797`
now reproduces the evaluator's precision-100 Decimal operations exactly and
rejects a one-final-unit mutation; frozen output SHA-256 is
`58e700ae18dd2dd799b05fa9d305c025986d1fe9158bc1b224cf4a9e5ec11087`.
This remains a negative discovery result, not a certificate.

The first high-degree stratum correction has now been evaluated and is
negative.  It is the same pinned 272-term integer-scaled polynomial multiplied
on each stratum $R=\#\{i:t_i>\delta\}$ by

```text
a_R + b_R L + c_R Z,
L=sum_{t_i>delta} t_i,  Z=sum_{t_i<=delta} t_i,
```

using the exact rational vector in
`agents/exact-integrator/results/c10_stratum_linear_cappedopt_D4_exact.json`
and setting `b_R=c_R=0` for `R>11`.  The same construction at degree 4 has
the exact cutoff-10 quotient
`0.934812656645828990698336238450542021055045412...`, with independent
matrix contraction and cache-free traversal agreeing exactly.  At degree 12,
however, the completed Decimal100 traversal gives
`0.9671692127936067321469619048809532704997...<1`, with negative margin
`-3.0876715318889249488...e310`.  Its output SHA-256 is
`e83d3610b8130d743757a5f01aacc6ff2d2b2acd3128e5ff21b9a01cfa53d8da`;
an independent output auditor reproduces every serialized scalar and the
pinned I-stage contraction.  This is a negative discovery result, not an exact
certificate or an upper bound on the optimized affine space.

A separate static audit now verifies that this statement names exactly the
function consumed by both target loaders. It compares all 272 ordered base
coefficients and all 16 effective affine triples, including the eight raw
L/Z entries deliberately overwritten by cutoff 11, and derives the I/J
multiplier insertion on both implementations. Its report is
`agents/small-delta-frontier/AFFINE-CANDIDATE-IDENTITY-AUDIT.md` (SHA-256
`839d7dfbf5568c35fa6f83d6ec35b788da69e9b45071219821b998e60e4c53ef`).
This identity audit agrees with the completed negative evaluation; it is not
an exact integration or positive certificate.

The total-degree-two multiplier
`1_R F0 span{1,L,Z,L^2,LZ,Z^2}`, whose selected D4 rational vector has exact
quotient `0.953967438848550778577874658671...`, has now been transferred to
D12 and is negative.  The completed Decimal100 quotient is
`0.9555961622099513236283020204477523519713...`, with result SHA-256
`7e9f62fd5fa0040c2e9c184319f90e5278ec9f21912bd9198610bc7823544978`
and I-stage SHA-256
`8b5c1c1a499c74285a25ae12ae10dd2dca56acce3698d00e6e9558fdf7e79fc0`.
The static output checker passes in normal and optimized modes, but the
integration is not rigorous and the particular negative vector is not an
upper bound on the D12 multiplier space.  No dyadic certification was
launched.  The active successor is an exact D4 degree-three moment-table run;
any vector it discovers will still require a fresh D12 screen and exact or
outward-rounded reconstruction before certificate status can change.

Two cache-free rigorous reconstruction routes are being prepared.  The
grouped dyadic result driver recomputes direct `I` and all `J` branch domains.
Its hostile audit found that the first version trusted the integer-scaled
input's source metadata without reconstructing the scaling.  The repaired
version now pins both source files, recomputes the 714-bit LCM and every one
of the 272 scaled coefficients, checks primitive content and the 5,929 orbit
products, and rereads both inputs after each stage.  Its current SHA-256 is
`bf0ad4b3c1288c1d2df67e92f9ebe9e63613b9dcd2892c3f96522217d920677b`.
It has a scoped pre-launch audit pass at report SHA
`7315f5dcde8d171eb56aeaf129cefbe2f66f4bc88ab2ac755983c9055af3567a`.
That verdict covers parsing, algebra, traversal counts, serialization, and
the sign gate, but no target integration or target sign.

A second unlaunched driver,
`verify/check_c10_d12_affine_independent_dyadic.py`, routes dyadic coefficient
enclosures through the separately implemented tagged partition-radial
recurrence rather than the grouped Decimal face/marginal code.  A signed
`k=3` test encloses the literal exact oracle in normal and optimized modes.
Its seven-test hostile suite now gives a pre-launch scoped audit pass (report
SHA `5c42829e3d412a903f987057b67322ef389468894ab6f6c282eafb3eb0ea3a85`),
including uncertain coefficient intervals crossing zero.  This remains
certification infrastructure, not a target integration or positive
certificate.

The frozen independent tagged-residual checker (SHA-256
`1787e7b482a5c2982de56486bc774794f6e671b3db4d9ab7207ebb1c85dc079c`)
passes 43 low-dimensional, parser/adversarial, serial/fork, persistence, and
literal/expanded comparison tests in both normal and optimized Python.  Its
captured cache-free C10 degree-4 output has SHA-256
`2e7c072c87f143e5213db9eccb4a5f864cc9e46c79f978d4dd5f4a0c928a3763`.
All five exact fields `I,J,M2,M2-I,quotient` match the producer strings
bit-for-bit, and the checker fails closed with exit status 1 because the
margin is negative.  The scoped verdict is **C10 D4 INDEPENDENT REGRESSION
AUDIT PASS**.  It supplies no evidence for a degree-12 sign.

The tuple component is complete and independently executable:

```sh
python3 prime-gap-236/verify/check_tuple.py
```

It prints the size, diameter, and a missing residue witness for each prime
`q<=48`.  A future sieve certificate checker must reconstruct all moments from
the finite basis and rational parameters; it may not trust the SQLite discovery
cache or serialized matrix entries.
