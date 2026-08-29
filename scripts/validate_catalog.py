#!/usr/bin/env python3
"""Validate repository JSON metadata without third-party dependencies."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "catalog" / "datasets.json"
JSON_FILES = sorted(
    path
    for directory in ("catalog", "corpora", "recipes", "manifests", "schemas")
    for path in (ROOT / directory).glob("*.json")
)


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def load_json(path: Path):
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"cannot load {path.relative_to(ROOT)}: {exc}")


def valid_http_url(value: object) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def main() -> int:
    for path in JSON_FILES:
        load_json(path)

    catalog = load_json(CATALOG)
    datasets = catalog.get("datasets")
    if not isinstance(datasets, list) or not datasets:
        fail("catalog.datasets must be a non-empty list")

    required = {
        "id",
        "name",
        "url",
        "provider",
        "modalities",
        "access",
        "license",
        "priority",
        "status",
        "scale",
        "tags",
    }
    ids: set[str] = set()
    priorities: set[int] = set()
    for index, dataset in enumerate(datasets):
        label = f"catalog.datasets[{index}]"
        if not isinstance(dataset, dict):
            fail(f"{label} must be an object")
        missing = sorted(required - dataset.keys())
        if missing:
            fail(f"{label} is missing: {', '.join(missing)}")
        dataset_id = dataset["id"]
        if not isinstance(dataset_id, str) or not dataset_id:
            fail(f"{label}.id must be a non-empty string")
        if dataset_id in ids:
            fail(f"duplicate dataset id: {dataset_id}")
        ids.add(dataset_id)
        if not valid_http_url(dataset["url"]):
            fail(f"{label}.url is not an HTTP(S) URL")
        if not isinstance(dataset["modalities"], list) or not dataset["modalities"]:
            fail(f"{label}.modalities must be a non-empty list")
        if not isinstance(dataset["scale"], dict):
            fail(f"{label}.scale must be an object")
        if not isinstance(dataset["tags"], list):
            fail(f"{label}.tags must be a list")
        priority = dataset["priority"]
        if not isinstance(priority, int) or priority < 1:
            fail(f"{label}.priority must be a positive integer")
        if priority in priorities:
            fail(f"duplicate priority: {priority}")
        priorities.add(priority)

    expected = set(range(1, len(datasets) + 1))
    if priorities != expected:
        fail(f"priorities must be contiguous 1..{len(datasets)}")

    print(
        f"Validated {len(datasets)} catalogue entries and {len(JSON_FILES)} JSON files."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
