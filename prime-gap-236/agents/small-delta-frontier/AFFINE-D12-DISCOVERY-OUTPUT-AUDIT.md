# Audit of the C10 D12 affine-transfer discovery output

Date: 2026-09-02  
Verdict: **DISCOVERY-OUTPUT AUDIT PASS; NEGATIVE; NOT RIGOROUS**

## Frozen output

The producer wrote a different basename from the initially queued/monitored
one.  The actual file is

```text
agents/exact-integrator/results/c10_D12_affine_transfer_decimal100_cut11.json
SHA-256 e83d3610b8130d743757a5f01aacc6ff2d2b2acd3128e5ff21b9a01cfa53d8da
```

The absent path
`results/c10_D12_stratum_linear_decimal100_cut11.json` was never treated as a
failed computation; monitoring moved to the actual completed path after root
reported it.  No producer file was modified.

## Independent checks

The fail-closed auditor is
`audit_affine_discovery_output.py`, SHA-256
`1607c4963019a56c512ed15185c507326ec8c969046e4f45f9c264a0450b9973`.
It consumes a caller-supplied result SHA and independently requires:

- exact top-level and gate schemas, accepted status, `complete=true`,
  `rigorous=false`, `theorem_ready=false`, and every producer gate true;
- `k=48`, Decimal precision 100, cutoff 11, 272 fixed coefficients, 48
  multiplier coordinates, 695 marginal components, 312 staged I faces and
  1,200 J domains;
- the pinned integer-scaled input SHA `8650e44c...`, exact D4 affine
  multiplier SHA `ffa607e0...`, and I-stage SHA `96c9b89b...`;
- the six exact C10 support parameters and every transfer dependency SHA;
- all 48 cutoff-applied transferred coefficients reconstructed from the
  source rational vector; and
- all 76 staged I entries, their complete key set, the 16 per-stratum
  contractions and the denominator, reconstructed at Decimal100.

It then recomputes, from the serialized 16 J components,

\[
 N=48\sum_rJ_r,\qquad q=N/D,\qquad M=N-D
\]

under a fresh Decimal100 context and requires exact equality with all four
serialized fields and the boolean sign.  Inputs, dependencies, stage and
result are rehashed at the end.

The first invocation found an auditor-side expectation error: the audit had
used the transfer driver SHA `91d1b4ad...` for the separate I-stage driver's
`driver` slot.  The stage correctly pins its matrix producer
`ba3ff83b...`, while the final result separately pins transfer driver
`91d1b4ad...`.  The auditor now has two explicit dependency dictionaries.
The repair did not touch or reread-favorably round any numerical field; the
same frozen result bytes were audited from the beginning.  This failed first
invocation is retained here rather than hidden.

Normal and optimized modes are byte-identical, with output SHA-256
`6b711d1be6916838b540a720f959089a049218df062d6aabab0eb3f2ddf66bfe`.

## Recomputed sign

The independently contracted denominator agrees exactly with the frozen
comparison value:

```text
D = 9.404805046184364933993801445964141570663344888014190056715425272135294022457997898153502271689941759E+311
N = 9.096037892995472439112847946761071826521884812110357334729191462324513650889701137458593316040739739E+311
q = 0.9671692127936067321469619048809532704996719782235687810561380108925883953316516260403891506696291930
M = -3.08767153188892494880953499203069744141460075903832721986233809810780371568296760694908955649202020E+310
```

Thus `margin_positive=false`; the shortfall is

\[
 1-q=0.0328307872063932678530380951190467295003280217764312\ldots .
\]

The producer reports 15,305.70 seconds for J and peak RSS 335,768 KiB.  This
audit validates serialized arithmetic and provenance only.  It does not
independently integrate the 1,200 domains, provide an error interval, or
prove optimality in any affine space.

## Five-direction residual gate

The queued five-coordinate screen is retired without execution.  It would
test only

```text
(R,channel) = (11,1),(11,L),(11,Z),(12,1),(13,1)
```

around this transferred vector.  Its conservative cost was 2.6 hours and
0.68 GiB.  The same D4 cutoff-boundary rescue changes the quotient by only
about `1.47e-7` (the best individual two-vector change is about `1.456e-7`),
whereas the D12 candidate needs `0.0328307872...`, over `2.2e5` times as much.
Moreover the transferred candidate is itself about `0.00380063` below the
already known fixed D12 polynomial quotient `.9709698476...`, and the five
boundary directions do not make that fixed multiplier belong to the tested
span.

This is an explicit heuristic resource gate, not a mathematical upper bound.
The omitted 34 affine directions, their correlations, and other multiplier
spaces remain unbounded by this negative result.

## Commands

```bash
python3 agents/small-delta-frontier/audit_affine_discovery_output.py \
  agents/exact-integrator/results/c10_D12_affine_transfer_decimal100_cut11.json \
  --expect-sha256 e83d3610b8130d743757a5f01aacc6ff2d2b2acd3128e5ff21b9a01cfa53d8da

python3 -O agents/small-delta-frontier/audit_affine_discovery_output.py \
  agents/exact-integrator/results/c10_D12_affine_transfer_decimal100_cut11.json \
  --expect-sha256 e83d3610b8130d743757a5f01aacc6ff2d2b2acd3128e5ff21b9a01cfa53d8da
```
