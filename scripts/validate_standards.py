from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.standards_checker import load_standards  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="article_standards.yml 스키마 검증")
    parser.add_argument("path", nargs="?", default="spec/article_standards.yml")
    args = parser.parse_args()

    standards = load_standards(args.path)
    common = standards["common"]["must_pass"]
    categories = standards["categories"]

    print(json.dumps({
        "path": args.path,
        "common_must_pass": len(common),
        "categories": sorted(categories.keys()),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
