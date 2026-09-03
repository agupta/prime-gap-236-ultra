# Frozen exact-whitened importance calibration v6 hostile audit

## Verdict

`AUDIT FAIL`

Production authorization must remain absent.  The exact transform and direct
point-evaluation mathematics are sound, but the serialized J-record validator
does not enforce the new stratum-specific Cauchy bounds on `z` and `z^2`.

The frozen gate audited here is
`d7ab62d01cc873e732857f1662d40af53624aa1fe36abaaf58bacbe03729521b`.
It states `production_launch_authorized: false`; this audit created no
authorization or production directory and did not inspect any future
production output.

## Smallest counterexample

Start from the deterministic tiny-smoke record for target J, common stratum 0,
replicate 0 (`expected_chain_table()[64]`).  The exact-whitened constant
weights give

```text
z_bound       = (1/128)^2 + (1/32)^2 = 0.00103759765625
z_second_bound = z_bound^2            = 1.0766088962554932e-06
```

Mutate only two serialized fields:

1. Set `batch_z_second_means[0]` to the canonical float hex encoding of
   `2*z_bound^2 = 2.1532177925109863e-06`.
2. Recompute `raw_second_sum[-1]` as
   `samples_per_batch * fsum(batch_z_second_means)` so raw/batch aggregation
   remains exact to the validator's tolerance.

Frozen v6 `validate_chain_record(...)` returns `True`.  This is impossible for
any retained point, because `0 <= z <= z_bound` implies
`z^2 <= z_bound^2`, and hence the mean of `z^2` in every batch obeys the same
bound.

This counterexample leaves every J numerator batch, every `z` batch mean,
every raw mean, every reconstructed matrix and ratio, z precision, R-hat, and
all generalized roots unchanged.  The only statistical effect of its larger
raw second moment is to increase (and eventually cap) the reported ESS.  Thus
the later matrix/oracle gates do not close this corruption class.

The defect is at the v6 dispatch boundary: I records receive the new
transform-derived signed-moment validation, while J records are sent directly
to the saved v5 validator.  The v5 validator knows only the legacy universal
`z <= 2`, `z^2 <= 4` bounds, not the v6 bound determined by the record's common
stratum and exact base weights.

Permanent reproducer:

- `agents/audit/test_importance_d4_calibration_v6_j_bounds.py`
- SHA-256
  `b278c5a78513e2e5ed017cdff873a519cef44c40a49ed1e076b32dfae41edc3d`

It deliberately fails against v6 in both normal and optimized Python because
the expected `ArithmeticError` is not raised.  A repaired successor should
make it pass.  The repair must bind the stratum label/index before deriving
the allowed constants and validate, at minimum, every J batch `z` mean against
`z_bound`, every J batch second mean against `z_bound^2`, and the corresponding
raw mean/second aggregates and Jensen relations before legacy validation.

## Dependency-by-dependency findings

### Frozen bytes and provenance

All 33 source hashes and all four data hashes in the gate match the live bytes.
The principal frozen objects match:

| Object | SHA-256 |
|---|---|
| v6 gate | `d7ab62d01cc873e732857f1662d40af53624aa1fe36abaaf58bacbe03729521b` |
| gate builder | `96e908fe7bf29e117a2d7919023d8c443618a4e85472cb9869fdd3178e5ed344` |
| v6 driver | `26cc965edcefaef939a692729f11ccc51e76252c4c1877a2f9c8027e5007cfb1` |
| whitening | `fcbc7068c7e5648601316e043c2ecb9b50bc3324c8f3b576618eb04250ba7901` |
| envelope | `741dc672228021d5e67e847c911cf3b19a7f70b4f908e600304c92569c8164ee` |
| v6 calibration tests | `39a267795154e52c2c8c407ef94be4adffbe2be0758f0d00adca3a965331fa4e` |
| whitening tests | `30fcc951164d1d40a395478f21692ade1372bb8be72849488751f07e3e816430` |
| v6 spec | `5cd72aefe0a49ec5b867043d31f7eb48f023e707d3114e3cad51fe7046987de5` |
| rank postmortem | `62e0a032383a8124377dcb7ce144b88cdc5414b489b00d239e431523600d4987` |
| postmortem tests | `dde27f36949b54888ef9d0352f79f534a0ae2dc10df2255d80e54d7e7290f69f` |
| superseded v5 gate | `860a9a51284187388e2384b7ca19615dc7d17eb523a7a4fa4d5617e2e6f29196` |
| exact D4 quadratic oracle | `fbc8c38d2cf4241fdba03beb4251e2692e96af01ad4918c9a3a1075af2ed6e86` |
| fixed D4 vector | `2b11a18c697e9a2be61204b5493bf7a235ce4add39d853bbb4d76ef31fb4666b` |
| stratum normalizers | `96e0655e0ace238cc561aa654d1facb8ac1e93257835f3ad174efef42d09d42e` |

The gate has an exact key set, byte-pins the v5 gate it supersedes, retains the
frozen 128-chain schedule/threshold/extension schema, and is production
disabled.  The driver requires a separately byte/inode-bound authorization
and fresh held-directory checkpoints for production; no authorization is
shipped.

### Exact LDL, orientation, rank, and base reconstruction

An independent `Fraction` implementation parsed the primary exact moment
artifact directly, rebuilt normalized A and factor-48 B, performed its own
unpivoted LDL and triangular solve, and obtained the exact canonical transform
SHA-256
`f2a0e8325809956c6883191d04cde6bc67ea74c4af34f86dce7a1ac60c4ac1fb`.

It verified `A=L D L^T`, `L^T T=S`, and the correct orientation
`T^T A T=S D S` exactly.  The deliberately reversed orientation differs.  All
93 exact-active pivots are positive; scaled pivots range from
`1.0067330611129017` to `3.982032130771286`, inside `[1,4)`.  Stratum 0 retains
channels `(1,Z,Z^2)` and all other strata retain six channels.  Every nonzero
transform entry is within one stratum and has input degree no greater than
output degree, giving the complete nested active dimensions `16/47/93`.

The independent weights satisfy `T*w=c0` exactly.  Both normalized congruent
forms evaluate to exactly one under `w`.  The producer transform, base weights,
transformed A, and transformed B agree entry-for-entry with the independent
construction.

### Direct point/marginal evaluation

For all 16 I strata, direct formula evaluation of the old `(L,Z)` channels
followed pointwise by the independently reconstructed `T^T` equals the adapter
output bit-for-bit; the maximum absolute discrepancy is zero.

For all 16 common-J strata, an independent polynomial-in-the-distinguished-
coordinate calculation was built directly from the 12 exact D4 basis labels
and vector coefficients.  It integrated the small and large branches and only
then applied `T^T`; no aggregated matrix was transformed.  The maximum
scale-relative discrepancy from the runtime marginal vector is
`2.8297225067907106e-12`, and physical `m0` recombination differs by at most
`2.294327694733049e-12`, consistent with the different floating evaluation
orders.  Support is confined to the current/next blocks.  Substituting the
legacy unweighted envelope is detected by its `m0` reconstruction guard.

### Weights, factor 48, and envelope

The Decimal denominator, numerator, and quotient agree with the independently
parsed exact `I0`, factor-48 `B0`, and `B0/I0` to better than `1e-110`.  All 16
I base masses reconstruct both before and after congruence; the I and common-J
stratum lists reconstruct their respective base forms and are positive.

At directly evaluated points in every common stratum, the v6 envelope has at
most two nonzero tagged constants, reconstructs physical `m0`, obeys its local
Cauchy bound, and has global maximum `z_bound = 0.125 < 2`.  The runtime
point-level envelope is sound.  The failure is specifically loss of this
stronger invariant when J sufficient statistics are serialized/reopened.

### Signed I and inherited v5 closure

The signed-I validator checks all 21 local upper entries' batch means, batch
second moments, raw sums, and raw second sums at their transform-derived
absolute scales; it checks raw/batch aggregation, nonnegativity of seconds,
raw and batch Jensen inequalities, and exact zero on inactive stratum-0
coordinates before the affine compatibility map.  Nonfinite/malformed fields,
seed/state/support/stratum binding, acceptance arithmetic, structural masks,
zero-SE rules, rank, coverage, jackknife, extension eligibility, checkpoint
O_EXCL publication, dependency rechecks, and directory/inode race defenses are
inherited from the byte-pinned v5 implementation and tests.  No additional
failure was found in those paths.  They do not compensate for the missing v6
J serialized bound.

## Commands and observed outcomes

Independent mathematical/hash/counterexample verifier (both exit 0 and print
the same `"status": "AUDIT FAIL"` payload):

```bash
python3 agents/audit/verify_importance_d4_calibration_v6.py
python3 -O agents/audit/verify_importance_d4_calibration_v6.py
```

Verifier SHA-256:
`b643bd7458e1ecdf3909d33a753fcabe83abbf9305d811d086a5d24030837ce7`.

Frozen v6/whitening/postmortem tests:

```bash
python3 -m unittest agents/structural-basis/tests/test_importance_whitening_v6.py agents/structural-basis/tests/test_importance_d4_calibration_v6.py agents/structural-basis/tests/test_importance_d4_rank_postmortem.py
python3 -O -m unittest agents/structural-basis/tests/test_importance_whitening_v6.py agents/structural-basis/tests/test_importance_d4_calibration_v6.py agents/structural-basis/tests/test_importance_d4_rank_postmortem.py
```

Observed: 17 tests pass in each mode (`106.928s`, `105.155s`).  This demonstrates
that the frozen producer suite misses the counterexample.

Inherited calibration/hostile tests:

```bash
python3 -m unittest agents/structural-basis/tests/test_importance_d4_calibration.py agents/structural-basis/tests/test_importance_hostile_crosscheck.py
python3 -O -m unittest agents/structural-basis/tests/test_importance_d4_calibration.py agents/structural-basis/tests/test_importance_hostile_crosscheck.py
```

Observed: 22 tests pass in each mode (`7.059s`, `5.854s`).

New fail-closed regression:

```bash
python3 -m unittest agents/audit/test_importance_d4_calibration_v6_j_bounds.py
python3 -O -m unittest agents/audit/test_importance_d4_calibration_v6_j_bounds.py
```

Observed in both modes: one failure,
`AssertionError: ArithmeticError not raised`.  This failure is the intended
v6 counterexample, not test flakiness.

## Launch consequence

Do not authorize the frozen v6 package.  A successor must add a J-specific
pre-legacy validator keyed by the already validated common stratum, enforce
both first- and second-moment Cauchy bounds (including raw aggregates), add the
permanent mutation above, rebuild and re-pin the gate, and receive a fresh
normal/`-O` hostile audit.
