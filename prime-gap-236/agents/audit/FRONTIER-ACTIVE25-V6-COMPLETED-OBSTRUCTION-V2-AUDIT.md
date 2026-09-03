# Active25 D16 v6 completed-output obstruction audit

## Verdict

`INDEPENDENT ARITHMETIC RECONSTRUCTION AND EXACT FINITE-SPACE OBSTRUCTION PASS`

This is a reproducibility pass for the completed v6 arithmetic and a rigorous
negative result for the frozen 27-dimensional space.  It is not a bounded-gap
theorem claim.  `theorem_ready` remains `false`.

The independently rebuilt matrices equal the serialized candidate matrices
exactly.  The particular rational vector has quotient

```text
92897375898349188514599709951216368905239050887927251603305922902061365939408100669132947797160119817716961655757587800144257063380395560856598583290376684641533448738999633467286107139736170533071547189227575021252166738862439550718407845582288967622270416866833816960775123205225158757954771975471425713977657556585367832189370612778892552574647188921/94669022434748535670107283592121555951480034630760318300475907898593610877646162162217108393756833117847775791113277862954435959426561246958816055224354745734604796817646203439360500891249093532842166331292058812602241741674165281305323824392767172364304049235089497775865020366329849396944466172386230354583118377048441340955911190904197453004619206250
```

or approximately
`0.98128588960955554112629255356510083066903841676631`.  Its exact margin
`N-D` is

```text
-1771646536399347155507573640905187046240983742833066697169984996532244938238061493084160596596713300130814135355690062810178896046165686102217471933978061093071348078646569972074393751512922999770619142064483791350075002811725730586915978810478204742033632368255680815089897161104690638989694196914804640605460820463073508766540578125304900429972017329/91326840911059064655483274725943483637889954414999962354064403046294486196305340363930439377291417710415142723187670321827156060344732876800000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000
```

This is approximately
`-1.9398968788646807396840839773526782287179640146335e-152`.

## Independent reconstruction

The checker held and rebound the complete pinned source closure, the exact
28-leaf attempt directory, the candidate, and the root authorization.  It then:

1. reparsed and recontracted the D16 radial coordinate before each shard;
2. recomputed all 26 common-count integrations from the low-level exact core;
3. recomputed all shell masses and all four ordered `HH`, `HL`, `LH`, `LL`
   blocks, with 9,360 domain records in each orientation;
4. assembled fresh `I_diagonal` and `48J_matrix` forms;
5. only then parsed and compared the 26 stages, manifest, and candidate;
6. recomputed every exact scalar and required the serialized crossing flag to
   equal the sign of the fresh margin.

The canonical fresh-forms SHA-256 is
`e22f3ccc7057b6daf09665a4bc2ba5846f45eabb0fc36834012f3480c0ce1b17`.

## Exact finite-space obstruction

On the fresh matrices the checker formed

```text
M1 - M2 = diag(I_diagonal) - 48J_matrix
```

and performed a no-pivot exact `Fraction` LDL^T factorization.  Exact
reconstruction of `L D L^T` was checked entry by entry.  All 27 pivots are
strictly positive.  Therefore `M1-M2` is positive definite.  Since the fresh
`I_diagonal` entries are positive, every nonzero vector in this fixed
27-dimensional space has generalized quotient strictly less than one.

- Pivot signs: 27 entries, all `+1`.
- Minimum pivot index: `0` (zero based).
- The exact minimum pivot is the positive opposite of the margin printed
  above.
- Canonical exact pivot-list SHA-256:
  `fbfbe8c73f0388b6680c8ec554cf00d505293f5f076b27b657cfbca53fcc96e2`.
- Canonical exact unit-lower-matrix SHA-256:
  `03b181d51cec0f4b44543615575e702acad610615387c56aef09dacc8a4e02e5`.

The canonical JSON contains the complete 27-element exact pivot list.

## Design mismatch and successor scope

The frozen prelaunch design
`976d7f43d52d45be33def40f376ebfe657af0fe3aba880f5c4de807a46b2693e`
requires a positive exact margin.  The preserved design-conforming v1 checker
therefore cannot report a reproducibility pass for this mathematically
negative attempt.  Its initial long replay was stopped before publication
once the completed candidate's negative sign was known; it produced no result
artifact.

The distinct v2 checker retains the entire v1 reconstruction order and exact
comparisons, but makes the terminal result outcome-neutral: matrix, scalar,
and sign equality are required, and a non-crossing outcome must additionally
carry the exact positive-definiteness certificate above.  No interrupted or
rejected artifact is an input to v2.

## Regression and replay results

- v1 hostile suite: 20/20 pass under normal Python and `python3 -O`.
- v2 focused suite: 22/22 pass under normal Python and `python3 -O`.
- v2 normal replay: wall `42:10.86`, user `2217.31 s`, system `5.80 s`,
  maximum RSS `49,836 KiB`, exit 0.
- v2 optimized replay: wall `40:36.34`, user `2229.62 s`, system `8.01 s`,
  maximum RSS `49,364 KiB`, exit 0.
- Normal and optimized canonical JSON are byte-identical.

## Exact pins

- Outcome-neutral v2 checker:
  `2c08afe2c75b6a9a4546aa94e958a2810a3e77bcf807aae9429420de5d84d490`.
- v2 tests:
  `8b6ee299aa859ec470acd318b7b357fb7841193690c13a6169128c2437b88361`.
- Preserved positive-only v1 engine:
  `6f73b06cf2c494b271a2ce169a00b9324b1ef1f41b224903c6c969bc7edeaa66`.
- v1 tests:
  `7d9e0097539d90ab0ae6963d9365cccea8887f1b99f70567146c3bbf020bce80`.
- Canonical result, normal replay, and optimized replay (each):
  `c0a83ceeec28d4aa419f384afaffd180f7438ccee1d8dae6997cd0b768cedf83`.
- Completed manifest:
  `493ca9c10f790d9d12adaa0a98816bf08756d6f034c0984a0e244b906d5b7faa`.
- Conditional candidate:
  `641832b027d37b769d6f5a1de2248be178f5a4d7b92d9eb0ee17b49ab9e5c77d`.
- Root authorization:
  `e973251372fa0ebacf927fc03b252892b4fddce316436b21cae1de7ee34c55ca`.
- Run ledger:
  `c58b895f5de4ceaa52d66c9727d7e904b72b1ea41d983c48d2c0a191bb16e2fa`.

The exact scoped conclusion is: the completed v6 data are independently
reproducible, but the entire frozen 27-dimensional space lies strictly below
the crossing threshold.  This attempt cannot support a theorem promotion.
