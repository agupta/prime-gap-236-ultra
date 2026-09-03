# Adversarial audit

Status: **OPEN / NO FINAL CERTIFICATE PASS**.  No bounded-gap proof claim is
currently made.  There is, however, an independent
**SPECIALIZED ANALYTIC AUDIT PASS** for the direct Heath--Brown route at the
published support and at `B_m=889/5000` for `m>=3`; see
`agents/hostile-analytic-audit/direct-hb-prime-equidistribution.md`.
The actual C10 candidate has now received a separate verdict
**C10 ANALYTIC AUDIT PASS WITH REPAIRS**; see
`agents/hostile-analytic-audit/C10-AUDIT.md`.
The deep predecessor chain actually used by C10 has the further restricted
verdict **C10 DEEP-DISTRIBUTION AUDIT PASS WITH MANDATORY REPAIRS** in
`agents/structural-basis/C10-DEEP-DISTRIBUTION-AUDIT.md` (SHA-256
`f9ced080b78e4f4b82c804b957005b779816531e057cafa351f4e80a581b7cdd`).
This is not an endorsement of the paper's universal Baker--Irving branch.
The exact `c_1=c_2=0` specialization of Proposition 1 itself has verdict
**PROP1 c2=0 AUDIT PASS WITH REPAIRS**; see
`agents/structural-basis/PROP1-C2ZERO-AUDIT.md`.

At the current one-band target, all thirteen `A=I(H)` shards and their sum
have an independent hostile `PASS` (report SHA `ab227302...`, result SHA
`9c846bb1...`); the strict full-direction aggregate SHA-256 is
`e00feb75871e9a4f9be34e9042283f0eda1aa16d139fe27dd2c5deb044865c44`.
The current symmetric `R<=9` direction selects counts `0..9` from these
already-audited base shards.  The mixed-form target remains incomplete.

Fixed-polygon v8 `b=48J(F,H)` shards `r=8` and `r=9` have independent
result-level passes.  Their result SHA-256 hashes are
`ffbeb7f3cbc13c279a8c89b561d93af36fafed8d2442c90d22bb6c244e531631`
and
`e9397f72f78f9ad53716d61bb3f10854a640081f81632028904836d6c6778d88`;
the combined audit report SHA-256 is
`00de4af6856e1b81425f875b829eabd526c35968ecb172ea3cd7804d63c69531`.
Shard `r=7` has also passed its independent result audit (report SHA-256
`2383a1f46c2f4fc243736b5248fccdf5c3c99e6753ed32bdc042d7404549ca00`).
At the 2026-09-03 13:36 CEST checkpoint, v8 `r=6` is running and `r=0..5`
are missing.  For the `R<=9` direction, all four branches are required for
`r=0..8`, only the two small-distinguished-coordinate branches are retained
for `r=9`, and `r>=10` contributes zero.

The repaired standalone `R<=9` replay driver has a scoped source/control-flow
pre-certificate pass, including binding reconstruction to startup-audited
shard bytes.  It has not completed a target end-to-end replay and has issued
no compact certificate.  The Green-formula v9 implementation likewise has a
scoped source-level **PRE-CERTIFICATE AUDIT PASS**, pinned to core, runner,
and checker SHA-256 hashes
`019fecc00727bfdeb62fc3a02277298c6d08543db4d71ce47f049a73bc1d7a0c`,
`ad38951dadecdb5a5c51d1221b0a078bc9f804e9c4ec8d434706fca55a11935a`,
and
`7dbb352011d840a5bddf8f6f101f864d0a1b1e436ff4ebb5533ef1137217b4a7`;
its report SHA-256 is
`22eeabeba62a15dd0509e0b2b9215198e2056418dbc8f5a5c2b906d531ba34af`.
No v9 target result or certificate claim is included in that verdict.

The theorem-facing one-band cross calculation now has two additional scoped
verdicts, neither of which is yet a target-result pass.  The reference engine
has **PRE-CERTIFICATE AUDIT PASS** in
`agents/audit/SYMMETRIC-CUTOFF-CROSS-PRE-CERTIFICATE-AUDIT.md` (report/test
SHAs `ebcd39d0...`/`b4e17d1b...`): an independent named-monomial rational
polygon oracle checks every Definition-5 branch, both endpoint orientations,
the single factor 48, target dilation/scales, and orbit multiplicities in
normal and optimized Python.  The common-denominator/collected-affine fast
engine has a separate **PRE-CERTIFICATE AUDIT PASS** in
`agents/audit/FAST-TAGGED-SCALAR-V2-PRE-CERTIFICATE-AUDIT.md` (report/test
SHAs `6d7326c6...`/`4be6e1ee...`), including coefficientwise restoration of
both cleared denominators.  The final audit must still reconstruct every
remaining mixed-form shard required by the selected `R<=9` direction and the
exact positive scalar margin.

The paired exact `A=I(H)` shard engine likewise has a scoped
**PRE-CERTIFICATE AUDIT PASS** (report/test SHAs
`fe90ab3b...`/`6621aa41...`).  Its independent literal-polygon tests cover
all 64 low-dimensional basis pairs, random signed vectors and geometries,
top/zero counts, cap multiplicities, endpoint dependence, and invalid reuse
guards in both Python modes.  A separately written target radial checker
(SHA `105a0136...`) reconstructs the complete 508-orbit/3,034-residual-term
square without importing the producer.  That checker has since reconstructed
and matched all thirteen target base counts; the strict aggregate has the
hostile pass recorded above.

The completed active25 D16 v6 target has a final independent verdict
**INDEPENDENT ARITHMETIC RECONSTRUCTION AND EXACT FINITE-SPACE OBSTRUCTION
PASS**.  Normal and optimized Python both recomputed every shard, reproduced
the exact negative quotient `.9812858896095555411...`, and proved `I-48J`
positive definite with 27/27 exact LDL pivots.  Checker/test/result/report SHAs
are `2c08afe2...`/`8b6ee299...`/`c0a83cee...`/`dd3241ca...`; fresh-form,
pivot-list, and unit-lower hashes are `e22f3ccc...`, `fbfbe8c7...`, and
`03b181d5...`.  This rigorously obstructs only that 27-dimensional space and
does not imply a theorem or an omitted-space upper bound.

The new `delta=1/60` single-band and two-outer-band analytic supports currently
have discoverer exact passes only.  Their frozen checker/result SHAs are
`b8abaa8f...`/`b7070c26...` and `187a87f6...`/`c74da6b5...`, respectively.
The first of those supports now has a scoped hostile **AUDIT PASS**:
checker/result/report SHAs are `0a6b6dbc...`/`eabffdc8...`/`c17dab46...`,
and the normal/optimized results are byte-identical.  The audit independently
reconstructs 672 ordered fixed cases, 767 IIb crossings, and all 36,608
nonempty plus 256 empty IIc cells.  It also verifies the actual interface:
the specialized direct Heath--Brown route bypasses Propositions 2/3 and
directly supplies the weighted prime function to all four Proposition-1
hypotheses.  This pass does not automatically cover a changed cap schedule.
The stronger priority support retains only one sorted-removal outer band.  It
now has a scoped hostile **AUDIT PASS**: producer checker/result/test SHAs are
`fff28057...`/`c9be4426...`/`9b0e1409...`, and independent
checker/result/report SHAs are `b4e889ab...`/`fea750c7...`/`652f1b16...`.
The audit independently reconstructs every one of the 43,008 nonempty
Type-IIc cells (including 6,081 sorted-removal three-block actions), the cap
bands, the common `+/-10^-7` translation, and the direct Heath--Brown route to
all four Proposition-1 hypotheses.  It found a real generic-producer defect:
2,522 ordinary-prefix Type-IIb affine roots were omitted from the producer's
19,182 probes.  The independent complete 24,226-probe oracle nevertheless
proves that no omitted root changes a frozen minimum or gives a counterexample,
so the pass is valid for this exact tuple but the producer must be repaired
before being reused for another tuple.  The route bypasses Propositions 2/3;
it directly supplies the weighted prime function required by Proposition 1.

The exact-normalized D18 `h^2` bridge is statistical discovery only.  It
successfully exposes the earlier direct-iid cap estimates as high-degree
rare-event misses, but its reported standard errors are not rigorous interval
bounds.  On the priority sorted-removal one-band support, two calibrated runs
give `.01376755+/- .00012570` and `.01367847+/- .00010871`, versus the exact
D18 deficit `.0146491591498...`.  No audit may promote these estimates or
their naive combined shortfall `.00093258` to an exact sign.

A proposed multiband extrapolation of the one-band Riesz-shell lemma has been
stopped before production.  Definition 5 uses the cutoff
`s <= max(eta_i,eta_j)` for a pair of bands.  At a fixed leave-one-out sum
`eta_1 < s <= eta_2`, the two-band kernel is exactly
`[[0,1],[1,1]]`, whose determinant is `-1` and whose quadratic form takes the
negative value `-1` at `(1,-1)`.  Consequently `J(H)` is not positive
semidefinite merely "by definition" on a union of bands.  The inference
`sum_j b_j^2/A_j > deficit` is therefore unauthorized without either the
full outer `48J` block or a separate sign/support lemma.  The literal
single-outer-band Riesz reduction is unaffected: its self term is one
truncated marginal square.  The exact-stage design is being repaired to use
the per-band test `b_j^2/A_j > deficit` only.  An independent proof audit
`agents/analytic-new-lever/RIESZ-SHELL-LEMMA-INDEPENDENT-AUDIT.md` (SHA
`6dc822f2...`) now gives **AUDIT PASS** in precisely this single-band scope,
including the factor 48, Fubini identity, boundary/L2 details, finite
projection inequality, and an actual symmetric `k=2` multiband counterexample
with exact `J=-7/375`.

The complete canonical B19 inner vector has a cache-free direct replay.  The
v1 arithmetic and its normal/optimized result bytes are exact, but hostile
review found that its wire parser accepted JSON basis exponent `0.5` and
silently coerced it to `0` when the caller supplied the mutant hash.  Repaired
v2 checker/test/result SHAs are `ff2046ce...`/`5f03f8cd...`/`8b0d47b2...`.
V2 rejects noninteger basis fields, noncanonical rational strings, and
malformed hash strings before invoking the pinned v1 recurrence; normal and
optimized Python again reconstruct 13,955 square and 13,955 marginal-square
orbit terms and give identical bytes.  It proves the particular-vector
quotient `.9867930836956087557...` and exact normalized deficit
`.0132069163043912443...`.  Independent hostile review of final v2 now gives
`PASS` (report SHA `6a4623ec...`): both execution modes reproduce the strict
result byte-for-byte, an independent scan-free recurrence reproduces every
form, the complete basis and factor 48 are checked, and ten further malformed
records are rejected.  No outer certificate is included in that scoped pass.

Two calibrated finite-projection runs now use the natural dilated D19
polynomial restricted to the audited one-band cap.  They give
`b^2/(A I(F))=.03680472098+/- .00054888164` and
`.03629520584+/- .00049266945`, where `A=I(H)` and `b=48J(F,H)`, against the
exact inner threshold `.0132069163043912443...`.  Their source/tests/result
SHAs are `132992f8...`/`2150bd54...` and
`bdf356b7...`,`69fb8bb1...`; a separate frozen-run summary checker SHA
`79c85f65...` passes.  This is exceptionally strong discovery evidence, but
the errors are empirical and it is not a certificate.  The decisive remaining
arithmetic task is exact reconstruction of this projection, or of a cheaper
lower-degree rational test polynomial retaining the same sign.

That cost screen selected the exact 195-label D14 direction.  The
common-denominator `10^38` rationalization preserves its exact full-simplex
quotient to `1.8761e-21` and changes the capped Monte Carlo projection by only
`2.29e-15 +/- 1.78e-15` under common random numbers (fine-grid artifact SHA
`72208259...`, screen SHA `6c2349a1...`).  This is still discovery evidence;
the exact scheduled-stratum `A` and cutoff-preserving cross term `b` are now
being reconstructed independently.

The newest wide nonuniform schedule has a separate **ANALYTIC AUDIT PASS**.
Checker/artifact/report SHAs are `1c041d15...`/`700f7931...`/`dc17388c...`;
normal and optimized outputs are byte-identical.  The audit reconstructs all
fixed-prefix and 135,168 dynamic-IIc cells, proves the mixed-IIc range empty,
checks the weighted minorant with `c1=c2=0`, and certifies a simultaneous
ten-parameter strict-interior box.  Its scope excludes every quotient claim.

That plateau support is now strictly superseded by the independently audited
active-25 rising tail.  Its checker/artifact/report SHAs are
`c96b1d1c...`/`111a48a2...`/`0c89e776...`; root reproduced byte-identical
normal and optimized outputs.  All 172,800 dynamic cells and every fixed case
pass, count 26 is the first empty stratum, and a simultaneous 25-parameter
radius-`1/1000000` box remains strict.  This verdict is again analytic only:
no finite quotient is included.

A fresh proof-wide rereading of the assembled C10 argument has verdict
**AUDIT PASS EXCEPT CERT** in
`agents/small-delta-frontier/PROOF-COMPLETENESS-REAUDIT.md` (SHA-256
`a5928d97ea7e0fc53ae7fc7807d47d783b0b0e323d2bdbab24696ffe40303ac5`).
It is pinned to proof-draft SHA-256
`30532156254193456faa6f8d1c9e6ac53395d7a46d633410bb749a0557773c2f`
and independently retraces the weighted/truncated minorant, all four
Proposition-1 hypotheses, the repaired predecessor chain, boundary and
subsequence logic, the BFI correction-note scope, and the tuple.  Its sole
excluded mathematical assertion is `[CERT-C10-48]`, namely exact positivity
of `I` and `48J-I`; it is therefore not a final certificate pass.

The completed D12 quadratic-multiplier discovery output has a separate
static **DISCOVERY-OUTPUT AUDIT PASS (NOT RIGOROUS INTEGRATION)** in both
normal and optimized Python.  Result SHA-256 is
`7e9f62fd5fa0040c2e9c184319f90e5278ec9f21912bd9198610bc7823544978`
and I-stage SHA-256 is
`8b5c1c1a499c74285a25ae12ae10dd2dca56acce3698d00e6e9558fdf7e79fc0`.
The checker reopens all pinned inputs/dependencies and recomputes the
serialized Decimal100 denominator, numerator, quotient, margin, and all
count gates.  The quotient is negative at
`0.9555961622099513236283020204477523519713...`; this retires only that
particular transferred vector and supplies neither a theorem nor a
finite-space upper bound.

The importance-discovery infrastructure has a separate **SCOPED AUDIT PASS
AFTER REPAIRS** in
`agents/structural-basis/IMPORTANCE-DISCOVERY-AUDIT.md` (SHA-256
`ba7eae582b6fcaf1fe0f1e39c7abbe01b2e845d9e4eed5c7312acd2a4a3c0b27`).
Its 47 tests pass in both normal and optimized modes, which root independently
reran.  This audit explicitly blocks the original global-chain design because
an exact D4 stratum has mass `8.16e-18`, and it gives D4 and D12 sign changes
showing that direct `m_i/m_0` ratios lack a positivity safeguard.  The repaired
conditional-stratum identity with bounded envelope `g=sum_i m_i^2` passes
algebraically, including the D4-versus-D12 factor-48 schema distinction.  No
Markov chain, statistical matrix, or quotient was part of that pass; finite
MH batch ratios remain discovery-only.

The direct-transform importance-calibration successor has not yet earned a
prelaunch pass.  Three frozen versions were rejected before production:

- v6 failed to apply its exact stratum-specific `z^2` bound to serialized J
  records (`IMPORTANCE-D4-CALIBRATION-V6-PRELAUNCH-AUDIT.md`, SHA
  `2c2b3ec5887b982185624216d041ecf44531bb0da279271e05a1a77a11d06ff4`);
- v6.1 inherited unit-floor absolute tolerances and accepted a zero raw sum
  against positive `4.14e-21` batches and a zero second moment against a
  positive squared mean (report SHA `3e86f5b7...`);
- v6.2 used locally scaled tolerances but divided before checking survival, so
  a minimum-positive binary64 raw total averaged to zero and was accepted
  (report SHA `3105d232...`).

Each report has an independent normal/`-O` verifier and permanent regression.
No chain, D12 screen, Ritz matrix, or quotient was produced.  V6.3 was also
kept production-disabled after a fresh audit found a positive-first/zero-
second subnormal Jensen counterexample.  Its frozen report SHA is
`9b65083f...`, independent verifier SHA `6302c8f8...`, and permanent
regression SHA `0aa8fa5c...`.  V6.4 failed because a nonzero weighted first
moment could square-underflow to zero (report SHA `aea310d5...`; regression
SHA `3e387aca...`).  V6.5 failed because a finite near-maximum input made the
recomputed square and tolerance infinite, which the wrapper accepted (report
SHA `6dc01442...`; verifier SHA `5ca07de7...`; regression SHA `f400f250...`).
Frozen v6.6 now has a scoped independent **AUDIT PASS**.  Report SHA
`6ff06457...`, verifier SHA `4d3698a2...`, and hostile-regression SHA
`36084f03...` close every preserved v6--v6.5 attack, both signs at the
resolved-square underflow boundary, the finite-square overflow boundary,
cancellation residuals, local-ULP comparisons, nonfinite paths, provenance,
and runtime closure.  Normal/`-O` verifier outputs agree and both hostile and
producer suites pass 8/8 in each mode.  This is only a prelaunch package
audit: it contains no production chain, matrix, quotient, or certificate.

The revised narrow full-BV two-band support's v4 and v5 analytic PASS claims
are both **WITHDRAWN**.  V5 repaired v4's missing near-square coverage, but an
independent hostile audit found a smaller source-level failure in the
outer/outer above-square Type-IIb branch.  At the strictly interior point
`omega=3/1000`, `gamma=4536000001/10^10`, its frozen auxiliary width makes
the lower endpoint in Partition Lemma 2
`a2=-4285714453/5000000000000<0`, violating the lemma's stated requirement
`a2 in (0,1/2)`.  Report/verifier/artifact SHAs are
`971f328f...`/`801c7f85...`/`848c190a...`, with byte-identical normal/`-O`
failure output.  The preserved mixed IIb `(1,4)` case still shows only that
the all-first allocation fails; moving the smallest outer coordinate to bin
2 succeeds and leaves bin 3 empty.  A prospective width `d=delta+h/4`
repairs the exhibited endpoint and local theorem margins, but it is outside
v5 and requires a newly frozen v6 proof and hostile audit.  The D4/D6/D8 and
full-outer finite forms remain exact algebra but currently have no analytic
Proposition-1 implication.

A separate wide BV/C722 hybrid is currently only at **EXACT GEOMETRY PRODUCER
PASS**.  The repaired generic checker SHA `ffe1904e...` reconstructs two incomparable
outer schedules in byte-identical normal/`-O` runs.  High-plateau artifact SHA
`e71f5411...` has active counts `0..23` and 147,200 outer dynamic cells;
volume-ramp artifact SHA `3517533f...` has active counts `0..22`, 3,308 mixed
fixed branch checks per orientation, 2,112 outer fixed checks, and 135,168
outer dynamic cells.  An earlier exploratory loop incorrectly subdivided a
mixed gamma interval with its endpoints reversed; those claimed
193,280+193,280 mixed cells remain invalidated.  The correct mixed dynamic-
IIc interval is empty.  Hostile source audit found that the preceding
`732495cd...` checker used the paper's nonuniform IIb third capacity and did
not state the outer-near `omega=0` split.  The current producer replaces C3 by
the smaller uniform `delta+2*omega` and adds all 1,584/1,725 outer-near branch
checks.  Two separately frozen hostile reconstructions now return **ANALYTIC
AUDIT PASS**: high-plateau report/verifier/output SHAs
`2948b4c0...`/`b0a972af...`/`5f43cbf3...`, and volume-ramp SHAs
`f6c3eb4d...`/`f6882dd2...`/`88b6e1ae...`.  Both are byte-identical in normal
and optimized modes and pin the weighted minorant with `c1=c2=0`.  Neither
schedule yet has a finite quotient, so neither proves the theorem.

## Findings that currently block a theorem claim

1. **High-`gamma` Type I swap (universal route only).**  Lemma `typeIBI` in the 2026 TeX states Type I
   equidistribution for arbitrary `alpha` and smooth `beta`.  In the branch
   `1/2 <= gamma <= 1/2+2 omega+varepsilon`, its proof swaps the two factors and
   invokes `typeIIPoly`.  That lemma requires its second (now original `alpha`)
   factor to have the Siegel--Walfisz property.  No such hypothesis appears in
   `typeIBI` or Type I of Definition 4.  Baker--Irving's source version of the
   corresponding Type I lemma explicitly assumes it.  The 2023 Heath--Brown
   sequence class has a subset-convolution Siegel--Walfisz property, so a repair
   may exist for the sequences actually used, but it has not yet been proved
   through every Buchstab branch.  The specialized direct Heath--Brown proof
   bypasses this lemma by classifying its actual terms as Type 0, SW/SW Type II,
   or smooth Type III.

2. **Type III endpoint slack.**  Definition 4 permits smooth factors as large as
   `x^(xi3+epsilon)`.  Substituting `gamma=xi3` into the Type III estimate drops
   that slack.  A prospective repair replaces the auxiliary allowance by one
   with an additional `-2 epsilon`; its exact propagation through Proposition 3
   has been made with a reserved `h`-margin and passes the specialized audit.

3. **Literal Proposition 3 defects.**  Its Type IIc quantifier includes negative
   `omega0`, making a displayed bin capacity negative; the proof uses a different
   epsilon constant (`100` versus `52`); one-zero and two-zero `(m,m')` cases are
   omitted; and the Type I proof uses an extra partition condition absent from
   the statement.  A repaired baseline case split exists in
   `agents/source-fidelity/repaired-proposition3.md`, but it has not passed the
   current hostile audit.

4. **Section 5/source ambiguity.**  The introduction's degree condition
   `2a+b<=21` conflicts with the final `B_19` label, and the displayed `B_D` is a
   family schema rather than a finite linear basis.  The computation therefore
   uses the explicit Polymath even-monomial-orbit convention and records its
   finite basis verbatim.  This is an independent choice, not a claimed recovery
   of an unpublished coefficient vector.

5. **Malformed definitions.**  Definition 3 references undefined `B_{j,0}`;
   Definition 5's `K` contains an unbound `t'_k` and no corresponding
   differential.  The former has the evident empty-product/vacuous-condition
   completion.  The latter prevents use of the general `c2>0` route until an
   explicit repaired functional is justified.

## Checks already passed

### Transferred-affine candidate identity (static scope)

The proof-to-checker identity has a separate **AUDIT PASS** at
`agents/small-delta-frontier/AFFINE-CANDIDATE-IDENTITY-AUDIT.md`
(SHA-256
`839d7dfbf5568c35fa6f83d6ec35b788da69e9b45071219821b998e60e4c53ef`).
Its fail-closed checker (SHA-256
`a24dbe781c2311420a5c8fa2366ee5959f28ddcd3e62aa69f94976eb78b8a950`)
passes under normal and optimized Python. It compares all 272 ordered base
labels and coefficients, reconstructs the original-to-integer scaling,
compares all 16 effective affine triples after the explicit cutoff 11, and
checks the two independently implemented I/J multiplier formulas at `k=48`.
This verdict is identity-only: it computes no target integral or sign and
does not upgrade either target driver from pre-launch status.

- The tuple checker independently verifies 48 distinct integers, diameter 236,
  and an omitted residue class for every prime at most 48.
- Ten low-dimensional exact integration regression tests pass; an independent
  million-sample Monte Carlo calculation agrees with the exact constant-function
  moment within 0.4 estimated standard errors for `J`.
- Every reported "exact quotient" is evaluation of one displayed rational
  vector against forms reconstructed by the recurrence.  None on an
  analytically justified capped support is above 1.  The exact full-simplex
  D12 relaxation is above 1, but its enlarged support lacks the required
  equidistribution proof and is explicitly excluded from every theorem claim.
- `agents/hostile-analytic-audit/audit_exact.py` and
  `direct_hb_exact.py` independently verify the specialized analytic
  inequalities and the four Proposition 1 hypotheses for the two audited
  supports.  This is an analytic-component pass, not a final theorem pass.
- `verify/check_hb_support.py` exhausts all 81 nonempty count pairs and 2,520
  empty-side cases at `(A,epsilon,delta)=(1279/5000,1/200,1/50)`.  The frontier
  checker `agents/independent-attack/verify_direct_hb_frontier.py` gives a
  closed-form six-inequality continuum proof for C16 through C10, and the
  independently implemented rational-box checker
  `agents/independent-attack/code/verify_direct_hb_support.py` reconstructs all
  corresponding bin assignments.
- The hostile C10 audit independently repaired two nonfatal defects in the
  discovery dossier.  The correct IIb third-bin minima are
  `350000001/35000000000` at `omega=0` and
  `2972900003/105000000000` at `omega=2747/300000`.  In IIc one must use
  `delta_c=delta+4h=25000001/2500000000`, Section-3 epsilon at most `h/1000`,
  and inward endpoint shrink `h/10`.  Its exact checker verifies every
  resulting distribution, structural, capacity, and packing margin and all
  four Proposition 1 hypotheses.  The computational quotient was outside its
  scope.
- A separate count-dependent C10 schedule is an exact analytic candidate,
  not yet a quotient improvement.  Its closed-form prefix checker enumerates
  every feasible count pair using the literal inward-shrunk IIa/IIb/IIc/III
  capacities from the C10 proof.  The least margins are
  `499995341/15000000000000` in IIc at `(3,3)` and
  `899021332939/5600000000000` in maximal-omega Type III at `(13,14)`.
  An independent interval-box engine reconstructs those two critical boxes;
  this spot check is not substituted for the universal closed-form loop.
  The schedule restores count strata 16 and 17, but no quotient monotonicity
  under this support enlargement is claimed.
- The refined C722 direct-Heath--Brown support has a separate source-rebuilt
  exact audit at `delta=361/50000`, `A=3121/12000`, and support epsilon
  `1/250`.  Its constant support has least inward reserve
  `3/350000000000`.  The hard-coded count schedule verifier checks 625
  ordered count pairs in each of seven literal inward-shrunk branches; its
  worst IIc prefix margin is
  `56499669613/285000000000000`, and it passes under normal and optimized
  Python.  Root independently reran both modes.  This is an analytic-support
  pass, not an audit of any quotient.  The discovery and hard-coded schedule
  check were produced by the same research agent, so a final proof would
  still require a hostile reconstruction of the prefix lemma and schedule.
- The fixed-polynomial `{1,L,Z}` stratum-multiplier implementation initially
  had two real defects: it discarded a shifted marginal when the unshifted
  marginal cancelled, and its raw Gram solve did not account for the
  identically zero `L` direction in stratum `R=0`.  Both were repaired.  The
  current implementation SHA is
  `7400369a2e0e321ed032374f1e45f35785b0f0c53a085af18bf5ec2cb3c80162`;
  five tests check the cancellation counterexample, null-direction pruning,
  reduction to the amplitude evaluator, a hand `k=2` recurrence, and a fresh
  signed-vector traversal.  Root reran all five successfully.  No production
  D12 value exists yet.  The completed D4 production artifact has exact
  quotient `0.9348269207174672858115632780638459199717...`, exact negative
  margin, and block/fresh-traversal equality over 312 I faces and 1,200 J
  domains.  Its SHA-256 is
  `ffa607e0f2a8a3b6648f248efb13dc7ac2f1e7ef5809771f31c5f04b30f53158`.
  This is a scoped implementation/result pass, not an independent final
  certificate audit or an upper bound on the multiplier space.
- The same independently tested construction now includes all total
  multiplier degrees through two.  The 96-coordinate exact Gram matrix has
  precisely the three expected dependent labels `(R=0,L)`, `(R=0,L^2)`, and
  `(R=0,LZ)`; the remaining 93-coordinate Decimal100/160 solves agree, with
  residual bounds `1.69e-91` and `4.87e-155`.  Exact contraction of the
  rationalized vector gives
  `0.9539674388485507785778746586710282622062...` and positive exact
  `I-48J`.  The block form and a fresh multiplier-inserted traversal agree
  bit-for-bit across 31,980 channels.  Artifact SHA is
  `fbc8c38d2cf4241fdba03beb4251e2692e96af01ad4918c9a3a1075af2ed6e86`;
  script/test SHAs are `62dad8c9...` and `213dc2c6...`.  Root reran all three
  tests under normal and optimized Python.  This is a scoped negative-result
  pass, not an audit of the forthcoming D12 port.
- A separate exact two-dimensional C722 L/Z integrator reconstructs the D2,
  D3, and D4 bases (150, 250, and 375 labels) without reading serialized
  matrix entries.  Its shifted
  inclusion--exclusion moments agree bit-for-bit with a piecewise-expanded
  density algorithm through dimension 6; `k=1` and `k=2` hand tests pass;
  and matrix contraction agrees with a sum-first/square-second evaluator at
  scheduled `k=8` and the actual `k=48`.  Root reran the D2 checker in normal
  and optimized modes and the D3 reconstruction once; an independent agent
  completed the D4 cache-free/direct run in 554.8 seconds.  The D2/D3/D4
  matrix SHAs are respectively `e808a08f...`, `c9da4795...`, and
  `9744efd5...`.  Their exact rational-vector quotients are
  `0.89660694768491289...`, `0.919288303984479267...`, and
  `0.929761624569573128...`, each with positive exact shortfall.  At D4 the
  checker rebuilt all 375 columns and the matrix and sum-first/square-second
  contractions agreed bit-for-bit.  This is an exact negative
  particular-vector result, not a final certificate or an upper bound for
  richer bases.
- The old Decimal generalized power iteration was found logically unsafe as
  an optimizer because it selects by magnitude rather than largest algebraic
  eigenvalue.  A new diagonal-scaled Decimal Cholesky/Jacobi solver computes
  the full symmetric spectrum at two precisions and gates residuals.  Its
  tests include an indefinite pencil with eigenvalues `{-10,2}`, which
  exposes the old failure mode.  On the exact C70 D4 matrix, 160- and
  240-digit solves agree through 158 digits and exact contraction of the
  rationalized vector gives `0.80379100835794699...`.  This validates that
  particular negative result; it proves neither a finite-space nor an
  infinite-space upper bound.
- The generic `run_basis.py` experiment cache was also found to key entries by
  parameters and basis labels but not by the source implementation.  This did
  not change the already persisted exact particular-vector claims, but it made
  reuse across later integrator repairs unsafe.  Cache version 2 now includes
  the exact-integrator SHA.  A new normal/optimized regression proves that an
  unchanged source hash hits and a changed hash misses.  Future BV extensions
  must rebuild and match the stored D14 principal-matrix SHA before using any
  higher-degree result.  The repaired driver/test SHAs are
  `f660a30d8dd83f13459e0412ded1e28c7ec0864abb41ad04a396475a7905e1d4`
  and `f1736232c9144a75ee76c5e45f675678633914263edb33275ea8a5c901736c1e`.
- The repaired source-bound BV cache has now passed its production provenance
  gate.  Rebuilding all 19,110 D14 entries with integrator SHA `941ee82b...`
  reproduced the historical matrix SHA `ec6d141c...` bit-for-bit.  Extending
  to the 307-label D16 basis gives matrix SHA `989b60a9...` and an exact
  rational-vector quotient
  `0.981278109819760620341348914562469789...`, with positive exact shortfall.
  The separate read-only checker (SHA `35c3d23c...`) refuses missing cache
  rows and validates source, run metadata, labels, matrix hash, vector, and
  both quadratic forms; normal and optimized modes pass.  This is a rigorous
  particular-vector result, not an optimality proof or a positive certificate.
- The deep C10 audit traces every specialized IIa/IIb/IIc/III input to the
  pinned Polymath8a and Stadlmann-2023 sources. Its mandatory repairs are:
  sum the sharp-cutoff boundary by an $L^2$/Cauchy argument; separate target
  and source epsilon parameters; restore the omitted Corollary-4.16 size
  hypothesis; read IIc `100e` as `52e` and `v_2` as `v_1`; retain the
  $q_0^{-2}$ scale, $|\Lambda|$, and
  $\Delta^*=\min\{N/(|\Lambda|x^{5e}),\Delta_1\}$; use the squarefree
  second exponential bound; and correct Type III's `-5/6` to `+2/3` while
  using arbitrary residual alpha. The report checks every downstream
  $\Delta^*$ use and every $q_0,H,x$ exponent. The universal
  Baker--Irving role swap still lacks an SW hypothesis, but C10 never uses it.
- A line-by-line audit of the fresh paper's Proposition 1 proof found and
  repaired source-level omissions in the specialization actually used here:
  truncate the nonnegative minorant globally; tensorize the retreated smooth
  function directly with bounded overlap; restore the omitted coprimality
  subtraction `O(x^(1-beta+o(1)))`; reduce shifted intervals to Definition 3
  using the strict relevant-modulus exponent; fix dummy/index errors; replace
  the printed numerator equality by the required lower bound; and make
  denominator positivity and the final liminf argument explicit.  The audit
  supplies a line-by-line table and four falsification tests.  No `c_2>0`
  claim is made.
- The cache-free grouped fixed-vector evaluator has a separate implementation
  audit in `agents/structural-basis/GROUPED-EVALUATOR-AUDIT.md`.  At script
  SHA-256
  `47167e92a0f346e969706dc282ccb2dfd4ac31a0a75b654938ffbe8423cf4a4a`
  and imported integrator SHA-256
  `941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52`,
  the combined exact regression/adversarial suite passes 17 tests.  These
  include two repaired `k=1` boundary counterexamples, ordered-versus-grouped
  branch factors, exact serial-versus-fork equality, dependency-hash rejection,
  and bit-for-bit equality with a separate pairwise reconstruction of the C20
  degree-4 quadratic forms.  This validates the tested algorithm and small
  cases only; it is not an audit of the unfinished capped C10 degree-12 value.
- A separately written ordered-branch checker has persisted a cache-free
  same-geometry C10 degree-4 reconstruction.  At checker SHA-256
  `1787e7b482a5c2982de56486bc774794f6e671b3db4d9ab7207ebb1c85dc079c`,
  43 tests pass under normal and optimized Python.  The output SHA-256 is
  `2e7c072c87f143e5213db9eccb4a5f864cc9e46c79f978d4dd5f4a0c928a3763`;
  its exact `I`, `J`, `M2`, margin and quotient strings equal the producer,
  and its negative-certificate exit semantics are correct.  Verdict:
  **C10 D4 INDEPENDENT REGRESSION AUDIT PASS**.  This is not a D12 sign or
  final-certificate pass.
- The raw degree-12 input has a logically separate `INPUT AUDIT PASS` in
  `agents/structural-basis/D12-INPUT-AUDIT.md`.  Six fail-closed tests verify
  the complete 272-label no-ones basis through degree 12, all 272 exact
  rational coefficients, uniqueness/order, the independent 12-core plus
  eight-band encoding, and the production CLI load path with integration
  stubbed out.  The source-vector SHA-256 is
  `719c656e6e45388273b4c27f51f7a18b33e9ed1abb5f883e6fcc5de5d6d64a87`.
  This audit deliberately reconstructs no moment and therefore supplies no
  evidence about the capped quotient's sign.
- For exact-runtime reduction the same vector was multiplied by its exact
  714-bit common denominator.  `agents/structural-basis/SCALED-INPUT-AUDIT.md`
  gives `SCALED INPUT AUDIT PASS`: independent tests reconstruct the LCM,
  all 272 coefficient identities, primitive content one, the complete basis,
  byte-identical absolute/relative-path generation, and fail-closed metadata
  mutations.  The integer artifact SHA-256 is
  `8650e44cace6b6d3e4eee8e1632cfd8a59cde6a48f76a8763dcfb400e49f4a93`.
  Scaling both quadratic forms by the same positive square preserves their
  quotient and sign; no integration value is assumed by this audit.
- The sparse 20-band value/gradient producer has a scoped algebra pass but a
  concrete provenance counterexample.  Fresh exact signed-owner matrices,
  serial/fork equality, and a target-support constant oracle validate its
  channel formulas, the single factor `48`, all 312 I faces, all 1,200 J
  domains, and the 695 marginal components.  However, it computes dependency
  end hashes before writing its output and does not forbid output aliasing an
  input or source file; such an alias can mutate a protected file after every
  recorded gate has passed.  The active invocation resolves to five distinct
  paths, so that latent defect is not triggered, but its eventual artifact is
  discovery-only.  Report SHA is
  `fb4b3ad5db39793730a0638a1e7bcfca82c12170863cf9188f1f005dd55c5a54`;
  eight hostile tests pass normally and under `-O`.  The fail-closed consumer
  pins all bytes and emits only a rational trial for a fresh scalar
  reevaluation, because a single action `(A theta,B theta)` cannot determine
  a finite-step quotient or finite-space optimum.
- The high-precision discovery run's completed `I` stage was migrated from an
  older driver into the final-hash `J` runner only to determine the candidate
  sign.  `agents/structural-basis/I-STAGE-CONVERSION-AUDIT.md` gives
  `DISCOVERY CONVERSION PROVENANCE PASS WITH EXPLICIT LIMITS` and five
  independent mutation tests pass.  The raw stage omitted a cryptographic
  integrator hash, so this migration is explicitly ineligible for theorem
  certification even though local file chronology and exact decimal
  preservation support it.  A positive candidate must be recomputed
  end-to-end under one pinned exact implementation.

- The two negative BV piecewise probes have a second implementation under
  `verify/`, written independently of the producer artifacts.  At SHA-256
  `e4d8c55bd3380623cbc946ebd7b5e07c6b80c6e2302e3ceb64e02248688c8586`,
  `dead_core_mass.py` expands the literal D16 square into 5,825 terms and uses
  a coordinate-selection inclusion--exclusion formula different from the
  producer's orbit-family generating function.  Its Decimal100 reconstruction
  gives
  `I_C/I=2.4209735209838009877654067757140e-8` and
  `q'=0.9812781335762444014262788544242...`, agreeing with the independently
  exact artifact.  At SHA-256
  `847f4edc6835b54637abdf21906ee8b0d0eb92c173c5ac247ff6833dd5c94403`,
  `radial_split.py` reconstructs all three inner/outer marginal forms exactly;
  its unrecombined `RR` numerator differs from the stored D16 numerator by
  exactly zero, and its Decimal100 generalized quotient is
  `0.9812858896095555411262925535651...`, agreeing with the producer's exact
  rational-vector contraction.  Four small exact regressions at test SHA-256
  `93c30c74fa57e90047437cfb2c71900e5a96a0c6f7713e665439de21bc4e354e`
  pass under normal and optimized Python.  They include a shifted-triangle
  hand calculation, exact empty-core cancellation, and comparisons of the
  independently derived simplex and cross-marginal formulas with the base
  integrator.  These are adversarial confirmations of negative particular
  candidates, not finite-space upper bounds.

- A hostile audit of the staged affine-transfer probe found a concrete
  fail-open provenance defect before any D12 quotient was emitted.  Under old
  transfer SHA `f8e642c5...`, changing only staged entry
  `((0,0),(0,0))` to `1` still returned status zero and
  `gates_passed=true`, while changing the quotient to about `8.08e-19`.
  Repaired transfer SHA
  `91d1b4ad0c675ccfe36100166bee20bb4007af49e1d0cfe618c8c82c8857f354`
  now requires the stage byte SHA before parsing, rechecks the path at the
  end, requires the exact recorded dependency dictionary, and pins the full
  transitive arithmetic closure.  Its mutation/arithmetic test SHA is
  `5399df38abc2e5dac58a4f4514d1e5324d3479ca4d7517e0f45f1fe9fc48508f`;
  root reran all four tests normally and with `-O`.  The already-running I
  producer cannot retroactively record one transitive hash, so every result
  resumed from that stage is explicitly marked `theorem_ready=false`; a
  positive sign requires a fresh end-to-end run.  Independent audit script
  SHA `6e7e00f5...` exactly contracts the D4 cutoff-10 forms and matches the
  Decimal production path to about 75 digits.  A separate ordered-branch
  literal oracle, SHA
  `1d4cb452c376878fe4fa136008d3b5aeae237159e965c2c5ac56eb4642bc4a26`,
  checks signed affine and quadratic multiplier insertion at `k=2,3` without
  the producer's channel assembly or implicit factor-two convention.  Its
  three-test SHA is
  `078fa3a508c5fa6181b816b9b9bf81d2c19d8450d1dbfd7266c9928ca5ff9bdf`;
  root reran normal and optimized modes.  The scoped verdict and the preserved
  counterexample are in `agents/small-delta-frontier/AFFINE-TRANSFER-AUDIT.md`
  (SHA `13a08e9c...`).  This is an arithmetic/provenance pass only, not a D12
  sign or theorem audit.

- A separately written cache-free exact affine backend now reconstructs
  `F_0(a_R+b_RL+c_RZ)` from checked rational basis and multiplier bytes.  It
  imports no discovery matrix or moment cache, keeps residual/fiber powers
  tagged, and accumulates all 16 ordered branch pairs.  Core SHA-256 is
  `9c21d73af25f63ad16c62a2a1935a9cfd3a8d134d7b7ada2620eddc12e1c3d3e`;
  its three-test SHA is
  `1c6c62124f21804a03d80f7b30108b8a4137b5cccfe02dedd8c0a0e2861ca061`.
  Signed `k=2,3` affine functions agree exactly with the literal expanded
  oracle, forward/reverse and one/two-worker sums agree bit-for-bit, constant
  multipliers reproduce the audited tagged backend, and malformed SHA/label
  inputs fail closed.  The trust boundary is documented in
  `verify/EXACT-AFFINE-MULTIPLIER.md` (SHA
  `45defefdb3d5b67cc4f6294087d476feb557a11301539892368330380a54fd51`).
  This is an independent correctness core, not yet a D12 sign.

- The fixed-point outward-interval fallback received a hostile audit which
  first found six explicit counterexamples: live endpoint reinterpretation,
  exact-shadow hash mismatch, stale scalar-valued support caches, false
  equality of overlapping enclosures, a singleton hash corner, and a mutable
  orbit-table closure.  All six were repaired and preserved as regressions.
  The frozen ring/backend SHAs are `f6f1730f...` and `1dae2001...`; their test
  SHAs are `bf54fbfc...` and `21547aa6...`.  Normal and optimized runs pass
  all nine formal tests.  Additional adversarial coverage includes 160,000
  random expression steps, 100,000 floor divisions, 400,000 comparisons,
  12 random grouped affine cases after cache prewarming, and all 2,700 C10
  branch-pair polygons with 27,000 low-degree moments.  Verdict:
  **DYADIC BACKEND SCOPED AUDIT PASS AFTER SIX REPAIRS**, at
  `agents/small-delta-frontier/DYADIC-INTERVAL-AUDIT.md` SHA
  `085f39c2b8853a5732cf1c062257e12f3c7e413a18fca6b317a17249c7f02d60`.
  No D12 interval result or future result-driver provenance is covered by
  that verdict.

- The grouped D12 affine *result driver* has now received a separate hostile
  pre-launch audit.  Its first revision was retracted after a smallest
  counterexample showed that a byte-pinned integer artifact could carry an
  unrelated coefficient while merely repeating the claimed original-source
  SHA and LCM.  Repaired driver SHA
  `bf0ad4b3c1288c1d2df67e92f9ebe9e63613b9dcd2892c3f96522217d920677b`
  reads the original and scaled sources, pins ordered payload SHA
  `8ea54de0...`, reconstructs the 714-bit LCM and all 272 coefficients,
  checks primitive content, requires 5,929 orbit products, and rereads every
  input after each phase.  The independent mutation suite SHA
  `c3f16fabb32c23b0081477a2739ca1b61f2436713e70c4268571e9c4d588fce7`
  has six tests passing normally and under `-O`.  It independently obtains
  312 I faces and J-domain rows
  `102,99,94,91,88,85,82,79,76,73,70,67,64,61,58,11`, totaling 1,200;
  verifies the factor 48 is applied once; tests actual reverse count order;
  and rejects a straddling interval whose quotient upper endpoint exceeds
  one but whose margin lower endpoint is zero.  Verdict:
  **GROUPED DYADIC D12 DRIVER AUDIT PASS, PRE-LAUNCH SCOPE ONLY**, in
  `agents/small-delta-frontier/DYADIC-D12-DRIVER-AUDIT.md` SHA
  `7315f5dcde8d171eb56aeaf129cefbe2f66f4bc88ab2ac755983c9055af3567a`.
  No D12 integral or sign is covered.  A resumed stage SHA proves integrity,
  not computational origin, so a final theorem invocation must run both
  phases or independently reconstruct I.  Any positive grouped output still
  requires a second arithmetic reconstruction and its own output audit.

- The second, algebraically independent tagged-dyadic driver also has a
  **PRE-LAUNCH AUDIT PASS**.  Driver SHA
  `7e2ed20a68e3c3e95a9566b32cae3d403949a79a3a81adfa61b8dab833b640b9`
  encloses coefficients before entering the separately implemented ordered-
  branch partition-radial recurrence.  Seven hostile tests at SHA
  `1a62de64f491473275926a2e3616f1216c36e2c247fef01f911b2bfa841f8f6b`
  pass normally and under `-O`.  Shadowless intervals crossing zero survive
  every coefficient-cleanup layer, and uncertain signed `k=2`
  base/multiplier boxes enclose five exact literal-oracle specializations in
  both face orders.  Input-scaling mutations, all active target counts
  `r=0,...,15`, stage schema, protected paths, the single factor 48, and the
  strict lower-margin gate are independently exercised.  The report is
  `agents/small-delta-frontier/INDEPENDENT-DYADIC-DRIVER-AUDIT.md`, SHA
  `5c42829e3d412a903f987057b67322ef389468894ab6f6c282eafb3eb0ea3a85`.
  Its scope explicitly excludes any target D12 integral, runtime, error width,
  sign, or output audit.

- The completed Decimal100 cutoff-11 affine transfer has a separate
  **DISCOVERY-OUTPUT AUDIT PASS**, not an integration certificate.  The
  fail-closed auditor pins the output at SHA-256
  `e83d3610b8130d743757a5f01aacc6ff2d2b2acd3128e5ff21b9a01cfa53d8da`,
  independently re-contracts the pinned I-stage entries, checks the distinct
  stage and transfer dependency closures, enforces 272 base coefficients,
  48 multiplier coordinates, 695 components and 1,200 domains, and
  recomputes `q=.9671692127936067321...` with strictly negative margin.
  Checker SHA `1607c4963019a56c512ed15185c507326ec8c969046e4f45f9c264a0450b9973`
  passes normally and under `-O`; report SHA is
  `4eff92fe4bf1a99bae71cbb6f2a1aea06284d33ad8a8ba19c2d9c3436d4b5886`.
  Its first revision incorrectly conflated the I-stage driver hash with the
  transfer-driver hash; that auditor-side defect was repaired while retaining
  the same frozen result bytes.  The producer and auditor both declare
  `rigorous=false` and `theorem_ready=false`, and the sign is negative.

- The C10 support-epsilon fallback was also closed at degree 4 with exact
  arithmetic.  At `epsilon=7/2000`, a rationalized 12-coordinate vector has
  quotient `0.896837259628928073309820817264039399...` and exact negative
  target margin.  The serialized pair matrix and a separately scheduled
  grouped reconstruction agree bit-for-bit on `I` and `48J`; all stated
  Definition-1 margins are recomputed from rationals.  Checker SHA
  `c01631dc06e49a23a2441f9049a9ac428905c67f28736b675e401de7f43c1a5a`
  passes normally and under `-O`.  This verdict covers only the displayed
  particular vector and analytic support identities, not generalized-
  eigenvalue optimality and not any D12 inference.

- A separate exact general-minorant diagnostic gives **GEOMETRIC AUDIT PASS /
  THEOREM_READY=false**.  At
  `(A,epsilon,delta,B,c2)=(521/2000,37/10000,7/1250,21/2500,24)`, an
  exactly-one-large-coordinate symmetric core has `K=0` pointwise and an
  explicit open J fiber extending beyond C10 by `299/150000`.  Its exact
  singleton quotient is nevertheless below `133/500`.  Normal and optimized
  checker outputs are byte-identical (checker SHA
  `e65aa613b9a84ce9faa049d5c8654363a50ee007fdce3fb7e3749da7105cfb18`;
  report SHA
  `e5a6bd96029cb0c673bf489c7b8c1cea01869f080c58965ad03a1f2b8b3de6e1`).
  This disproves the proposed geometric obstruction "J enlargement forces
  K>0", but it does not repair the high-gamma Type-I Siegel--Walfisz gap or
  the signed `c2>0` Proposition-1 implication, so it is not a proof route yet.

- The authorized importance-calibration v6.6 computation produced all 128
  immutable records but failed closed at publication on one `numpy.bool_`.
  Its narrowly repaired, records-only v6.7 replay had a scoped pre-execution
  pass and was explicitly authorized.  The completed-output audit then
  independently replayed all 128 records and returned **AUDIT PASS OF
  REJECTED OUTPUT / NO HEURISTIC CANDIDATE**: degree-1 and degree-2 deletion
  stability fail, `Rhat=1.498...>1.05`, ESS is `85.59...<200`, zero of 16 J
  precision cells pass, and the maximum standardized discrepancy is about
  `557.6>12`.  No matrix, root, vector, or quotient was emitted.  Checker,
  hostile-test, result, and report SHAs are respectively `f051baf7...`,
  `ab594024...`, `0e1daaaf...`, and `c9f84451...`; the mechanism is retired.

- No active25 D16 staged target arithmetic has been launched.  The v3 delta
  audit found a resettable four-hour clock, a post-return-only shard timeout,
  a late extra leaf accepted by the assembler, and injectable memory/sleep
  hooks (`13c5a756...`/`a384a193...`).  V4 then failed because same-process
  mutation could manufacture accepted production-shaped stages and because
  ledger/link/global-interval binding was incomplete (`b1da2c8...`/
  `f020711a...`/`11fe3b77...`).  V5 moved to fresh `python3 -I` processes and
  externally anchored its genuine ledger, but an independent fresh-process
  counterexample supplied 26 canonical, future-dated stages and a manifest
  carrying marker `inner_48J=999`; resume accepted them with zero integrations.
  Its checker/result/report SHAs are `127024d7...`/`a173658f...`/
  `c60934e5...`, byte-identical under normal and optimized Python.  V5 also
  rereads rather than continuously binds the external source SHA.  It is
  frozen and retired.  The successor must be a no-resume one-shot run whose
  starting directory contains exactly its externally anchored ledger, must
  bind startup source bytes directly, and must reject all persisted timestamps
  beyond a fresh live monotonic observation.  The final checker will still
  recompute every arithmetic shard independently.

- The active25 outer even-`B4` denominator block has an independent scoped
  `AUDIT PASS` in both interpreter modes.  The checker imports neither B4
  producer revision and independently performs 55 high-support plus 55
  low-support exact calls, reconstructs all 100 displayed entries and their
  `H-L` differences, matches the preserved v1 values, proves exact rank 10,
  and obtains ten positive LDL pivots.  Normal and optimized canonical outputs
  are byte-identical (checker/result/report SHAs `aa8b8cdb...`/
  `9888d319...`/`8a2a2040...`).  This pass is denominator-only: there is no J
  matrix, quotient, or sieve certificate.

The final `AUDIT PASS` can be issued only after a positive certificate is reconstructed
by a checker independent of the discovery cache and every analytic item above
that lies on the chosen route is either repaired or bypassed.

Exact analytic checks currently run with:

```sh
python3 prime-gap-236/agents/hostile-analytic-audit/audit_exact.py
python3 prime-gap-236/agents/hostile-analytic-audit/direct_hb_exact.py
python3 prime-gap-236/agents/independent-attack/verify_support_889.py
python3 prime-gap-236/verify/check_hb_support.py
python3 prime-gap-236/agents/independent-attack/verify_direct_hb_frontier.py
python3 prime-gap-236/agents/independent-attack/code/verify_direct_hb_support.py \
  --delta 1/100 --A 77747/300000 \
  --bounds 3/20,3/20,97/625,97/625,97/625,97/625,97/625,97/625,97/625,97/625,97/625,97/625,97/625,97/625,97/625,97/625 \
  --gamma-cells 4 --omega-cells 4
python3 prime-gap-236/agents/hostile-analytic-audit/c10_audit_exact.py
python3 prime-gap-236/agents/structural-basis/code/verify_c10_nonconstant_schedule.py
python3 prime-gap-236/agents/structural-basis/code/spotcheck_c10_nonconstant_intervals.py
python3 prime-gap-236/agents/small-delta-frontier/verify_c722_all.py
python3 -O prime-gap-236/agents/small-delta-frontier/verify_c722_all.py
python3 prime-gap-236/agents/small-delta-frontier/verify_c722_lz.py
python3 -O prime-gap-236/agents/small-delta-frontier/verify_c722_lz.py --skip-low-k-tests
python3 prime-gap-236/agents/small-delta-frontier/verify_c10_epsilon_d4.py
python3 -O prime-gap-236/agents/small-delta-frontier/verify_c10_epsilon_d4.py
```
