from __future__ import annotations

import json
from pathlib import Path

import pytest

from neurodata_cnd import cli, corpus, pipeline


def test_convert_command_reports_created_files(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    result = pipeline.ConversionResult(
        output_directory=tmp_path / "output",
        neural_path=tmp_path / "output/dataCND/dataSub1.mat",
        stimulus_path=tmp_path / "output/dataCND/dataStim.mat",
        manifest_path=tmp_path / "output/manifest.json",
        source_path=tmp_path / "source.edf",
        source_reused_cache=False,
        n_channels=2,
        n_samples=500,
        n_features=1,
        event_counts={"event": 1},
    )
    monkeypatch.setattr(pipeline, "convert_recipe", lambda *args, **kwargs: result)

    assert cli.main(["convert", "recipe.json"]) == 0
    assert json.loads(capsys.readouterr().out)["n_samples"] == 500


def test_plan_and_status_commands(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        corpus,
        "plan_corpus",
        lambda *args, **kwargs: {
            "recording_count": 2,
            "source_bytes": 100,
            "pilot_recording_ids": ["sub-001"],
        },
    )
    plan = tmp_path / "plan.json"
    assert cli.main(["plan", "corpus.json", "--output", str(plan)]) == 0
    assert json.loads(capsys.readouterr().out)["recording_count"] == 2

    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    (corpus_dir / "summary.json").write_text(
        json.dumps({"status_counts": {"complete": 2}}), encoding="utf-8"
    )
    assert cli.main(["status", str(corpus_dir)]) == 0
    assert json.loads(capsys.readouterr().out)["status_counts"] == {"complete": 2}


@pytest.mark.parametrize(
    ("command", "expected_retry"), [("batch", False), ("retry", True)]
)
def test_batch_commands_forward_retry_mode(
    tmp_path: Path, monkeypatch, capsys, command: str, expected_retry: bool
) -> None:
    calls = []

    def fake_run_batch(*args, **kwargs):
        calls.append(kwargs)
        return {"outcomes": {"completed": 1}, "summary": {"status_counts": {}}}

    monkeypatch.setattr(corpus, "run_batch", fake_run_batch)
    assert cli.main([command, str(tmp_path / "plan.json")]) == 0
    assert calls[0]["retry_failed"] is expected_retry
    assert json.loads(capsys.readouterr().out)["outcomes"] == {"completed": 1}
