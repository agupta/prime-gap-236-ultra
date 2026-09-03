# Independent audit: C10 D4 degree-three finite-space obstruction

## Verdict

`AUDIT PASS`

The pinned artifact proves the claim in its stated scope: on the exact
154-dimensional Gram quotient of the 160-coordinate fixed-base
`1_R F0 L^a Z^b`, `a+b<=3`, space, `A-B` is positive definite.  Here
`B=48J`, so every nonzero quotient class has

```text
q = (v^T B v)/(v^T A v) < 1.
```

The canonical obstruction artifact is
`agents/small-delta-frontier/results/c10_D4_degree3_finite_space_obstruction.json`,
SHA-256
`ace35d91e3ddc1d912711e140d72e54b6ad105355a59e44b07b9f53f3b2b1424`.
No counterexample was found.

This verdict is deliberately limited to the finite D4 multiplier space
reconstructed from the pinned primary moment artifact.  I did not rerun the
2,284-second fused-plus-unfused source integration, and this audit makes no
D12 claim.  The primary artifact itself records that source-integral trust
boundary; the obstruction checker does not conceal it.

## Independent verifier

`agents/audit/verify_d4_degree3_obstruction.py`, SHA-256
`5df6955c2f61bfdecf384a5a172bad5e194cc07749da9d44a67d56f61ba634d9`,
uses only the Python standard library.  It imports no producer, consumer,
moment-table, or obstruction-checker code.  It independently:

1. checks every frozen artifact and every source/data hash in the producer
   gate;
2. derives the 10,980-tag matrix-query inventory;
3. parses the 448 dense I rows and 10,516 sparse nonzero J rows;
4. reconstructs all 160 by 160 rational entries with the factor 48 applied
   once;
5. verifies the common kernel and exact Gram rank;
6. rebuilds `C=A-B`, its power-of-two congruence, and all interval pivots;
7. recomputes the midpoint residual and perturbation bound exactly.

Both invocations print the same canonical line ending in
`"status":"AUDIT PASS"`:

```sh
cd /home/anish/code/prime-gap-236-ultra/prime-gap-236
python3 agents/audit/verify_d4_degree3_obstruction.py
python3 -O agents/audit/verify_d4_degree3_obstruction.py
```

## Dependency findings and hashes

Every byte identity below matched.  The D4 input, D2 exact reference, D2
fused oracle, and all thirteen producer sources are also exactly the
path/hash inventories frozen inside the producer gate.

| dependency | SHA-256 | finding |
|---|---|---|
| primary D3 moment artifact | `c9cce84c8a75f231738edabfb7c0ca17e48085b2f4e27f4305866103b8d4d0f5` | canonical rows/status accepted |
| obstruction artifact | `ace35d91e3ddc1d912711e140d72e54b6ad105355a59e44b07b9f53f3b2b1424` | canonical certificate accepted |
| D4 input | `2b11a18c697e9a2be61204b5493bf7a235ce4add39d853bbb4d76ef31fb4666b` | producer-gate match |
| D2 exact reference | `fbc8c38d2cf4241fdba03beb4251e2692e96af01ad4918c9a3a1075af2ed6e86` | complete embedded contraction replayed |
| D2 fused oracle | `72ece5aa4a15536153d7634ee630ebf5e1090dc2ce0a7104cf00190bf310f6eb` | producer-gate match |
| producer gate | `964ab9cdbe952b317f4c42d7b18a47269f886448fdf5f53d581f754405e32e3b` | exact source/data inventory accepted |
| consumer gate | `a1ab82c3f5f4805c3f3c2506baa00295caf884f94200da290bb906f74e4b0ed3` | result/reconstruction policy accepted |
| authorization | `8bf587b2ee0c0ff27c99d18446802b7be3007c17651cf4aa6c573b1745445c89` | gate and driver bound |
| consumer report | `4f92ffd427e7d8ca58e4a8e59f38ea0b383e8d57ba7e0668fc6df36074d6b797` | frozen comparison report present |
| consumer ledger | `5c99e3a52172a768b98154a725bc0e1ae03bd7ab5763c815f8de3989cb0389e2` | frozen invocation ledger present |
| obstruction checker | `d422fe7a472c61223a367c2e1cc1bb332fa79bcb2036f2e083c9ee183ed3d3d1` | artifact self-binding match |
| obstruction tests | `da96598022fb5c6db88471736ef7ee80d3540abef928328a48c014911834848c` | 7/7 normal and 7/7 `-O` |
| frozen consumer | `fedf1970b197af825675fa62644aa227875487453d125ad454d213ebcdedfb7c` | checker binding match |
| consumer tests | `421f5630ade4077282c96646542a058202d0659962b065ec74093e56e6c6c749` | 7/7 normal and 7/7 `-O` |
| D3 producer | `e48d46f447893d21addef38d979670107086550495fd390a1adeebf1ad6ba7ef` | gate/result/authorization match |
| D3 producer tests | `a2f80e49a302d1c77c5edbff74f989a4b4934270a39fd8c1d8defc552f1f3b46` | 3/3 normal and 3/3 `-O` |
| unfused moment table | `fcc471d8a0c8dce01147b6984f981ae5f40ef08a943d2f05ecbe1ec3b0eadccd` | producer-gate match |
| unfused moment tests | `fe9ceb7767231751275931f1ea395fb910fa9f6c61e6c3cb6ccbabbc7e7d863b` | 3/3 normal and 3/3 `-O` |
| fused moment table | `8f8eabfa1f56db41da69bd425f7c506710b292f9e86ad1255d733dac018c8190` | producer-gate match |
| fused moment tests | `c0ede840c75b3ac73d15b160fb87b524182940f7b4180e002108eae93a0053ab` | 3/3 normal and 3/3 `-O` |
| exact integrator | `941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52` | producer-gate match |
| grouped fixed vector | `47167e92a0f346e969706dc282ccb2dfd4ac31a0a75b654938ffbe8423cf4a4a` | producer-gate match |
| stratum quadratic | `62dad8c96005bdb06945552a36b6dc35cecea6633daa5f3cf06e514a6aa77234` | producer-gate match |
| stratum linear | `7400369a2e0e321ed032374f1e45f35785b0f0c53a085af18bf5ec2cb3c80162` | producer-gate match |
| stratum amplitude | `d23d42315d7b518ae5d3f200a6192f47f3500d6eebd3a73fb6aa4ce7a23c7887` | producer-gate match |
| robust generalized solve | `2086244acb674e5bd92e4880fb38d32d6dd981cd0272db595de2578554da257e` | producer-gate match; not used by rigorous obstruction |
| scheduled-basis runner | `06f79a13dbf172f40716d603ae8d824b5f65d2d69ed08dee59bd5c091821c4d0` | producer-gate match |
| scheduled-vector verifier | `97f36696712f9cbe0cc0fff1fab6c4dc5ec4850220c12ebcc63f9c794aff1a1a` | producer-gate match |

The relevant original TeX,
`sources/stadlmann-2608.31126-src/Bounded_Gaps_2.0.tex`, has SHA-256
`c0d5d2317c77f4de7eacdef6e1d4b1eb6433e6240b5c09273b3d4eee99e6c3ba`.
Definition 5 gives `I` and `J`; the main sieve inequality and the matrix
identity at TeX lines 1762--1770 put `kJ` in the numerator.  With `k=48` and
`c1=c2=0`, this confirms the sign/orientation `q=(48J)/I=B/A`.

## Reconstruction, quotient, and kernel

- The total-degree-three monomial inventory is exactly
  `{L^a Z^b: a,b>=0, a+b<=3}`, ten monomials.  The cap schedule with
  `delta=1/100` and `beta(r)=97/625` for `r>=3` makes counts 0 through 15
  feasible and 16 first impossible.  Hence the stated coordinate inventory
  is exhaustive: `16*10=160`.
- The independently derived J query inventory has 10,980 tags and SHA-256
  `746de1d75e0deee16c7e15380e1b912dbe36c6de215e1e45844cec1ceea7fa92`.
  The artifact contains 10,516 canonically ordered, nonzero, mirror-symmetric
  rows.  The remaining 464 tags reconstruct as zero under the pinned
  producer's fused/unfused equality gate.
- Independent matrix reconstruction gives
  `A` SHA-256
  `5a412e448a8156d8b4f6d94d58a146b6c2b9e05a0dacd5c47b20720e2dad985e`
  and `B=48J` SHA-256
  `58aa4b989641517597c85c0c3ad85d7a3bf96faed6665a3331ed3fa211a74252`.
- The embedded D2 vector contracts to the exact reference denominator and
  numerator and reproduces the serialized quotient as `B/A`, independently
  ruling out a sign, transpose, or extra/missing factor-48 error.
- At `R=0`, `L=0`; the six channels with positive L power have indices
  `1,3,4,6,7,8`.  Their complete A and B rows are exactly zero.  Independent
  exact block LDL gives 154 positive A pivots on the complement, with ordered
  pivot SHA-256
  `465e53036085cbeb95a5550bb12e9db6630ef40bbe5a6b6faf9b642693e45dce`.
  Thus the kernel elimination is exact and exhaustive, not tolerance based.

## Positive-definiteness proof

The independently rebuilt active `C=A-B` has SHA-256
`bd9c5717294d0284e755e5ca2df895ba38e4dcbf083c1f27137cb2261812b241`
and is exactly block tridiagonal in R.

The audit's interval implementation represents endpoints on the
`2^-768` grid but performs endpoint algebra as exact `Fraction` operations.
Each exact input is snapped down/up; multiplication and division take all
four endpoint corners; division requires a positive lower denominator;
squaring handles intervals crossing zero; every result is snapped outward.
It reproduces all 154 stored pivot endpoint pairs byte for byte.  Every lower
endpoint is positive, and the endpoint-list SHA-256 is
`ff8fb22931c5511a142456684cecdf9ee891a820bec67bda8648a2adfff03325`.
This directed LDL alone proves positive definiteness of the congruent matrix.

The second closure also reproduces exactly.  Dyadic midpoint factors give
`H=Lhat Dhat Lhat^T+E`; the exact residual-entry list has SHA-256
`abafdfa0bebe44b8065d861c3d2ba48af9ce5ffcb0b2bf52906c5c541b3140af`.
Upward `2^-512` recurrences bound both inverse norms.  For symmetric E,

```text
lambda_min(Lhat Dhat Lhat^T)
  >= min(Dhat)/(||Lhat^-1||_inf ||Lhat^-1||_1),
||E||_2 <= ||E||_inf.
```

The exact computations give `||E||_inf <= 2^-725` and the base lower bound
at least `2^-388`, a strict 337-bit separation.  Positive diagonal congruence
then proves `C` positive definite.  Since A is positive definite on the same
154 coordinates, `v^T(A-B)v>0` is exactly equivalent to `q=B/A<1` for every
nonzero quotient vector.

## Executed checks

The canonical checker was run in normal and optimized modes at new `/tmp`
paths.  Both returned rank 154, all pivots positive, and the strict residual
gate.  Their exact JSON content after removing the runtime/RSS measurement
was identical to each other and to the canonical artifact, with normalized
SHA-256
`414c5bb1c9770b5998e43400aa4fcfedf515833821852d953449cb705d35d673`.
The raw normal and `-O` outputs had SHA-256
`7317a9b7525fa1f34621ea82ef2ca66eaa369b473d7526d23948dd46ae84921e`
and `51a089b97d319b2e1d36e5f27f242e55678b954e5859e87643c47a4ad9a23d50`,
respectively; only their measured time/RSS fields differ.  The checker is
new-path-only, so substitute fresh output names when repeating these commands.

```sh
python3 agents/small-delta-frontier/certify_d4_degree3_finite_space.py \
  --result agents/small-delta-frontier/results/c10_D4_degree3_moment_exact.json \
  --expected-result-sha256 c9cce84c8a75f231738edabfb7c0ca17e48085b2f4e27f4305866103b8d4d0f5 \
  --expected-checker-sha256 d422fe7a472c61223a367c2e1cc1bb332fa79bcb2036f2e083c9ee183ed3d3d1 \
  --output /tmp/d3-obstruction-audit-normal.json

python3 -O agents/small-delta-frontier/certify_d4_degree3_finite_space.py \
  --result agents/small-delta-frontier/results/c10_D4_degree3_moment_exact.json \
  --expected-result-sha256 c9cce84c8a75f231738edabfb7c0ca17e48085b2f4e27f4305866103b8d4d0f5 \
  --expected-checker-sha256 d422fe7a472c61223a367c2e1cc1bb332fa79bcb2036f2e083c9ee183ed3d3d1 \
  --output /tmp/d3-obstruction-audit-opt.json
```

The checker, consumer, producer-preflight, unfused moment, and fused moment
test suites all passed under both normal Python and `python3 -O`: 23/23 tests
per mode (46/46 executions total).  No acceptance condition in either the
canonical checker or the independent verifier relies on `assert`.
