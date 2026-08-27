"""Typed access to reviewed JSON conversion recipes."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


class RecipeError(ValueError):
    """A conversion recipe is incomplete or internally inconsistent."""


@dataclass(slots=True, frozen=True)
class SourceSpec:
    dataset_id: str
    provider: str
    url: str
    version: str
    file_url: str
    filename: str
    sha256: str
    doi: str | None = None


@dataclass(slots=True, frozen=True)
class FeatureSpec:
    name: str
    kind: str
    source_annotation: str
    unit: str
    description: str | None = None


@dataclass(slots=True, frozen=True)
class ConversionRecipe:
    path: Path
    recipe_id: str
    recipe_version: str
    status: str
    source: SourceSpec
    selection: dict[str, Any]
    trials: dict[str, Any]
    features: tuple[FeatureSpec, ...]
    synchronization: dict[str, Any]
    output: dict[str, Any]
    validation: dict[str, Any]
    license: dict[str, Any]
    notes: tuple[str, ...]


def load_recipe(path: str | Path) -> ConversionRecipe:
    """Load and perform executable-contract checks on one JSON recipe."""
    recipe_path = Path(path).expanduser().resolve()
    with recipe_path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise RecipeError("Recipe root must be a JSON object")

    source_payload = _mapping(payload, "source")
    version = _text(source_payload, "version")
    if source_payload.get("require_pinned_version_before_conversion") and not version:
        raise RecipeError("source.version must be pinned before conversion")
    file_url = _url(source_payload, "file_url")
    sha256 = _text(source_payload, "sha256").lower()
    if len(sha256) != 64 or any(
        character not in "0123456789abcdef" for character in sha256
    ):
        raise RecipeError("source.sha256 must be a 64-character hexadecimal digest")

    feature_specs: list[FeatureSpec] = []
    raw_features = payload.get("features")
    if not isinstance(raw_features, list) or not raw_features:
        raise RecipeError("features must be a non-empty list")
    for index, feature in enumerate(raw_features):
        if not isinstance(feature, dict):
            raise RecipeError(f"features[{index}] must be an object")
        kind = _text(feature, "kind")
        if kind != "annotation_impulse":
            raise RecipeError(
                f"features[{index}].kind={kind!r} is not implemented; "
                "supported: annotation_impulse"
            )
        feature_specs.append(
            FeatureSpec(
                name=_text(feature, "name"),
                kind=kind,
                source_annotation=_text(feature, "source_annotation"),
                unit=_text(feature, "unit"),
                description=_optional_text(feature, "description"),
            )
        )
    names = [feature.name for feature in feature_specs]
    annotations = [feature.source_annotation for feature in feature_specs]
    if len(set(names)) != len(names):
        raise RecipeError("Feature names must be unique")
    if len(set(annotations)) != len(annotations):
        raise RecipeError("Source annotations must map to only one feature")

    selection = _mapping(payload, "selection")
    if _text(selection, "modality").lower() != "eeg":
        raise RecipeError("The first converter release supports EEG only")
    trials = _mapping(payload, "trials")
    if _text(trials, "unit") != "recording_run":
        raise RecipeError(
            "The first converter release requires one recording_run trial"
        )

    output = _mapping(payload, "output")
    if str(output.get("format")) != "CND 1.0":
        raise RecipeError("output.format must be 'CND 1.0'")
    if str(output.get("mat_version", "5")) not in {"5", "7.3"}:
        raise RecipeError("output.mat_version must be '5' or '7.3'")

    return ConversionRecipe(
        path=recipe_path,
        recipe_id=_text(payload, "recipe_id"),
        recipe_version=_text(payload, "recipe_version"),
        status=_text(payload, "status"),
        source=SourceSpec(
            dataset_id=_text(source_payload, "dataset_id"),
            provider=_text(source_payload, "provider"),
            url=_url(source_payload, "url"),
            version=version,
            file_url=file_url,
            filename=_text(source_payload, "filename"),
            sha256=sha256,
            doi=_optional_text(source_payload, "doi"),
        ),
        selection=selection,
        trials=trials,
        features=tuple(feature_specs),
        synchronization=_mapping(payload, "synchronization"),
        output=output,
        validation=_mapping(payload, "validation"),
        license=_mapping(payload, "license"),
        notes=tuple(str(note) for note in payload.get("notes", ())),
    )


def _mapping(parent: dict[str, Any], key: str) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        raise RecipeError(f"{key} must be an object")
    return dict(value)


def _text(parent: dict[str, Any], key: str) -> str:
    value = parent.get(key)
    if not isinstance(value, str) or not value.strip():
        raise RecipeError(f"{key} must be a non-empty string")
    return value.strip()


def _optional_text(parent: dict[str, Any], key: str) -> str | None:
    value = parent.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise RecipeError(f"{key} must be null or a non-empty string")
    return value.strip()


def _url(parent: dict[str, Any], key: str) -> str:
    value = _text(parent, key)
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise RecipeError(f"{key} must be an HTTP(S) URL")
    return value
