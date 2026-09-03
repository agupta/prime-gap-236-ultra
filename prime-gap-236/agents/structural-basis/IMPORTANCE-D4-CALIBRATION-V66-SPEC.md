# Exact-whitened D4 calibration v6.6

Status: repaired, production-disabled prelaunch candidate. No chain, sampled
quotient, D12 screen, exact certificate, or theorem claim follows from this
file.

Frozen v6.5 gate SHA
`5aec092841721a8e54292eb631e43c5e298088960e4031e7528df6272def905a`
is preserved and permanently unlaunched. Its weighted base marginal could be
finite while its square overflowed. The resulting comparison had both
infinite discrepancy and infinite tolerance, so `inf > inf` incorrectly
accepted a forged point.

V6.6 retains every v6--v6.5 record, exact-stratum, raw-total, Jensen,
zero-support, and pre-square-underflow check. Before authenticating a returned
J-envelope `z`, it additionally:

- requires the 96 transformed coordinates and exact tagged weights to have
  their pinned finite binary64 representation;
- locally verifies the unit-coordinate and unit-norm invariants;
- rejects every nonfinite or unresolved tagged product and an overflowing
  `fsum`;
- checks square overflow before multiplication, then requires the square to
  be finite and resolved;
- requires returned `z`, the local 16-ULP tolerance, and the discrepancy all
  to be finite before the final comparison.

Exact signed cancellation of the two allowed tagged constants remains valid.
A nonzero tagged product or weighted marginal that is lost to underflow is
rejected. The smallest normal resolved square remains accepted when embedded
in a valid unit vector.

The independent v6.5 `AUDIT FAIL` is pinned verbatim: report SHA
`6dc014424f5a551b46d086cd8305a535cf905a0f36696fd398866b8d57bb3a80`,
verifier SHA
`5ca07de73cc4f10cabe9cc2d3e61c2c1b7bc0f2088041ba4301ebf834c7d0b7b`,
and overflow regression SHA
`f400f250b6485a4d77f02a346eae319cea3f4283acadf5630d32c5aa873c8ad2`.
The v6.6 gate must remain disabled until a fresh independent normal/`-O`
hostile audit passes and root separately authorizes production.
