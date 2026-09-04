from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]


def test_all_recipes_match_the_recipe_schema() -> None:
    schema = _load(ROOT / "schemas" / "recipe.schema.json")
    validator = Draft202012Validator(schema)
    for path in sorted((ROOT / "recipes").glob("*.json")):
        errors = sorted(
            validator.iter_errors(_load(path)), key=lambda error: error.path
        )
        assert not errors, f"{path.name}: {errors}"


def test_example_manifest_matches_the_manifest_schema() -> None:
    schema = _load(ROOT / "schemas" / "manifest.schema.json")
    Draft202012Validator(schema).validate(
        _load(ROOT / "manifests" / "example.manifest.json")
    )


def test_all_corpus_recipes_match_the_corpus_schema() -> None:
    schema = _load(ROOT / "schemas" / "corpus-recipe.schema.json")
    validator = Draft202012Validator(schema)
    for path in sorted((ROOT / "corpora").glob("*.json")):
        errors = sorted(
            validator.iter_errors(_load(path)), key=lambda error: error.path
        )
        assert not errors, f"{path.name}: {errors}"


def test_all_committed_plans_match_the_plan_schema() -> None:
    schema = _load(ROOT / "schemas" / "plan.schema.json")
    validator = Draft202012Validator(schema)
    for path in sorted((ROOT / "plans").glob("*.json")):
        errors = sorted(
            validator.iter_errors(_load(path)), key=lambda error: error.path
        )
        assert not errors, f"{path.name}: {errors}"


def _load(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))
