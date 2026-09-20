from __future__ import annotations

import json
from pathlib import Path

import mne
import numpy as np
import pytest
from cnd_mne import read_cnd, validate_cnd
from conftest import synthetic_raw, write_test_recipe
from jsonschema import Draft202012Validator

from neurodata_cnd.analysis_check import check_cnsp_trf_compatibility
from neurodata_cnd.pipeline import convert_recipe
from neurodata_cnd.recipe import RecipeError, load_recipe


def test_fixed_pipeline_guarantees_cannot_be_disabled(tmp_path: Path) -> None:
    source = tmp_path / "source_raw.fif"
    synthetic_raw().save(source, overwrite=True, verbose="ERROR")
    recipe = write_test_recipe(tmp_path / "recipe.json", source)
    payload = json.loads(recipe.read_text(encoding="utf-8"))
    payload["validation"]["require_round_trip_sample"] = False
    recipe.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(RecipeError, match="fixed pipeline guarantee"):
        load_recipe(recipe)


@pytest.mark.parametrize("status", ["draft", "reviewed", "deprecated"])
def test_only_active_recipes_run_directly(tmp_path: Path, status: str) -> None:
    source = tmp_path / "source_raw.fif"
    synthetic_raw().save(source, overwrite=True, verbose="ERROR")
    recipe = write_test_recipe(tmp_path / "recipe.json", source)
    payload = json.loads(recipe.read_text(encoding="utf-8"))
    payload["status"] = status
    recipe.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="not directly executable"):
        convert_recipe(
            recipe,
            cache_root=tmp_path / "cache",
            output_root=tmp_path / "outputs",
            source_override=source,
        )


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
    assert recording.neural is not None
    locations = recording.neural.channel_locations
    assert locations is not None
    assert [location["labels"] for location in locations] == raw.ch_names
    # Exercise the installed converter through both MATLAB formats: an older
    # dependency silently omitted the spherical and polar coordinate fields.
    for location in locations:
        xyz = [location[key] for key in ("X", "Y", "Z")]
        angles = [location[key] for key in ("sph_theta", "sph_phi", "theta")]
        assert np.isfinite(angles).all()
        assert np.isfinite(location["radius"])
        np.testing.assert_allclose(location["sph_radius"], np.linalg.norm(xyz))
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
    assert len(manifest["source"]["sha256"]) == 64
    assert len(manifest["source"]["snapshot_sha256"]) == 64
    analysis = check_cnsp_trf_compatibility(
        result.neural_path,
        result.stimulus_path,
        feature="a_onset",
        max_samples=500,
    )
    assert analysis.strict_cnd == "pass"
    assert analysis.design_shape == (500, 41)
    assert analysis.response_shape == (500, 2)
    assert analysis.finite_weights


def test_complete_conversion_retains_reviewed_eog_as_external(
    tmp_path: Path,
) -> None:
    raw = synthetic_raw()
    raw.add_channels(
        [
            mne.io.RawArray(
                np.vstack(
                    (
                        np.full(raw.n_times, 4e-6),
                        np.full(raw.n_times, -3e-6),
                    )
                ),
                mne.create_info(["VEOG", "HEOG"], raw.info["sfreq"], ["eog", "eog"]),
                verbose="ERROR",
            )
        ]
    )
    source = tmp_path / "source_raw.fif"
    raw.save(source, overwrite=True, verbose="ERROR")
    recipe = write_test_recipe(tmp_path / "recipe.json", source)
    payload = json.loads(recipe.read_text(encoding="utf-8"))
    payload["selection"].update(
        {
            "channel_type_policy": "eeg_with_external",
            "external_channel_types": ["eog"],
            "external_description": "Test EOG channels",
        }
    )
    payload["output"]["external_unit"] = "V"
    recipe.write_text(json.dumps(payload), encoding="utf-8")

    result = convert_recipe(
        recipe,
        cache_root=tmp_path / "cache",
        output_root=tmp_path / "outputs",
        source_override=source,
    )

    recording = read_cnd(result.neural_path, stimulus_path=result.stimulus_path)
    assert recording.neural is not None
    assert recording.neural.n_channels == 2
    assert recording.neural.external_trials is not None
    assert recording.neural.external_trials[0].shape == (raw.n_times, 2)
    assert recording.neural.external_description == "Test EOG channels"
    from scipy.io import loadmat

    stored = loadmat(result.neural_path, struct_as_record=False)["eeg"][0, 0]
    assert stored.extChan.dtype == object
    assert stored.extChan[0, 0][0, 0].data[0, 0].shape == (raw.n_times, 2)
    stim = loadmat(result.stimulus_path, struct_as_record=False)["stim"][0, 0]
    assert stim.data[0, 0].shape == (raw.n_times, 1)


def test_conversion_preserves_a_separate_stimulus_sampling_rate(
    tmp_path: Path,
) -> None:
    raw = synthetic_raw()
    source = tmp_path / "source_raw.fif"
    raw.save(source, overwrite=True, verbose="ERROR")
    recipe = write_test_recipe(tmp_path / "recipe.json", source)
    payload = json.loads(recipe.read_text(encoding="utf-8"))
    payload["synchronization"]["stimulus_sampling_rate_hz"] = 50.0
    recipe.write_text(json.dumps(payload), encoding="utf-8")

    result = convert_recipe(
        recipe,
        cache_root=tmp_path / "cache",
        output_root=tmp_path / "outputs",
        source_override=source,
    )

    recording = read_cnd(result.neural_path, stimulus_path=result.stimulus_path)
    assert recording.neural is not None
    assert recording.stimulus is not None
    assert recording.neural.sfreq == 100.0
    assert recording.stimulus.sfreq == 50.0
    assert recording.stimulus.features[0][0].shape == (250,)
    report = validate_cnd(recording)
    assert report.is_valid
    assert any(issue.code == "sampling_frequency_mismatch" for issue in report.warnings)


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


@pytest.mark.parametrize(
    "max_samples,lag_max_ms,message",
    [(40, 10, "predictor variation"), (60, 1000, "lags must be shorter")],
)
def test_analysis_rejects_unusable_windows(tmp_path, max_samples, lag_max_ms, message):
    source = tmp_path / "source_raw.fif"
    synthetic_raw().save(source, overwrite=True, verbose="ERROR")
    recipe = write_test_recipe(tmp_path / "recipe.json", source)
    result = convert_recipe(
        recipe,
        cache_root=tmp_path / "cache",
        output_root=tmp_path / "outputs",
        source_override=source,
    )
    with pytest.raises(ValueError, match=message):
        check_cnsp_trf_compatibility(
            result.neural_path,
            result.stimulus_path,
            feature="a_onset",
            max_samples=max_samples,
            lag_max_ms=lag_max_ms,
        )
