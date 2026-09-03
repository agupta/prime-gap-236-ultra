#!/usr/bin/env python3
"""Delta audit for v3 band trials, reusing the frozen exact v2 math audit.

V3 changes only provenance closure, filenames, generator SHA, and explicit C10
parameters.  The underlying exact P/direction/projective reconstruction is
delegated to the byte-pinned independent Fraction auditor after replacing its
artifact pins with the v3 pins.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
BASE_AUDITOR = HERE / "audit_band_trials_v2.py"
BASE_AUDITOR_SHA = \
    "3b3cd6377c8e2aa5359a05de74c9a067a79e057cdd152ca1eb829bb9fa0623fc"
EXPECTED_PARAMETERS = {
    "alpha": "79247/300000", "delta": "1/100", "eta": "76247/300000",
    "beta1": "3/20", "beta2": "3/20", "beta3plus": "97/625",
}
V3 = {
    "producer": ("code/propose_band_trials.py",
                 "5e999a3727b9922aac986629e6b022b08614cfcd5ab38203b5f1a8e9e806a7bc"),
    "manifest": ("results/c10_D12_band_trials_manifest_v3.json",
                 "c16b960004b42e0c66fd2255fd6002eed1cbcf049167fe88f1f18c124e7686e5"),
    "near5": ("results/c10_D12_h12_near_5pct_v3.json",
              "43ba7ad464cc4db70fd8b8ae1152f0aed64d5c888b79af7071c8f2df51b0f816"),
    "near10": ("results/c10_D12_h12_near_10pct_v3.json",
               "e3319cde99820683737d1b4abc9aa61a4e44c40b0cadb73a11d2750555ea782d"),
    "near20": ("results/c10_D12_h12_near_20pct_v3.json",
               "88c1d26f6cf46bbdd12dc000eb802cac8efe91be0ad003d6827f2ccdc6c0ff47"),
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    if sha(BASE_AUDITOR) != BASE_AUDITOR_SHA:
        raise RuntimeError("base exact math auditor SHA mismatch")
    spec = importlib.util.spec_from_file_location("band_trials_exact_audit", BASE_AUDITOR)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    sb = module.SB
    for key, (relative, expected) in V3.items():
        path = sb / relative
        if sha(path) != expected:
            raise RuntimeError(f"v3 {key} SHA mismatch")
        module.PATHS[key] = path
        module.SHAS[key] = expected
    for key in ("near5", "near10", "near20"):
        trial = json.loads(module.PATHS[key].read_bytes())
        if trial.get("parameters") != EXPECTED_PARAMETERS:
            raise RuntimeError(f"v3 explicit parameter mismatch at {key}")
    module.main()
    if sha(BASE_AUDITOR) != BASE_AUDITOR_SHA:
        raise RuntimeError("base exact math auditor changed")
    for key, (_, expected) in V3.items():
        if sha(module.PATHS[key]) != expected:
            raise RuntimeError(f"v3 {key} changed during audit")
    print("V3 FINAL-TRIAL-CLOSURE DELTA AUDIT PASS")


if __name__ == "__main__":
    main()
