# Six-channel independent dyadic checker: prelaunch audit

Date: 2026-09-02 (Europe/Berlin)

## Status

**SCOPED PRELAUNCH AUDIT PASS.**  The independent checker is implemented,
passes its low-dimensional exact and interval tests, and reproduces both
realistic D4 forms bit-for-bit.  It has **not** been launched on D12.  Launch
is gated on a positive sign from the separate Decimal100 transfer, and a
positive dyadic output would still require an output audit and final analytic
audit.

Frozen inputs currently parsed by the checker are:

- original rational D12 base SHA
  `719c656e6e45388273b4c27f51f7a18b33e9ed1abb5f883e6fcc5de5d6d64a87`;
- integer-scaled D12 base SHA
  `8650e44cace6b6d3e4eee8e1632cfd8a59cde6a48f76a8763dcfb400e49f4a93`;
- exact D4 quadratic multiplier SHA
  `fbc8c38d2cf4241fdba03beb4251e2692e96af01ad4918c9a3a1075af2ed6e86`.

The loader reconstructs the base LCM (714 bits) and multiplier LCM (2310
bits), checks primitive integer content after each global scaling, and obtains
272 base coordinates, 96 serialized multiplier coordinates, and 93 effective
coordinates.  The only discarded coordinates are
`(R,L)=(0,L),(0,L^2),(0,LZ)`, which vanish identically because `L=0` on the
zero-large-coordinate stratum.  No degree cutoff or silent projection is
applied.

## Independently reconstructed algebra

Write

\[
Q_r(L,Z)=a_r+b_rL+c_rZ+d_rL^2+e_rLZ+f_rZ^2.
\]

For `I`, the tagged base square retains each power of the residual slack
`alpha-S`.  On a face with `r` large coordinates and inclusion--exclusion
shift `h`, the checker substitutes exactly

\[
L=r\delta+X,\qquad Z=h\delta+Y,
\]

after convolving all 36 ordered channel pairs in `Q_r^2`.  It then invokes the
same exact two-affine geometry primitive used by the independently audited
capped checker.

For `J`, the distinguished coordinate is integrated before squaring.  On a
small branch the total large count remains `r` and

\[
L_{\rm total}=L,\qquad Z_{\rm total}=Z+t;
\]

on a large branch the total large count is `r+1` and

\[
L_{\rm total}=L+t,\qquad Z_{\rm total}=Z.
\]

Thus only fiber moments `t^0,t^1,t^2` occur.  The implementation expands
`(Z+t)^z` or `(L+t)^l` with exact binomial coefficients, preserves both
fiber-slack and `(1-U)` residual-slack tags, and retains all sixteen ordered
branch intersections separately.  The public J routine returns one `J`; the
driver multiplies it by exactly 48 once and accepts only when

```text
I.lo > 0 and (48*J - I).lo > 0.
```

No eigenvalue, Decimal integral, serialized matrix entry, or persistent
moment cache is read.

## Tests and evidence

The exact tagged recurrence agrees identically with the pre-existing literal
expanded-polynomial oracle for signed six-channel cases at both `k=2` and
`k=3`, in forward and reverse face order.  It also reduces exactly to the
audited capped backend when only the constant channel is one, and its dyadic
version encloses the signed `k=2` literal result.

The realistic D4 calibration reconstructed the exact `I` particular form
bit-for-bit in 46.037205 seconds with 50,800 KiB peak RSS.  Its independent
exact `48J` calibration likewise matched the stored exact form bit-for-bit:

```text
J_SECONDS=3037.074594
M2_BITWISE_EQUAL=True
D4 EXACT FORMS PASS
PEAK_RSS_KIB 296552
```

This is an algebra/calibration result only.  It does not prove that the D12
candidate has positive sign and does not establish numerical optimality.

Normal and optimized Python both pass the four core tests and four driver
tests:

```sh
PYTHONPATH=prime-gap-236 python3 \
  prime-gap-236/agents/small-delta-frontier/test_exact_quadratic_multiplier.py -v
PYTHONPATH=prime-gap-236 python3 -O \
  prime-gap-236/agents/small-delta-frontier/test_exact_quadratic_multiplier.py -v
PYTHONPATH=prime-gap-236 python3 \
  prime-gap-236/agents/small-delta-frontier/test_quadratic_independent_dyadic_driver.py -v
PYTHONPATH=prime-gap-236 python3 -O \
  prime-gap-236/agents/small-delta-frontier/test_quadratic_independent_dyadic_driver.py -v
```

The driver tests include exact reconstruction of both scalings, active-face
counts `(16,16)`, strict interval serialization, Boolean-width and extra-field
rejection, protected-path/stage-binding failures, the single factor 48, and
rejection when the lower margin is exactly zero.

## Prepared command (not authorized until the Decimal sign gate)

The launch is deliberately split so the exact stage bytes can be pinned:

```sh
PYTHONPATH=prime-gap-236 python3 \
  prime-gap-236/verify/check_c10_d12_quadratic_independent_dyadic.py \
  --phase i --precision 512 --shadow-bits 96 \
  --stage prime-gap-236/agents/small-delta-frontier/results/c10_D12_quadratic_independent_dyadic.I-stage.json \
  --output prime-gap-236/agents/small-delta-frontier/results/c10_D12_quadratic_independent_dyadic.json

# Substitute the printed, independently recorded stage SHA below.
PYTHONPATH=prime-gap-236 python3 \
  prime-gap-236/verify/check_c10_d12_quadratic_independent_dyadic.py \
  --phase j --precision 512 --shadow-bits 96 \
  --stage prime-gap-236/agents/small-delta-frontier/results/c10_D12_quadratic_independent_dyadic.I-stage.json \
  --expected-stage-sha256 <PINNED_STAGE_SHA256> \
  --output prime-gap-236/agents/small-delta-frontier/results/c10_D12_quadratic_independent_dyadic.json
```

This is a readiness command only.  It is not a claimed certificate and must
not be run while the Decimal gate is absent or negative.
