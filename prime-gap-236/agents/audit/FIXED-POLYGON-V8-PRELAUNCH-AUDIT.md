# Fixed-polygon v8 hostile prelaunch audit

## Verdict

**FATAL PRELAUNCH FAILURE.  DO NOT LAUNCH OR INHERIT A PASS.**

The smallest counterexample is an ordinary hash-pinned invocation of the
frozen runner at `common-r=0`.  It exits before `v2.build` with

```text
AttributeError: 'PosixPath' object has no attribute '_polygon_monomial_batch'
```

and publishes no result.

## Frozen bytes tested

```text
fixed polygon core
4100a9eeb86563ae84bf02ed4df9a2a5b696b5cc9ff163d15ac482b242b637bb

core tests
165bacf0b02778e35151327112832898f6c40870ac68d8de3d349ac52e6ffd36

runner
649c50273dce8de9dce04014eb602f41a3ed005ed2593f5b89f15ad3196d9e79

latest checker seen during audit
59c45bff37148701065a54fd9c43cf54804d6b9506130f197037dec73ca22542

latest checker tests seen during audit
7dad9c27443806359ce40833941b89ee8f52f7eebf5d0832978c484f169d3860
```

## Root cause

The runner loads the base v1 module as `base`.  In that module, `RADIAL` is
the filesystem path of `verify/exact_capped_certificate.py`; it is not the
freshly imported radial module.  Runner line 144 nevertheless executes

```python
base.RADIAL._polygon_monomial_batch = \
    fixed_moments.polygon_monomial_batch_fixed
```

Setting an attribute on this `PosixPath` raises immediately.  The actual
radial module used by `v2.build` is imported later inside the inherited build
path, so the intended substitution is not merely pointed at the wrong alias:
no replacement reaches the computation at all.

## Exact reproduction

The independent reproducer is

```text
agents/audit/reproduce_fixed_polygon_v8_runner_failure.py
2a53a1e74d9f94ec82002cda6a706a8e9c4b82849d1a1ad0beb5639d47a7262a
```

It checks the runner hash, starts a fresh isolated interpreter, requires the
exact `AttributeError`, and requires the intended output to remain absent.
It passes in both normal and optimized modes, thereby reproducing the failure
rather than testing a mock.

```bash
cd prime-gap-236
python3 -B -I -X pycache_prefix=/tmp/v8-failure-normal \
  agents/audit/reproduce_fixed_polygon_v8_runner_failure.py
python3 -B -O -I -X pycache_prefix=/tmp/v8-failure-opt \
  agents/audit/reproduce_fixed_polygon_v8_runner_failure.py
```

The direct minimal invocation is

```bash
python3 -B -I -X pycache_prefix=/tmp/v8-direct-cache \
  agents/exact-projection-engine/d14_grid38_scaled_b_shard_fixed_polygon_v8.py \
  --common-r 0 --output /tmp/v8-direct-r00.json \
  --expected-self-sha256 \
  649c50273dce8de9dce04014eb602f41a3ed005ed2593f5b89f15ad3196d9e79
```

Observed exit status is `1`; `/tmp/v8-direct-r00.json` is absent.

## Secondary test defect

The latest checker-test snapshot uses three bare Python `assert` statements
for all successful reference-result checks.  Python `-O` removes those
statements, so its advertised optimized-mode run does not check reference
equality, factor-48 recombination, or the denominator-proof flag.  This is
not the cause of the runner crash, but it independently invalidates the
claimed optimized-mode coverage.  A repair should use explicit exceptions
or `unittest` assertions.

## Repair and reaudit gate

A successor must patch the exact freshly loaded radial module that
`v2.build` will use, with restoration or process-local isolation made
explicit.  Its tests must invoke the real runner at least through entry into
the build path, rather than only test the polygon helper and synthetic result
normalization.  Every changed runner/checker/test hash requires a fresh
audit of:

- the substitution target and source snapshot closure;
- exact equality of the replacement to an independent polygon-moment oracle
  on every target domain shape and the full target degree range;
- zero-dimensional/empty domains, orientation, triangulation, and the
  common denominator `L^(E+2)(E+2)!`;
- target result schema and optional same-count v7 equality;
- normal and optimized execution under a private empty bytecode cache.

No claim about the mathematical core is promoted while the only frozen
runner cannot execute.
