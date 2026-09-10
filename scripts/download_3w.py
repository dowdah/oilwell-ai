#!/usr/bin/env python3
"""Download an explicitly supplied, authorized 3W archive to an ignored path."""
from __future__ import annotations

import argparse
import hashlib
import urllib.request
from pathlib import Path

parser = argparse.ArgumentParser(description="Only use a source URL you are authorized to download.")
parser.add_argument("--source-url", required=True)
parser.add_argument("--output", type=Path, default=Path("ml/data/raw/3w-2.0.0.zip"))
parser.add_argument("--sha256", help="optional expected archive checksum")
args = parser.parse_args()
raw_root = Path("ml/data/raw").resolve()
output = args.output.resolve()
if not output.is_relative_to(raw_root):
    raise SystemExit(f"output must stay under the ignored directory {raw_root}")
output.parent.mkdir(parents=True, exist_ok=True)
partial = output.with_suffix(output.suffix + ".part")
with urllib.request.urlopen(args.source_url) as response, partial.open("wb") as destination:
    while chunk := response.read(1024 * 1024):
        destination.write(chunk)
digest = hashlib.sha256(partial.read_bytes()).hexdigest()
if args.sha256 and digest.lower() != args.sha256.lower():
    partial.unlink()
    raise SystemExit("checksum mismatch; partial archive removed")
partial.replace(output)
print(f"Downloaded {output}\\nsha256={digest}")
