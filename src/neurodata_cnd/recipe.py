"""Load conversion recipes from JSON."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


class RecipeError(ValueError):
    """A conversion recipe is incomplete or internally inconsistent."""


@dataclass(slots=True, frozen=True)
class SourceFileSpec:
    path: str
    url: str
    sha256: str | None = None
    checksum_algorithm: str = "sha256"
    checksum: str | None = None

    @property
    def integrity(self) -> tuple[str, str]:
        """Return the declared checksum algorithm and digest."""
        if self.sha256 is not None:
            return "sha256", self.sha256
        if self.checksum is None:
            raise RecipeError(f"Source file {self.path!r} has no checksum")
        return self.checksum_algorithm, self.checksum


@dataclass(slots=True, frozen=True)
class SourceSpec:
    dataset_id: str
    provider: str
    url: str
    version: str
    files: tuple[SourceFileSpec, ...]
    primary_path: str
    doi: str | None = None


@dataclass(slots=True, frozen=True)
class FeatureSpec:
    name: str
    kind: str
    unit: str
    source_annotation: str | None = None
    source_column: str | None = None
    source_value: str | None = None
    source_values: tuple[str, ...] | None = None
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
    """Load one JSON recipe and check that required fields are present."""
    recipe_path = Path(path).expanduser().resolve()
    with recipe_path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise RecipeError("Recipe root must be a JSON object")

    source_payload = _mapping(payload, "source")
    version = _text(source_payload, "version")
    if source_payload.get("require_pinned_version_before_conversion") and not version:
        raise RecipeError("source.version must be pinned before conversion")
    source_files = _source_files(source_payload)
    primary_path = str(
        source_payload.get("primary_path") or source_files[0].path
    ).strip()
    if primary_path not in {source_file.path for source_file in source_files}:
        raise RecipeError("source.primary_path must identify one declared source file")

    feature_specs: list[FeatureSpec] = []
    raw_features = payload.get("features")
    if not isinstance(raw_features, list) or not raw_features:
        raise RecipeError("features must be a non-empty list")
    for index, feature in enumerate(raw_features):
        if not isinstance(feature, dict):
            raise RecipeError(f"features[{index}] must be an object")
        kind = _text(feature, "kind")
        if kind not in {"annotation_impulse", "bids_event_impulse"}:
            raise RecipeError(
                f"features[{index}].kind={kind!r} is not implemented; "
                "supported: annotation_impulse, bids_event_impulse"
            )
        source_annotation = _optional_text(feature, "source_annotation")
        source_column = _optional_text(feature, "source_column")
        source_value = _optional_text(feature, "source_value")
        raw_source_values = feature.get("source_values")
        source_values: tuple[str, ...] | None = None
        if raw_source_values is not None:
            if (
                not isinstance(raw_source_values, list)
                or not raw_source_values
                or any(
                    not isinstance(value, str) or not value.strip()
                    for value in raw_source_values
                )
            ):
                raise RecipeError(
                    f"features[{index}].source_values must be a non-empty string list"
                )
            source_values = tuple(value.strip() for value in raw_source_values)
            if len(set(source_values)) != len(source_values):
                raise RecipeError(
                    f"features[{index}].source_values must not contain duplicates"
                )
        if source_value is not None and source_values is not None:
            raise RecipeError(
                f"features[{index}] must use source_value or source_values, not both"
            )
        if kind == "annotation_impulse" and source_annotation is None:
            raise RecipeError(
                f"features[{index}] annotation impulses require source_annotation"
            )
        if kind == "bids_event_impulse" and (
            source_column is None or (source_value is None and source_values is None)
        ):
            raise RecipeError(
                f"features[{index}] BIDS impulses require source_column and "
                "source_value or source_values"
            )
        feature_specs.append(
            FeatureSpec(
                name=_text(feature, "name"),
                kind=kind,
                unit=_text(feature, "unit"),
                source_annotation=source_annotation,
                source_column=source_column,
                source_value=source_value,
                source_values=source_values,
                description=_optional_text(feature, "description"),
            )
        )
    names = [feature.name for feature in feature_specs]
    if len(set(names)) != len(names):
        raise RecipeError("Feature names must be unique")
    selectors = [
        (
            feature.kind,
            feature.source_annotation,
            feature.source_column,
            feature.source_value,
            feature.source_values,
        )
        for feature in feature_specs
    ]
    if len(set(selectors)) != len(selectors):
        raise RecipeError("Source event selectors must map to only one feature")

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
            files=source_files,
            primary_path=primary_path,
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


def _source_files(source: dict[str, Any]) -> tuple[SourceFileSpec, ...]:
    raw_files = source.get("files")
    if raw_files is None:
        raw_files = [
            {
                "path": _text(source, "filename"),
                "url": _url(source, "file_url"),
                "sha256": _text(source, "sha256"),
            }
        ]
    if not isinstance(raw_files, list) or not raw_files:
        raise RecipeError("source.files must be a non-empty list")
    files: list[SourceFileSpec] = []
    for index, item in enumerate(raw_files):
        if not isinstance(item, dict):
            raise RecipeError(f"source.files[{index}] must be an object")
        relative_path = _text(item, "path")
        path = Path(relative_path)
        if path.is_absolute() or ".." in path.parts:
            raise RecipeError(
                f"source.files[{index}].path must stay inside the snapshot"
            )
        sha256 = _optional_text(item, "sha256")
        checksum = _optional_text(item, "checksum")
        algorithm = str(item.get("checksum_algorithm", "sha256")).lower()
        if sha256 is not None:
            algorithm = "sha256"
            checksum = sha256
        if checksum is None:
            raise RecipeError(f"source.files[{index}] requires a checksum")
        checksum = checksum.lower()
        expected_length = {"sha256": 64, "git": 40}.get(algorithm)
        if expected_length is None:
            raise RecipeError(
                f"source.files[{index}].checksum_algorithm={algorithm!r} is unsupported"
            )
        if len(checksum) != expected_length or any(
            character not in "0123456789abcdef" for character in checksum
        ):
            raise RecipeError(
                f"source.files[{index}] has an invalid {algorithm} checksum"
            )
        files.append(
            SourceFileSpec(
                path=path.as_posix(),
                url=_url(item, "url"),
                sha256=checksum if algorithm == "sha256" else None,
                checksum_algorithm=algorithm,
                checksum=checksum,
            )
        )
    paths = [item.path for item in files]
    if len(set(paths)) != len(paths):
        raise RecipeError("source file paths must be unique")
    return tuple(files)
