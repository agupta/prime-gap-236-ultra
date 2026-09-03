#!/usr/bin/env python3
"""Rank the twenty capped quotient sensitivities from a validated gradient."""

from __future__ import annotations

import argparse
import json
import os
import sys
from decimal import Decimal, getcontext
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from band_line_search import (BandMap, dec, direction_from_gradient,  # noqa: E402
                              load_bound, validate_gradient)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--bands", required=True)
    ap.add_argument("--gradient", required=True)
    ap.add_argument("--precision", type=int, default=230)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    getcontext().prec = args.precision
    band_map = BandMap.from_source_and_bands(args.source, args.bands)
    gradient, gradient_sha = load_bound(args.gradient)
    validate_gradient(gradient, band_map, args.source, args.bands)
    theta, a_theta, b_theta, direction, residual, diagnostics = \
        direction_from_gradient(gradient, band_map, args.precision)
    labels = []
    bands = json.loads(Path(args.bands).read_bytes())
    for item in bands["core"]:
        labels.append(f"G_({item['label'][0]},{item['label'][1]})")
    labels.extend(f"H_{degree}" for degree in sorted(bands["bands"], key=int))
    rows = []
    for i in range(band_map.dimension):
        rows.append({
            "index": i,
            "label": labels[i],
            "theta": str(theta[i]),
            "A_theta": str(a_theta[i]),
            "B_theta": str(b_theta[i]),
            "residual": str(residual[i]),
            "preconditioned_direction": str(direction[i]),
            "residual_direction_contribution": str(residual[i] * direction[i]),
        })
    ranking = sorted(range(len(rows)),
                     key=lambda i: abs(Decimal(rows[i][
                         "residual_direction_contribution"])), reverse=True)
    result = {
        "status": "validated-capped-band-sensitivity-report",
        "rigorous": False,
        "gradient_sha256": gradient_sha,
        "quotient": gradient["quotient"],
        "rows": rows,
        "rank_by_abs_residual_direction_contribution": ranking,
        "diagnostics": {key: str(value) for key, value in diagnostics.items()},
        "note": "Discovery sensitivities only; signs and magnitudes are not an exact certificate.",
    }
    Path(args.output).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
