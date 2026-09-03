# Piecewise D16, outer count 15: exact-I calibration and J cost gate

Date: 2026-09-03

## Scope and verdict

This is a deliberately narrow calibration for the analytically audited wide
C722 two-band support.  The inner coordinate is the original BV D16
polynomial and the outer coordinate is its natural dilation, restricted to
the capped shell and total large-coordinate count `R=15`.

The complete Decimal80 denominator stage was reconstructed.  One and only
one representative filtered marginal face was then evaluated to measure the
cost of the corresponding J calculation.  No complete J form, quotient, or
sieve certificate was produced.  Independent MCMC results for this count are
unstable/negative and are not used mathematically.

The volume-ramp schedule used in these calibration stages has since been
strictly superseded for future searches by a frontier schedule.  These stages
are therefore retained only as source-bound arithmetic and cost regressions.

## Frozen arithmetic

- staged target: `piecewise_d16_capped_target.py`, SHA
  `cb84d4eb6d24c7be2315b8195b8e0c1a6a9bc52e68e4e5f6a656ea41252e667c`;
- target tests: SHA
  `7fbbeb2b548f00189da774347052d1140392b59e64b50a71772a867b02a8c08e`,
  5/5 in normal and optimized modes;
- specialized count-15 marginal evaluator:
  `piecewise_d16_R15_specialized.py`, SHA
  `5086a4a381d301ae3a5b321f5e5afba685b677d6851694ef555f6ec76d7fdc58`;
- specialized tests: SHA
  `20caf2130d94a5380cba30e891cf94a4dcd3517f7bea4f940149f7b697d011ef`,
  4/4 in normal and optimized modes.

The independent hostile audit reconstructs ten exact low-dimensional tag
checks and passes the branch reduction.  Its report is
`agents/audit/PIECEWISE-D16-R15-FROZEN-TUPLE-AUDIT.md`, SHA
`38738aeccaa5fa70b9d86e431e7e93431d01b1cba29dfe657bfb4315889e51a9`.

## Complete I stage

Artifact:
`results/piecewise_D16_capped_R15_I_decimal80.json`, SHA
`4f493d645c25354ba9218c923ae8bff06d56a5b79cd45dc608c0aa3a4b051abd`.

The fused traversal shares every orbit density between the outer high and low
simplexes.  At Decimal precision 80 it gives

```
I_high = 2.8081782297870083235308820635672879694303642421940342633054987666712661576256593E-155
I_low  = 2.6214192239222542075342168351645109291359530099048844373475837179684563023267895E-155
I_R15  = 1.867590058647541159966652284027770402944112322891498259579150487028098552988698E-156
```

The last line equals `I_high-I_low` under the declared Decimal80 arithmetic.
All 23 high faces and 21 nonempty low faces were traversed.  Wall time was
683.314 s (675.531 s in the I phase), with peak RSS 271,784 KiB.

The first run completed the same arithmetic but failed closed before
publication because a removed vendored dependency name remained in the
protected-path set.  No artifact was created.  The repair deleted that stale
name and added protected-input, successful-O_EXCL, and duplicate-publication
tests before this clean rerun.

## One-face J cost gate

Artifact:
`results/piecewise_D16_R15_J_r14_h10_costprobe_decimal80.json`, SHA
`aafdc239484574e755cb79fbc1de72913994d371f595828aa794c65da0341167`.

This is explicitly incomplete (`selected_h=10`,
`complete_common_count=false`).  For common count 14, only `Ltotal,Lbig`
outer branches were constructed.  The exact retained branch-domain counts
were

```
fh=6, fl=4, hh=2, hl=3, ll=2.
```

The face took 244.030 s and 301,308 KiB peak RSS.  A purely linear
representative-face projection for the 21 faces at common count 14 and 20
faces at common count 15 is 10,005.25 s = 2.78 h.  It is not a conservative
runtime bound because face costs vary.  The full calculation is not
authorized.

## Assembly audit failure

The provisional assembler SHA
`290dc32bf233083ffa52162a4176e0618d6a1fb932d009ca73740d349fe3a363`
must not be used.  It accepted attacker-selected stage bytes whose spoofable
metadata named the correct scripts, and it published with an
`exists()+write_bytes` race.  The hostile fixture and report reproduce both
failures in normal and optimized modes:

- verifier SHA `159d1e4c8a31e8928c6a1574dfe9924d6e68ca677a2739b265c6f0608347ad94`;
- mutation test SHA `cafcf414804a136b85a79b54425a009b093e2dffcb3a9470ffcbf50610657947`;
- audit JSON SHA `0804655c58d2dc1eb97e836eb21222613f232a192743b3d5459149d1d0e32b48`.

Any future consumer must hard-code the completed artifact byte SHAs, validate
the complete parameter/source/filter schemas, rebind inputs after assembly,
and publish through an exclusively held file descriptor.

## Reproduction

```
python3 agents/small-delta-frontier/test_piecewise_d16_capped_target.py
python3 -O agents/small-delta-frontier/test_piecewise_d16_capped_target.py
python3 agents/small-delta-frontier/test_piecewise_d16_R15_specialized.py
python3 -O agents/small-delta-frontier/test_piecewise_d16_R15_specialized.py
sha256sum agents/small-delta-frontier/results/piecewise_D16_capped_R15_I_decimal80.json
sha256sum agents/small-delta-frontier/results/piecewise_D16_R15_J_r14_h10_costprobe_decimal80.json
```

