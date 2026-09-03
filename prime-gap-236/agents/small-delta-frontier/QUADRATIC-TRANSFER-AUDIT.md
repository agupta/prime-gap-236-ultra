# Hostile audit of the C10 degree-two transfer probe

Status: **ARITHMETIC AND PROVENANCE AUDIT PASS; SAFE FOR A D12 DISCOVERY
RUN; OUTPUT IS DELIBERATELY NOT THEOREM-READY**.

## Mathematical path checked

The transferred function is

```text
F(t)=F0(t)*(a_R+b_R L+c_R Z+d_R L^2+e_R LZ+f_R Z^2),
R=#{i:t_i>delta}.
```

The six channels are ordered exactly as
`(1,L,Z,L^2,LZ,Z^2)`.  On an I face with `r` large shared coordinates
and inclusion--exclusion index `h`, the aggregate variables are

```text
L = r*delta + X,
Z = h*delta + Y.
```

The driver forms the complete aggregate multiplier first, squares it once,
and integrates every active face.  Thus its per-r I stage is internal and
end-to-end; no serialized denominator or matrix entry is consumed.

For J, `r` counts large *shared* coordinates.  A small distinguished fiber
uses the coefficient block for total count `r`; its fiber powers enter `Z`.
A large distinguished fiber uses total count `r+1`; its fiber powers enter
`L`.  Zeroth, first, and second fiber moments are inserted with their exact
binomial coefficients before branch squaring.  The lower-triangular branch
loop receives the inherited factor two for unequal branches, and `k=48` is
applied once after summing all common-coordinate faces.  The exact signed
k=3 literal ordered-branch oracle checks these conventions independently.

## Exact and multiprecision calibration

The exact D4 source multiplier is
`results/c10_stratum_quadratic_cappedopt_D4_exact.json`, byte SHA-256
`fbc8c38d2cf4241fdba03beb4251e2692e96af01ad4918c9a3a1075af2ed6e86`.
The fixed D4 polynomial input is byte SHA-256
`2b11a18c697e9a2be61204b5493bf7a235ce4add39d853bbb4d76ef31fb4666b`.
The exact artifact has 96 listed coordinates, 93 independent discovery
coordinates, exact block/direct equality, 312 I faces, and 1,200 J domains.

The repaired direct Decimal100 transfer reconstructs

```text
q = 0.953967438848550778577874658671028262206211491757562896490184875539553765160860...
```

The exact Fraction artifact gives the same quotient with Decimal100
difference `+2.3984250178745458190759106810e-72`.  The transfer independently
reports 20 I orbit groups, 19 marginal components, 312 I faces, and 1,200 J
branch domains.  All gates pass, and the emitted I-stage SHA matches its
post-J byte hash.

## Provenance closure and live mutation test

The frozen transfer driver SHA-256 is
`cd1232cb448fbda9003fab366e9095ffd36913d83ddaeba9e9521d886057b07f`.
It pins and rechecks at the end every local file in its imported arithmetic
closure:

```text
stratum_quadratic.py                62dad8c96005...
stratum_linear.py                   7400369a2e0e...
stratum_amplitude.py                d23d42315d7b...
grouped_fixed_vector.py             47167e92a0f3...
src/exact_integrator.py             941ee82bc72f...
robust_generalized_solve.py         2086244acb67...
run_scheduled_basis.py              06f79a13dbf1...
verify_scheduled_fixed_vector.py    97f36696712f...
```

The last two files are required because the robust solver imports them at
module load; their omission was caught by this audit and repaired before a
D12 launch.  The fixed-polynomial and exact-multiplier files are read once
from required-SHA byte snapshots and rehashed after J.  The internally
written per-r I stage is hashed immediately and rehashed after J.  The driver
source itself and every dependency above are likewise checked start-to-end.

The producer test SHA-256 is
`a708314b1124364b8c7f09773111121ac0f7a13fb0639787056abafeda879408`.
Its three tests pass in normal and optimized Python.  They include exact
per-r versus monolithic signed k=3 arithmetic, required input SHA rejection,
and mutations of the full transitive dependency dictionary.

In an additional live hostile test, the auditor changed one byte of the
emitted D4 I-stage after the `I_STAGE_COMPLETE` marker while J was running.
The process completed the arithmetic but emitted
`status=rejected-transferred-quadratic-candidate`,
`gates_passed=false`, and exited nonzero.  Thus the stage end gate is not
merely metadata.

## Scoped verdict

`AUDIT PASS` for launching the pinned Decimal D12 *discovery* transfer.  The
driver correctly emits `rigorous=false` and `theorem_ready=false`: Decimal
evaluation of one transferred D4 multiplier is neither an exact certificate
nor an optimum over the D12 multiplier space.  A positive sign would still
need an independent exact/outward-rounded reconstruction with pinned inputs.

Regression commands:

```bash
python3 -m unittest prime-gap-236/agents/exact-integrator/tests/test_stratum_quadratic_transfer_decimal.py
python3 -O -m unittest prime-gap-236/agents/exact-integrator/tests/test_stratum_quadratic_transfer_decimal.py
python3 -m unittest prime-gap-236/verify/test_affine_multiplier_oracle.py
python3 -O -m unittest prime-gap-236/verify/test_affine_multiplier_oracle.py
```
