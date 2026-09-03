# D4 importance calibration v6.7 records-only recovery

Status: implementation candidate, not authorized and not yet independently
audited.  No chain may be launched through this package.

The frozen v6.6 run created and validated all 128 fresh checkpoint files, but
failed while serializing its final analysis.  Python reports the rejected type
as `bool`; it is specifically a `numpy.bool_`, which is neither a builtin
`bool` nor a NumPy integer and was omitted from the legacy `_json_safe`
dispatch.

`code/importance_d4_calibration_v67_recover.py` is a records-only successor.
It has no chain-execution branch.  Before opening a checkpoint it requires an
external expected source SHA and a separately generated recovery authorization.
The authorization binds:

- the complete v6.7 source/test/spec/audit closure;
- the original v6.6 gate and root authorization;
- the exact v6.6 rejection sentinel;
- the held record-directory device/inode and all 128 ordered checkpoint
  paths, SHA-256 digests, devices, and inodes; and
- one fresh output leaf beneath one held output-parent directory inode.

The recovery reopens every checkpoint through the held record-directory file
descriptor, reruns the frozen v6.6 record validator and full analysis, lists
the exact analysis paths containing NumPy Boolean scalars, and requires the
repair surface to be exactly
`$.hard_gates.constant_coordinate_sums_one`.  (The comparison inherits a
NumPy epsilon scalar, so Python's `and` returns `numpy.bool_`.)  It converts
only that scalar type to builtin booleans and uses the inherited
O_EXCL/held-dirfd publisher.  A fresh standalone interpreter is mandatory;
preloaded local importance modules are rejected, and every loaded module's
canonical file and bytes are rebound to the original gate.
Every original dependency, source, authorization, directory, and checkpoint is
rebound during publication.  The original records and rejection sentinel are
read-only and never overwritten.

The authorization builder defaults to `authorized=false`; a future explicit
root invocation with `--authorize` is required after independent audit.  Even
an accepted recovered calibration remains a nonrigorous discovery screen and
requires the predeclared exact reconstruction before any sieve implication.
