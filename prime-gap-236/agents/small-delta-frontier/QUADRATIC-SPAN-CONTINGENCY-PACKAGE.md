# Quadratic-span contingency package

Status: **PRELAUNCH PACKAGE PASS; D4 FALSIFICATION OF `1+Q`; NO D12 H RUN**

Date: 2026-09-02 (Europe/Berlin)

This package is a contingency for the active D12 transfer of the exact
quadratic stratum multiplier `Q`.  It does not assume the sign of that run,
does not launch another transfer, and does not make a rigorous statement from
Decimal arithmetic.

## Frozen files

| role | file | SHA-256 |
|---|---|---|
| exact generic `H=Q+s*1` D4 builder | `build_quadratic_span_contingency.py` | `aa15dd4a8e578ad96edfa3697b138c21ac034010ac8e089515cbed03731e256c` |
| builder hostile tests | `test_build_quadratic_span_contingency.py` | `2a46021d14d591dcce3b6a3ec943d9a7a66dfeeb14db67b5167634e6b3c1bad1` |
| exact D4 span analyzer | `write_quadratic_span_d4_analysis.py` | `c9f80055ff0733eb96915c652048915ad2afdc45703dca80ff98378e238130a7` |
| exact D4 span artifact | `results/c10_D4_constant_Q_span_exact.json` | `ec294139b12512d85f201cf38dff8a8584768be3c29701a11b929ed8e3f3572a` |
| fail-closed Decimal span consumer | `solve_quadratic_span_decimal.py` | `31cf67bbad36b3c8d9ddccd99947e15ddbe671543116e789fb3de5e2f4f0ea6d` |
| consumer hostile tests | `test_solve_quadratic_span_decimal.py` | `2b460f9c87e3eb67046f07c5012c73edf7a799e11d02d76d8d38c7f7916ae536` |

The pinned exact D4 quadratic artifact is
`agents/exact-integrator/results/c10_stratum_quadratic_cappedopt_D4_exact.json`
(SHA `fbc8c38d2cf4241fdba03beb4251e2692e96af01ad4918c9a3a1075af2ed6e86`),
and the pinned D4 vector input is
`agents/exact-integrator/results/c10_capped_D4_decimal55_vector_input.json`
(SHA `2b11a18c697e9a2be61204b5493bf7a235ce4add39d853bbb4d76ef31fb4666b`).

## Exact D4 result

The analyzer reconstructs every one of the 96 quadratic multiplier
coordinates, checks the channel order and the four null labels, and contracts
both the dense I blocks and sparse J entries.  Its exact pencil is the span of
the constant multiplier and `Q`, in the gauge `1+tQ`.  The decimal displays
below are derived only after the exact rational forms have been fixed:

| vector / projective point | quotient |
|---|---:|
| constant multiplier | `0.89636767834278262881161426263062034720281360971680...` |
| `Q` (projective infinity) | `0.95396743884855077857787465867102826220621149175756...` |
| `1+Q` | `0.89637613825112593842922381754071993365265395364865...` |
| span maximum | `0.95396743884855077857787465867592834407108219043012...` |

The maximum occurs at

```text
t = 921910832506237506.993217322167193008151989916848579...
```

in the gauge `1+tQ`.  The exact-span maximum exceeds `Q` alone by only

```text
4.9000818648706986725615136361924661166171853198882e-30.
```

The other stationary point is the minimum
`q=0.85954554184596398090721613005824702015...` at
`t=-5310.047158848413519213117408812389875...`.

Thus `H=1+Q` is concretely falsified as a useful transfer direction at D4.
This is not an upper bound on D12 and does not determine the D12 span.

## Generic exact builder

For an explicitly selected nonzero rational `s`, the builder forms

```text
H = Q + s * 1
```

by adding `s` to each of the sixteen stratum-constant channels.  It then
recomputes the complete D4 forms by a fresh exact direct evaluation; it does
not copy the source artifact's truth flags.  It requires exact agreement with
the independently contracted block/sparse forms and checks 312 I faces and
1200 J branch domains, with the factor 48 inserted exactly once.

No production value of `s` has been selected and no H artifact has been
emitted.  After the Q-only D12 output is complete and only if a contingency is
authorized, the exact D4 build command is:

```sh
python3 agents/small-delta-frontier/build_quadratic_span_contingency.py \
  --source agents/exact-integrator/results/c10_stratum_quadratic_cappedopt_D4_exact.json \
  --expect-source-sha256 fbc8c38d2cf4241fdba03beb4251e2692e96af01ad4918c9a3a1075af2ed6e86 \
  --input agents/exact-integrator/results/c10_capped_D4_decimal55_vector_input.json \
  --expect-input-sha256 2b11a18c697e9a2be61204b5493bf7a235ce4add39d853bbb4d76ef31fb4666b \
  --constant-scale-s S \
  --output agents/exact-integrator/results/c10_stratum_quadratic_Q_plus_s_D4_exact.json
```

`S` must be replaced by an explicit canonical nonzero rational.  It must be
chosen from the completed D12 scale information, not from the D4 optimum.
The fresh D4 direct evaluation is expected to take roughly 3--4 minutes and
about 50 MiB, based on the pinned source run.

## Decimal polarization consumer and trust boundary

If separate D12 Q and H transfers are later available, then in the gauge
`H=Q+s*1` the missing constant--Q cross forms are recovered as

```text
D01 = (DH - D11 - s^2 D00)/(2s),
N01 = (NH - N11 - s^2 N00)/(2s).
```

The consumer validates both transfer outputs, their stages, all counts and
dependency hashes, the exact H coordinate identity, and the factor-48
numerator convention.  It ranks every finite stationary root and infinity,
requiring positive denominators for admitted finite points.

There is no fresh plain-base Decimal100 traversal for the integer-scaled D12
input SHA
`8650e44cace6b6d3e4eee8e1632cfd8a59cde6a48f76a8763dcfb400e49f4a93`.
The only plain-base result is SHA
`02e1a6676a68380592fd272845f7714d583574bd74f73b9a96727171751281d9`,
made from the original input SHA
`719c656e6e45388273b4c27f51f7a18b33e9ed1abb5f883e6fcc5de5d6d64a87`.
The coefficient identity proves mathematical homogeneity by the exact 714-bit
LCM, but separately rounded Decimal100 traversals need not be byte-identical.
Consequently the consumer refuses to run without
`--allow-heuristic-rescaled-base`; when that flag is used it emits
`heuristic_decimal_cross_reconstruction=true`, `theorem_ready=false`, and an
explicit warning.  This mode is discovery-only.

A winning rational multiplier must be evaluated afresh by exact or directed-
interval recurrence.  Neither the Decimal polarization nor this prelaunch
package is a sieve certificate.

## Tests

```sh
python3 agents/small-delta-frontier/test_build_quadratic_span_contingency.py
python3 -O agents/small-delta-frontier/test_build_quadratic_span_contingency.py
python3 agents/small-delta-frontier/test_solve_quadratic_span_decimal.py
python3 -O agents/small-delta-frontier/test_solve_quadratic_span_decimal.py
```

The builder suite passes 4/4 in both modes and covers channel order, null
labels, input/source mutations, a deliberately omitted factor 48, forbidden
zero `s`, output aliasing, and O_EXCL reservation.  The consumer suite passes
5/5 in both modes and covers exact polarization, factor 48, output/stage
mutation, multiplier/source mismatch, and mandatory heuristic opt-in.

