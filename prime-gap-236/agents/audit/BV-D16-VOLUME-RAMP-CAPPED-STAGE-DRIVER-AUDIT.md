# BV D16 volume-ramp capped-stage driver audit

## Verdict

**AUDIT PASS for pinned staged Decimal discovery.**  No heavy D16 target stage
was run, and no output of this driver is an exact or interval certificate.

The source is bound to the independently audited analytic volume-ramp support
and piecewise exact base.  It uses the original polynomial (`c_inner=1`) on
the full inner simplex and the naturally dilated polynomial
(`c_outer=3090/3211`) on

```text
scheduled(alpha2) - scheduled(alpha1).
```

The inner/inner exact block uses `eta1=97/400`.  Every computed block involving
the outer shell uses `eta2=3031/12000`.  The outer schedule has exactly active
total counts `0..22`.

An exact low-dimensional oracle with distinct inner/outer coefficient kernels
passes same-support contractions, ordered cross products, count tags, and
decomposition into individual inclusion-exclusion `h` faces.  There is no
hidden factor two in an ordered cross table.

One `HL` table is sufficient, but only with the downstream entry formula

```text
B_shell[R,S] = HH[R,S] + LL[R,S] - HL[R,S] - HL[S,R].
```

Using `HH+LL-2*HL` entrywise is invalid in a count-dependent matrix unless
`HL` happens to be symmetric.  The latter shorthand is safe only after summing
all entries for a uniform outer amplitude.

## Mandatory consumer contract

- pin dilations exactly to `1` and `3090/3211`;
- consume every I total count and J common count in `0..22`;
- require exactly `fh,fl,hh,hl,ll`;
- require `selected_h=null` and `complete_common_count=true`;
- apply the transpose-symmetrized `HL` formula above;
- compare independent 80- and 100-digit Decimal traversals;
- treat the result as discovery until a rigorous exact/interval sign exists.

Any single-`h` cost probe is explicitly incomplete and non-consumable.

## Frozen replay

- driver/tests:
  `cad3e32b77717419061a46d9863e5a99785cf34f71fc5e992f684c3b1741f7f5`
  / `87ed989c9519e8a7890252321f8e15679f010e988400f58959d1f76fb3c416f5`;
- checker:
  `5cc5524bb21363d976ae1702632883569a02b8aec1e94bd1971d682ab7599141`;
- audit result:
  `d3b184da56da7ced37879ff8e9577101fba4d0f29785f224780150ffd117ac6e`.

```bash
cd prime-gap-236
python3 agents/audit/verify_bv_d16_volume_ramp_capped_stage_driver.py
python3 -O agents/audit/verify_bv_d16_volume_ramp_capped_stage_driver.py
python3 -m unittest \
  agents/structural-basis/tests/test_bv_d16_volume_ramp_capped_probe_v1.py
python3 -O -m unittest \
  agents/structural-basis/tests/test_bv_d16_volume_ramp_capped_probe_v1.py
python3 agents/structural-basis/code/bv_d16_volume_ramp_capped_probe_v1.py \
  --preflight-only
```

The checker, seven producer tests, and preflight all pass in normal and `-O`
mode; corresponding outputs are identical.
