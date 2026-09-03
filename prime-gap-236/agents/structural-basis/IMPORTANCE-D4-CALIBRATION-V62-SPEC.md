# Exact-whitened D4 calibration v6.2

Status: unfrozen repair candidate only. No production authorization, chain,
sampled quotient, D12 screen, or theorem claim follows from this file.

Frozen v6.1 gate SHA `ff1b6c71...ece83d` is preserved and permanently
unlaunched.  Its exact per-stratum upper bounds closed the v6 `z=1` false
accept, but its final call into the legacy validator still used absolute
`max(1,...)` aggregation and Jensen tolerances.  In common stratum 15 these
tolerances erase valid moments of order `1e-20` and squared moments of order
`1e-41`.

V6.2 retains every v6.1/v6/v5 check and additionally compares raw z means to
batch z means, raw z-second means to batch z-second means, and first to second
moments in both batch and aggregate Jensen inequalities.  Every tolerance is
proportional to the maximum magnitude of the two quantities actually being
compared, plus their own ULPs; it never has a unit floor and never substitutes
the much larger stratum upper bound.  The operation-count factor covers the
sequential raw accumulation and its batch regrouping for both initial and
extended schedules.

The independent v6.1 `AUDIT FAIL` is pinned verbatim: report SHA
`3e86f5b7bcdb3221c8279044cb1c1d9bd06919e1db8f1690fa7d162433fa2d81`,
verifier SHA
`ce527cf6176fe168fd0862be1189bdef0ccccbe96c48bc205327a53c3fbfe69c`,
and tail-moment regression SHA
`339e3620adae4c13bac0a00499740462dd2a3647f821a4246dc7ef32d4d2d4e6`.
The gate remains production-disabled pending a new independent hostile audit
and a separate root authorization.
