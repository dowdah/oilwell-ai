#!/usr/bin/env python3
"""Create a shareable manifest without copying raw 3W records into Git."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from oilwell_ml.manifest import build_manifest

parser = argparse.ArgumentParser()
parser.add_argument("data_root", type=Path, help="ignored local directory containing 3W Parquet files")
parser.add_argument("--output", type=Path, default=Path("docs/experiments/3w-manifest.json"))
args = parser.parse_args()
result = build_manifest(args.data_root.resolve(), args.output)
eligible = sum(item["eligible"] for item in result["instances"])
print(f"Wrote {args.output}: {eligible}/{len(result['instances'])} instances satisfy the 7-variable contract.")
