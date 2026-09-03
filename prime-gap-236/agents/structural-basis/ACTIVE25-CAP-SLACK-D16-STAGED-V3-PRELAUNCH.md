# Active-25 cap-slack/D16 staged v3 prelaunch contract

Status: **PRELAUNCH CANDIDATE — TARGET EXECUTION NOT AUTHORIZED**.

This package follows the independently reviewed v2 pruning decision: all 26
degree-zero count coordinates, plus cap-slack degrees 1 and 2 only at counts
9 through 14. The resulting outer basis has 38 coordinates and is crossed
with the fixed radial D16 inner coordinate. No complete cross, combined
vector, quotient, or theorem value was computed while preparing v3.

## Frozen reviewed inputs

The planner tuple is frozen byte-for-byte at:

| Role | SHA-256 |
|---|---|
| v2 planner source | `cd20a85e51d623476b5433626ec4ce35d242e8a00a5f706db1af05509b59d913` |
| v2 tests | `8f16fdc5a72f8e26ffc5c7b2a0ee5f0e8fc734a4383edeb3a2d414a97df94a1f` |
| v2 specification | `ce965d905274af92a3c64496369ffdb5cd97bf5c75a088432428f5707d032851` |
| v2 disabled artifact | `3a07078ca5b480b0d8d554019b42e05b7fb732a1225d97ff761d5b5231abd31c` |

The independent review tuple is frozen at checker
`881622f7bb8e189f240e76c8a31750ef0fb2db42b1561d9e03e06dc1124348fe`,
result
`bbda024a64b32bca96c76cc7b77917b4779daa3c1c108f3a2ff163200249112d`,
and report
`bf8e3bbfec2c6fe3bec3a9a30a7c6caa26ad6912b93b4082253feb4438e5b17a`.

## Exact one-face gate

The only target-geometry calculation performed for v3 was the required
`(common_r,h)=(10,10)` face. It used the reviewed custom cap marginal and the
established grouped D16 inner-density lift. It also recomputed the same face
through the pinned degree-zero arithmetic core and required exact rational
equality on every count. Eight literal endpoint cases independently cover
degrees 1 and 2 on `Sdelta`, `Stotal`, `Ltotal`, and `Lbig`.

The isolated one-worker process had a 20-second alarm and a 256 MiB
address-space ceiling. Its measurements were:

| Measurement | Value |
|---|---:|
| complete gate process | `9.635075082` seconds |
| 38-coordinate pilot face | `5.156675941` seconds |
| independent degree-zero reference face | `4.434376405` seconds |
| peak RSS | `39,640` KiB |
| external `/usr/bin/time` elapsed | `9.71` seconds |
| exact degree-zero comparison | PASS |
| literal positive-degree cases | 8/8 PASS |

The gate tuple is:

| Role | Path | SHA-256 |
|---|---|---|
| gate source | `agents/structural-basis/code/active25_cap_slack_cross_face_gate_v3.py` | `71d1c028e09cbf3484c8b2a7c37e650f747c479ff71fcebb512dbce05ef974a5` |
| gate tests | `agents/structural-basis/tests/test_active25_cap_slack_cross_face_gate_v3.py` | `0e7b863a096045d20aedba7d16b62edb3110e8b12eb55469cd5d1118cba86cf0` |
| exact gate artifact | `agents/structural-basis/results/active25_cap_slack_d16_cross_face_r10_h10_gate_v3.json` | `54d9bf648679c373ad6de8178e194d05f395f8150990060da187720f92f4adc8` |

The artifact remains `launch_authorized:false`; it is a one-face cost and
arithmetic gate, not a full-run authorization.

## Frozen execution candidate

| Role | Path | SHA-256 |
|---|---|---|
| one-shot producer | `agents/structural-basis/code/active25_cap_slack_cross_staged_v3.py` | `2657f9e008dbfb461c8010216dfe243e0b64d5450382dc4021b22978d0af020c` |
| producer tests | `agents/structural-basis/tests/test_active25_cap_slack_cross_staged_v3.py` | `f75d0fd9ce38d26f0f2ece4ad6022cf827259afa57bbb74894816030b39e771d` |
| conditional assembler | `agents/structural-basis/code/assemble_active25_cap_slack_cross_v3.py` | `1f0414e307927261df3108c38e78d0fa2ceac35a1edb7b9164c1239cfa3aaa6c` |
| assembler tests | `agents/structural-basis/tests/test_assemble_active25_cap_slack_cross_v3.py` | `8a75dca9d721e10c8e2e1f1c1a6ee300878493bae91d38eb47fe76fbc8bf225f` |
| independent-reconstruction design | `agents/audit/ACTIVE25-CAP-SLACK-D16-INDEPENDENT-RECONSTRUCTION-DESIGN-V3.md` | `b0fc8a48ead25f5b9c1eb4c632c4a9a69205bb39e5b538affd66f4ab688069cd` |

The producer and assembler preflights are byte-identical in normal and
optimized Python. The producer suite has six synthetic tests and the assembler
suite has five. Both suites pass in normal and optimized mode. No suite calls
the exact common-r kernel.

## One-shot, no-resume protocol

The arithmetic stage unit is one complete common count `r=0..25`; the 26
stages cover 585 exact faces. A production attempt has exactly two top-level
invocations:

1. Initialize one ledger in an already-existing empty directory. The caller
   externally binds the producer bytes and a singly linked root-authorization
   file. The returned ledger SHA, device, and inode must be recorded outside
   the producer.
2. Supply that external ledger binding to one fresh invocation. It requires
   the exact startup leaf set `{ledger.json}`, computes all 26 common counts in
   order, exclusively publishes each stage, and finally publishes a manifest.

There is no resume, reuse, skip, or partial-prefix CLI. A crash, timeout, extra
leaf, replaced inode, or failed validation abandons the attempt. A new run
requires a new empty directory, authorization, and ledger.

The producer is sequential and has one worker. Its immutable global deadline
is 7,200 seconds. Every arithmetic child has the lesser of the remaining
global time and a 600-second deadline, plus a 262,144 KiB address-space limit.
Thus neither a shard nor a complete attempt has an unbounded execution path.

Source, authorization, ledger, each stage, and the manifest are rebound by
SHA and inode. Outputs use exclusive creation. The authorization must bind the
fresh absolute record directory, exact producer and gate hashes, one worker,
the global deadline, and the SHA of a future independent prelaunch report.
Only root may create it after that report passes. None exists in this package.

## Conditional assembler scope

The assembler accepts only externally supplied producer, assembler,
authorization, ledger, and manifest bindings. It independently reparses the
frozen D2 cap-shell form, restricts its `I` and `48J` entries to the canonical
38 labels, and emits a sparse 39-dimensional pencil. The inner/cap matrix
entry is `48 * raw_J_cross`, applied once with no extra polarization factor.

The output deliberately has:

```text
contains_vector = false
contains_quotient = false
eigenvalue_optimality_rigorous = false
serialized_stage_arithmetic_conditional = true
independent_arithmetic_reconstruction = false
theorem_ready = false
```

The independent reconstruction design at hash
`b0fc8a48ead25f5b9c1eb4c632c4a9a69205bb39e5b538affd66f4ab688069cd`
requires a new checker to derive all positive-degree endpoint marginals and
recompute every face without importing either staged program. It also requires
an ungrouped oracle sample before any quotient or theorem claim.

## Plausibility screen, not a bound

The completed degree-zero count basis raises the fixed-inner numerical value
from approximately `0.9812858896095555` to `0.9812862324371874`, a gain of
only `3.4282763183846043e-7`; the remaining gap is
`0.018713767562812622`. Matching that gap would require about `54,586.5` times
the observed degree-zero eigenvalue gain, or about `233.6` times its coupling
scale in a perturbative comparison.

The frozen shell-only particular quotients are approximately `0.06838699`
(D0), `0.07092105` (D1), and `0.07134555` (D2), so the added cap-slack modes
are not near-degenerate with the inner value. Across selected counts 9--14,
the frozen diagonal-I square-root ratios relative to degree zero range from
`0.16369` to `0.25361` for degree 1 and from `0.04303` to `0.08520` for
degree 2. On the measured face, dividing the observed cross ratios by these
I scales gives normalized coupling multiples `3.30--3.34` for degree 1 and
`8.11--8.19` for degree 2 at counts 10 and 11.

Even scaling the degree-zero gain quadratically by the largest observed
`8.19097` coupling multiple gives only about `2.3001e-5`, still roughly 814
times below the remaining gap. This deliberately simple screen does not model
all-face aggregation or correlations between the new coordinates. Together
the frozen signals make closing the `~0.0187` deficit implausible, not
impossible: the selected denominator share is explicitly not an upper bound,
and only the independently reviewed full cross can decide the question.

## Permitted validation now

The following commands are preflight or lightweight synthetic validation only:

```text
python3 agents/structural-basis/tests/test_active25_cap_slack_cross_face_gate_v3.py
python3 -O agents/structural-basis/tests/test_active25_cap_slack_cross_face_gate_v3.py
python3 agents/structural-basis/tests/test_active25_cap_slack_cross_staged_v3.py
python3 -O agents/structural-basis/tests/test_active25_cap_slack_cross_staged_v3.py
python3 agents/structural-basis/tests/test_assemble_active25_cap_slack_cross_v3.py
python3 -O agents/structural-basis/tests/test_assemble_active25_cap_slack_cross_v3.py
python3 agents/structural-basis/code/active25_cap_slack_cross_staged_v3.py --preflight-only
python3 agents/structural-basis/code/assemble_active25_cap_slack_cross_v3.py --preflight-only
```

Do not initialize a ledger, invoke a child, run the one-shot producer, or
assemble target records until a byte-specific independent prelaunch PASS and
separate root authorization exist.
