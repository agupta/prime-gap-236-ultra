# Independent audit of the capped exact checker

Status: **SCOPED AUDIT PASS**, 2026-09-02.  The frozen independent checker
reconstructed the same-geometry C10 D4 scalar and matched every producer exact
field bit-for-bit.  Its expected exit status 1, positive-denominator flag, and
negative-margin failure flags were also correct.  This verdict is only for the
C10 D4 regression and checker plumbing.  The C10 D12 run remains deliberately
guarded and has not been launched.  The historical C20 D4 regression is not a
valid target-specialization test because its exact geometry has
`alpha-eta != delta`.

## Primary-source derivation

This audit used `agents/source-fidelity/source-tree/Bounded_Gaps_2.0.tex`
before reading any checker specification.  Definition 1 gives, for one band,

```text
sum(t_i) <= alpha=A+epsilon,
sum(t_i : t_i>delta) <= B_r,  r=#{i:t_i>delta}.
```

Definition 5 gives `I` over that support and gives `J` as the square of a
one-coordinate marginal over 47 shared variables, with the additional shared
sum bound `eta=A-epsilon`.  Boundaries do not affect these Lebesgue integrals.
For the target parameters

```text
alpha=79247/300000, eta=76247/300000, delta=1/100,
B_1=B_2=3/20, B_r=97/625 (r>=3),
```

one has `alpha-eta=delta`.  Consequently, on the outer `J` domain the small
distinguished-coordinate fiber is exactly `[0,delta]`.  For a base face with
`r` large coordinates, shifted large mass `X`, and small mass `V`, the excess
length of the large fiber is

```text
q=min(eta-r*delta-X-V, B_(r+1)-(r+1)*delta-X).
```

The ordering changes at the horizontal line
`V=eta-B_(r+1)+delta`.  This derivation is the basis of the ordered `J`
branches in the implementation.

## Trust boundary

`exact_capped_certificate.py` consumes only these fields from the discovery
JSON:

- `k`, `degree`, and `basis_dimension`, checked against a selected local
  preset;
- the complete finite list of basis labels;
- the same-length list of canonical rational coefficients.

It ignores the discovery JSON's parameters, matrices, hashes, eigenvalues,
quotients, cached values, timing data, and claimed signs.  In particular, the
target discovery JSON contains full-simplex `beta` values and they never enter
the calculation.  Target support values are code-local constants.  A canonical
SHA-256 of the ordered `(basis,rational_vector)` payload is pinned separately
for provenance and coefficient/label alignment; irrelevant discovery metadata
is excluded from that payload hash.

The parser rejects duplicate JSON keys, non-finite JSON constants, booleans in
integer fields, malformed/noncanonical rational strings, duplicate or
incomplete basis labels, dimension mismatches, degree violations, and an
identically zero vector.  It locally generates the complete no-ones label set.

The label contract is explicit:

```text
[b,lambda] = (1-sum(t_i))^b m_lambda(t),
```

where `m_lambda` is the unnormalized sum over distinct monomials in the orbit.

## Independent exact algorithm

The implementation does not use the paper's serialized matrices or either
research evaluator.

1. It reconstructs monomial-symmetric products by fixing one orbit
   representative, enumerating how equal exponent classes overlap occupied
   coordinates, and applying orbit-stabilizer division.  The resulting
   coefficients are required to be exact integers.  Commutative argument
   pairs use one canonical bounded-cache key, so a symmetric square does not
   repeat the same derivation in reverse order.
2. The production backend does not flatten residual `(1-S)^a` powers into
   partitions of exponent one.  For `I`, it forms the fixed square directly
   from checked label pairs and the exact identity
   `(1-S)^b=sum_c binom(b,c)(1-alpha)^(b-c)(alpha-S)^c`.
   The old fully expanded backend remains available only for `k<=4` tests.
3. On each face with `r` large coordinates, it translates large coordinates
   by `delta`.  It handles the `[0,delta]` small boxes by exact
   inclusion-exclusion.  Degree/count convolution implements both finite
   expansions without enumerating repeated exponents individually.
4. Dirichlet angular factors reduce each orbit on a fixed face to one radial
   polynomial keyed by `(h,X_power,V_power)`.  For `J`, each `(nu,r)` transform
   is built once and distributed across all marginal `(family,q)`
   coefficients before the transform is dropped.  Each resulting family is
   packed once per face and shared immutably by its ordered branch jobs;
   impossible IE shifts are pruned from the face-local output.
5. It clips the rational first-quadrant simplex by the cap and ordered-branch
   halfplanes using Sutherland--Hodgman clipping.  Each surviving shift is
   clipped once; the polygon is triangulated once and all requested affine
   simplex moments are evaluated as an exact batch from factorial identities.
6. For `J`, it distinguishes the 48th exponent directly in each checked
   `(a,lambda)` label and applies the finite antiderivative expansion from
   Definition 5.  Marginal terms retain the two tags
   `(fiber_slack_power,(1-U)_power)`.  Their product is expanded only into the
   two aggregate affine forms at the final geometry batch.
7. It enumerates all ordered pairs from the source's four `Sdelta`, `Stotal`,
   `Lbig` (cap-limited), and `Ltotal` marginals.  Under the target identity,
   `Stotal` is boundary-only; it and complementary `Lbig/Ltotal` pairs are
   passed to the geometry and required to have exactly zero measure.
8. It retains both the expanded streaming engine and the original literal
   term-by-term engine as independently exercised `k<=4` oracles.  The tagged
   production engine streams one face at a time.  An optional
   two-worker mode assigns two deterministic contiguous `r` blocks under
   `fork`, validates exact face coverage, and sums returned Fractions in the
   requested face order.
9. It computes `I`, `J`, `M2=48J`, and `M2-M1=48J-I` as reduced `Fraction`
   values, and requires both `I>0` and `48J-I>0` before returning success.

With `--output PATH`, the CLI first atomically installs a fail-closed JSON
sentinel, then atomically replaces it with the exact bytes emitted on stdout
after a completed calculation.  A handled calculation failure replaces any
stale success with a failure JSON.  Input/output path aliases are rejected.
This persistence path contains only the checker's reconstructed result, not
raw discovery metadata.

Process-local memoization contains only pure subexpressions produced during
the current run.  The orbit-product cache is bounded at 16,384 entries and
each radial/literal moment cache at 8,192 entries.  Face radial maps are
discarded before the next face.  Nothing is loaded from or written to a moment
cache.

## Light tests completed

`python3 -m unittest verify.test_exact_capped_certificate
verify.test_independent_tuple_verifier verify.test_verify_all_skeleton` and
the same tests under `python3 -O` pass.  After the packing and persistence
change there are 43 tests: 36 exact-checker tests, five independent-tuple
tests, and two orchestration tests.

The 36 exact-checker tests include:

- orbit products with repeated and odd parts, plus exhaustive literal
  permutation comparisons for a small four-variable family;
- exact triangle moments and independent halfplane clipping, plus equality of
  batched moments with the retained scalar triangulation;
- one-dimensional shifted-large and capped-small moments;
- a two-aggregate rectangle moment;
- direct equality of the new face-radial aggregation with the term oracle for
  repeated/signed exponent shapes, every face of `k=2,3`, and a quadratic
  affine fiber factor, plus strict IE-shift boundary tests;
- equality of the two-affine tagged moment batch, both unpacked and explicitly
  packed, with a combined-power scalar integral;
- the closed-form constant-function `k=2` values `I=1/8`, `J=13/324`;
- a capped constant `k=2` example whose large fiber switches between cap- and
  total-limited branches in the interior, with independently derived
  `I=11/160` and `J=403/24000`;
- signed rational polynomial comparisons with literal named-variable
  expansion and direct simplex integration at `k=2,3,4`;
- a signed capped `k=3` polynomial with interior ordered branch geometry,
  compared exactly with the literal engine;
- a mixed signed degree-4 capped `k=4` vector, including residual and orbit
  terms, compared exactly with both expanded and literal engines;
- direct re-expansion of both tagged `I` square coefficients and tagged `J`
  marginals back to the expanded symmetric-polynomial oracle;
- serial/two-worker and forward/reverse equality on a signed capped case;
- a packing call-count assertion: the interior-switch `k=2` `J` case packs
  exactly its three active families on each of two faces, rather than once per
  ordered branch job;
- enforced refusal by both expanded and literal oracles when `k>4`;
- a private general `k=1` zero-shared-variable test with
  `alpha=delta=eta=1/10`, constant `F`, and `J=1/100`;
- duplicate-key, duplicate-label, missing-coefficient, wrong-`k`, truncated,
  noncanonical-rational, and altered pinned label/vector provenance failures,
  plus a check that raw discovery support metadata is mathematically ignored,
  that an altered code-local target cap is rejected, and that historical C20
  geometry cannot enter the target-specialized path; and
- byte equality between atomic output and emitted stdout, plus replacement of
  a stale success by the pre-computation sentinel and final handled-failure
  JSON.

The first low-dimensional `J` test exposed a real edge error: when the small
aggregate has dimension zero, the cap/total equality had full measure in that
degenerate space and was counted on both closed branches.  The implementation
now assigns equality to one ordered branch only.  This fix was made from the
small exact counterexample, not by accommodation to a research checker.

## Same-geometry C10 D4 regression trail

The regression uses the final target geometry but degree four.  Its pinned
artifacts are:

```text
raw coefficient JSON SHA-256:
  ac48820277b68dd5232fd2678a7980d60318b69e60d15d44d9c6eb006fa1ea0d
ordered (basis,vector) payload SHA-256:
  0122b431b59165455325974760184f3f42a7fe64cdc326e2dd5487452023cafb
producer exact-scalar JSON SHA-256:
  51b1e6b36e289a69f7d52401ed9db7714e014a0182826f0e2d20a1f04b494874
canonical producer (I,J,M2,margin,quotient) tuple SHA-256:
  2ae7ea4d4741b3e4e280e4c7e9050a544a06b2401c4a15731fbf606f138e16f2
```

The producer artifact is internally exact-consistent:
`numerator=48*j_value`, `margin=48*j_value-denominator`, and
`quotient=48*j_value/denominator`.  It has positive `I` but negative margin,
so exit status 1 is expected and this D4 vector is a regression fixture, not a
passing prime-gap certificate.

The first independent run used checker SHA-256
`ec6dba634bede71658d3c2cf030d4ae910bbc3ce377dea5f42a47a2244c00530`
with one worker.  Its complete stdout visually agreed with the artifact, but
the closed execution session was not persisted.  That is recorded only as
transcript-level agreement.  The current packing/persistence revision is
SHA-256
`1787e7b482a5c2982de56486bc774794f6e671b3db4d9ab7207ebb1c85dc079c`.

That frozen revision was then run once in forward, two-worker mode with atomic
output.  The persisted checker JSON is
`verify/c10_capped_fullD4_independent_exact.json`, SHA-256
`2e7c072c87f143e5213db9eccb4a5f864cc9e46c79f978d4dd5f4a0c928a3763`.
A programmatic direct-string comparison gave

```text
checker I             == producer denominator : true
checker J             == producer j_value     : true
checker M2            == producer numerator   : true
checker M2_minus_M1   == producer margin       : true
checker quotient      == producer quotient     : true
```

The canonical checker scalar-tuple SHA-256 is
`2ae7ea4d4741b3e4e280e4c7e9050a544a06b2401c4a15731fbf606f138e16f2`,
identical to the producer tuple hash above.  Independently parsing the emitted
fractions also verified `M2=48J`, `M2_minus_M1=M2-I`, and
`quotient=M2/I`.  The checker reported `I>0`, negative margin, and
`certificate_passes=false`, and exited 1 exactly as required.  The atomic file
ended in a newline and contained the completed result rather than the sentinel.

Verdict: **C10 D4 INDEPENDENT REGRESSION AUDIT PASS**.  This is deliberately
not a D12 sign or final-certificate verdict.

## Challenge to `FINAL-CHECKER-SPEC.md`

The specification was read only after the derivation and implementation above.
Its support, face, Dirichlet, orbit, and polygon formulas agree with the
independent derivation.  Three trust/scope points need explicit resolution:

1. The original wording combined the target requirement
   `alpha-eta=delta` with a `k=1, alpha=delta=eta=1/10` regression that violates
   that identity.  The specification now states that the production path stays
   strict while a private general test path owns this valid Definition-5 edge.
   The implementation follows that split.
2. Pinning label/vector provenance is useful, but irrelevant raw discovery
   metadata must not become a mathematical premise.  The implementation pins
   a canonical hash of exactly the ordered label and rational arrays.  It
   continues to ignore the raw file's known full-simplex beta values and uses
   code-local capped support.
3. Requiring a locally generated basis in one unspecified "recorded order" is
   under-specified unless that generation order is made normative.  Pairing
   every unique label explicitly with its coefficient and checking set
   completeness is mathematically invariant under a simultaneous reorder.
   A separate pinned-artifact comparison may, of course, enforce serialization
   order for provenance.

The specification's allowance for empty, invocation-local memo tables agrees
with this implementation and confirms that "cache-free" excludes persistent
or prepopulated caches, not exact common-subexpression elimination within one
run.

## Pending decisive work

- Only after authorization, run the guarded capped C10 D12 calculation.
- Insert exact target values into the currently unarmed top-level orchestrator
  only after the capped result and its provenance have been audited.  The
  orchestration skeleton and independent tuple verifier already fail closed;
  neither has a final-PASS path while the exact values are absent.
