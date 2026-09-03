# Hostile audit of the grouped C10 D12 affine dyadic driver

Status: **AUDIT PASS, PRE-LAUNCH SCOPE ONLY; NO TARGET D12 INTEGRATION OR
QUOTIENT HAS BEEN COMPUTED.**

The audited result driver is
`verify/check_c10_d12_affine_dyadic.py`, SHA-256

```text
bf0ad4b3c1288c1d2df67e92f9ebe9e63613b9dcd2892c3f96522217d920677b
```

The producer regression is
`verify/test_c10_d12_affine_dyadic.py`, SHA-256
`4de32d1f15effdf61e1121b6cdcd148a523708515333eeac2ede165e86623fa6`.
The independent hostile suite is
`agents/small-delta-frontier/test_dyadic_driver_audit.py`, SHA-256
`c3f16fabb32c23b0081477a2739ca1b61f2436713e70c4268571e9c4d588fce7`.

## Exact input reconstruction

The first audited revision merely trusted the integer artifact's claim that
it was an LCM scaling of the original vector.  The smallest counterexample
was a separately byte-pinned integer artifact with one changed integer but
the same claimed source SHA and LCM metadata.  That revision would accept the
unrelated integer vector.  It is retracted.

The current driver instead reads and pins both files:

```text
original D12 source SHA  719c656e6e45388273b4c27f51f7a18b33e9ed1abb5f883e6fcc5de5d6d64a87
integer-scaled file SHA  8650e44cace6b6d3e4eee8e1632cfd8a59cde6a48f76a8763dcfb400e49f4a93
ordered payload SHA      8ea54de0e3bb4d9f978fee80a6788c81d542a7d6839ed8c69e22a5374845fe4e
```

It reconstructs all 272 ordered labels and rational coefficients, recomputes
the positive 714-bit LCM

```text
50000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000
```

and checks coefficient by coefficient that the integer input is exactly this
multiple of the source.  It also checks primitive integer content.  The
cutoff-11 affine table is parsed by the independently tested strict parser;
all retained constants and effective L/Z coefficients become integers after
multiplication by the positive 206-bit LCM

```text
100608472057547700406782448767158942943016780835590106744094720.
```

Both scalings multiply the whole function by one positive constant, so I and
48J acquire the same positive square factor.  The quotient and the sign of
`48J-I` are unchanged.

The driver pins and checks at start and end the complete local arithmetic
closure: the dyadic ring and installer, exact integrator, grouped evaluator,
stratum amplitude/linear/transfer modules, exact affine parser, and capped
certificate primitives.  The original source, integer source, affine input,
driver, and emitted I stage are also reread after their respective phases.

## Direct I identity

On an inclusion--exclusion face with `r` large coordinates and `h` shifted
small coordinates, the grouped base polynomial is exactly the face density
of `F0^2`.  The multiplier polynomial inserted before integration is

```text
a_r + b_r (r*delta + X) + c_r (h*delta + Y).
```

The driver squares this polynomial and multiplies it by the grouped `F0^2`
face integrand before the exact support-domain traversal.  It therefore
computes I directly; it does not contract a staged matrix.  The target count
range is `r=0,...,15`; its exact face count is

```text
sum_{r=0}^{15} (27-r) = 312,
```

and the squared residual/orbit grouping has exactly 1,575 nonempty orbit
groups.  Both counts are mandatory gates.

## J branches, factor two, and factor 48

For a common count `r`, a small distinguished fiber uses multiplier count
`r`; its first fiber moment is added only to Z.  A large distinguished fiber
uses count `r+1`; its first fiber moment is added only to L.  Thus the branch
marginals are the literal grouped versions of

```text
small: (a_r + b_r L_shared + c_r Z_shared) M0 + c_r M1,
large: (a_{r+1} + b_{r+1} L_shared + c_{r+1} Z_shared) M0 + b_{r+1} M1.
```

The four fiber branches are disjoint up to null boundaries.  The inherited
unordered branch loop visits a same-branch square once.  For two distinct
branches, `branch_orbit_product` supplies the factor two representing the two
orders in the square.  Inside one branch, distinct orbit-component products
also receive their own factor two exactly once.  No further symmetry factor
is applied by the result driver.

An exact rational constant-density enumeration, independent of the candidate
coefficients, gives these positive-measure unordered branch-domain counts by
common `r`:

```text
102, 99, 94, 91, 88, 85, 82, 79,
76, 73, 70, 67, 64, 61, 58, 11,
```

whose sum is exactly 1,200.  The target marginal decomposition has 695
components.  Both values are mandatory end gates.  A direct wrapper mutation
test feeds one common-count value `J=7` through the actual method at `k=48`
and obtains the exact singleton `48J=336`, confirming that the target factor
48 is applied exactly once.

## Interval and stage checks

The fixed-point ring stores `[lo/2^P,hi/2^P]` with integer-directed outward
rounding.  Its separate hostile audit is
`agents/small-delta-frontier/DYADIC-INTERVAL-AUDIT.md`, SHA-256
`085f39c2b8853a5732cf1c062257e12f3c7e413a18fca6b317a17249c7f02d60`.
The frozen ring/backend SHAs used here are respectively
`f6f1730f77ba490f04326338e7b3bfe5ab2e5c6438f10892bdf3f5bfe6fc875d`
and
`1dae20016b5fcbde5f56cf222ce92b45899f14bd5ff07fd3c70b7b10ce4ce608`.

Each staged/result interval records the precision, signed endpoint integers,
their canonical rational renderings, and the exact integer width.  Resume
requires the lowercase byte SHA of the complete I-stage file and its exact
field set.  Tests reject extra or missing fields, a Boolean width, a changed
width, noncanonical endpoint integers, changed endpoint fractions, wrong
precision, reversed bounds, and a nonpositive I lower endpoint.  Forward and
reverse count orders have distinct staged metadata.  The reverse mode really
reverses both I and J count lists and, on signed low-k cases, encloses the same
independent exact values.

Stage/output paths must differ and may not resolve to the driver, either D12
input, the affine input, or any pinned arithmetic dependency.  Every such
collision is mutation-tested.  Precision is restricted to 256--4096 bits and
exact-shadow size to 32--512 bits.

## Theorem gate

The only numerical success test is

```text
I.lo > 0  and  (48J-I).lo > 0.
```

Neither a midpoint, upper endpoint, quotient display, nor an assumed
positive-definite matrix is used.  An adversarial test with
`I=[2,2]` and `48J=[2,3]` is rejected: although the quotient upper endpoint
exceeds one, the rigorous margin lower endpoint is zero.  The result artifact
always records endpoint integers and widths.  It also keeps
`theorem_ready=false` pending an independent output audit and the final
analytic proof audit.

## Executed tests

The producer's signed k=3 direct grouped I/J calculation encloses the
independent literal expanded-polynomial oracle in forward and reverse count
orders.  The independent suite adds four deterministic signed k=2/k=3 cases,
the target-k factor test, all source-scaling mutations above, interval/stage
mutations, protected-path mutations, and positive/nonpositive/straddling
output gates.  All tests pass in normal and optimized modes:

```bash
PYTHONPATH=prime-gap-236 python3 -m unittest \
  prime-gap-236/verify/test_c10_d12_affine_dyadic.py
PYTHONPATH=prime-gap-236 python3 -O -m unittest \
  prime-gap-236/verify/test_c10_d12_affine_dyadic.py
PYTHONPATH=prime-gap-236 python3 -m unittest \
  prime-gap-236/agents/small-delta-frontier/test_dyadic_driver_audit.py
PYTHONPATH=prime-gap-236 python3 -O -m unittest \
  prime-gap-236/agents/small-delta-frontier/test_dyadic_driver_audit.py
```

## Exact limitations

1. No C10 D12 phase has been launched under this driver, so this audit proves
   no target quotient or margin.
2. A byte SHA makes a resumed I stage immutable; it does not by itself prove
   that an arbitrary caller-supplied stage was produced by phase I.  A final
   standalone theorem check must run `--phase all` or independently
   reconstruct I rather than treating a supplied stage hash as mathematical
   authentication.
3. This driver checks one fixed transferred affine candidate, not the optimum
   of an affine or higher-degree space.
4. The grouped driver and discovery code share the pinned grouped geometry
   implementation.  Low-k literal-oracle containment is independent, but a
   positive target output still requires a second reconstruction and hostile
   output audit.
5. Insufficient interval precision or an indeterminate support comparison can
   only make the run fail closed; it is not evidence for either sign.

Subject to these explicit pre-launch limitations, the current parser,
provenance closure, direct I/J formulas, interval serialization, traversal
counts, and sign gate receive **AUDIT PASS**.
