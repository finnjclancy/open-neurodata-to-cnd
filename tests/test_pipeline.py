from __future__ import annotations

import json
from pathlib import Path

import pytest
from cnd_mne import read_cnd, validate_cnd
from conftest import synthetic_raw, write_test_recipe
from jsonschema import Draft202012Validator

from neurodata_cnd.pipeline import convert_recipe


@pytest.mark.parametrize("mat_version", ["5", "7.3"])
def test_complete_local_conversion_and_round_trip(
    tmp_path: Path, mat_version: str
) -> None:
    raw = synthetic_raw()
    source = tmp_path / "source_raw.fif"
    raw.save(source, overwrite=True, verbose="ERROR")
    recipe = write_test_recipe(
        tmp_path / "recipe.json", source, mat_version=mat_version
    )

    result = convert_recipe(
        recipe,
        cache_root=tmp_path / "cache",
        output_root=tmp_path / "outputs",
        source_override=source,
    )

    assert result.n_channels == 2
    assert result.n_samples == 500
    assert result.event_counts == {"a_onset": 2, "b_onset": 1}
    recording = read_cnd(result.neural_path, stimulus_path=result.stimulus_path)
    assert validate_cnd(recording, strict_spec=True).is_valid
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    root = Path(__file__).resolve().parents[1]
    schema = json.loads(
        (root / "schemas" / "manifest.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator(schema).validate(manifest)
    assert manifest["validation"]["strict_cnd"] == "pass"
    assert manifest["validation"]["cnd_to_mne"] == "pass"
    assert manifest["contents"]["features"] == ["a_onset", "b_onset"]
    assert len(manifest["contents"]["files"]) == 2
    assert len(manifest["contents"]["canonical_content_sha256"]) == 64


def test_output_is_immutable_by_default(tmp_path: Path) -> None:
    raw = synthetic_raw()
    source = tmp_path / "source_raw.fif"
    raw.save(source, overwrite=True, verbose="ERROR")
    recipe = write_test_recipe(tmp_path / "recipe.json", source)
    options = {
        "cache_root": tmp_path / "cache",
        "output_root": tmp_path / "outputs",
        "source_override": source,
    }
    convert_recipe(recipe, **options)

    with pytest.raises(FileExistsError):
        convert_recipe(recipe, **options)

    assert not list((tmp_path / "outputs" / "synthetic").glob(".*.staging-*"))


def test_canonical_content_is_stable_across_mat_versions(tmp_path: Path) -> None:
    raw = synthetic_raw()
    source = tmp_path / "source_raw.fif"
    raw.save(source, overwrite=True, verbose="ERROR")
    manifests = []
    for mat_version in ("5", "7.3"):
        recipe = write_test_recipe(
            tmp_path / f"recipe-{mat_version}.json",
            source,
            mat_version=mat_version,
        )
        result = convert_recipe(
            recipe,
            cache_root=tmp_path / "cache",
            output_root=tmp_path / "outputs",
            source_override=source,
        )
        manifests.append(json.loads(result.manifest_path.read_text(encoding="utf-8")))

    first = manifests[0]["contents"]["canonical_content_sha256"]
    second = manifests[1]["contents"]["canonical_content_sha256"]
    assert first == second
