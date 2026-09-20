"""Run pinned upstream checks on the six converted ERP CORE pilot recordings."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

UPSTREAM_COMMIT = "74d26e5b7ded8eb80f56aa26517b7e73ba4a83a7"
TASK_FEATURES = {"MMN": 2, "N170": 1, "N2pc": 1, "N400": 1, "P3": 1, "flankers": 1}


def matlab_string(value: str | Path) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--upstream", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--engine", choices=["octave", "matlab"], default="octave")
    parser.add_argument(
        "--all-recordings",
        action="store_true",
        help="Validate every <recording>/dataCND directory below --data-root",
    )
    parser.add_argument(
        "--preprocess",
        action="store_true",
        help="Run full configured CNSP preprocessing (MATLAB required)",
    )
    args = parser.parse_args()
    if args.preprocess and args.engine != "matlab":
        parser.error("--preprocess requires --engine matlab")
    executable = shutil.which(args.engine)
    if executable is None:
        parser.error(f"{args.engine} is not installed or not on PATH")
    upstream = args.upstream.resolve()
    revision = subprocess.check_output(
        ["git", "-C", str(upstream), "rev-parse", "HEAD"], text=True
    ).strip()
    if revision != UPSTREAM_COMMIT:
        parser.error(f"Expected upstream revision {UPSTREAM_COMMIT}, found {revision}")
    changes = subprocess.check_output(
        ["git", "-C", str(upstream), "status", "--porcelain"], text=True
    ).strip()
    if changes:
        parser.error("Upstream checkout must be unmodified for this check")
    args.output.mkdir(parents=True, exist_ok=True)
    results = []
    script_dir = Path(__file__).resolve().parent
    if args.all_recordings:
        targets = []
        for manifest in sorted(args.data_root.resolve().glob("*/manifest.json")):
            recording_id = manifest.parent.name
            data_dir = manifest.parent / "dataCND"
            match = re.search(r"_task-([^_]+)$", recording_id)
            if match is None or match.group(1) not in TASK_FEATURES:
                parser.error(f"Cannot determine task from {recording_id}")
            task = match.group(1)
            targets.append((recording_id, task, 0, data_dir))
        if not targets:
            parser.error("No <recording>/dataCND directories found below --data-root")
    else:
        targets = [
            (
                task,
                task,
                feature,
                args.data_root.resolve() / f"sub-001_task-{task}" / "dataCND",
            )
            for task, feature in TASK_FEATURES.items()
        ]
    for recording_id, task, feature, data_dir in targets:
        output = args.output.resolve() / f"{recording_id.lower()}-upstream.json"
        function = "check_matlab_cnsp" if args.preprocess else "check_upstream"
        command = (
            f"addpath({matlab_string(script_dir)}); "
            f"{function}({matlab_string(data_dir)},{matlab_string(upstream)},"
            f"{matlab_string(output)},{feature});"
        )
        invocation = (
            [executable, "-batch", command]
            if args.engine == "matlab"
            else [executable, "--no-gui", "--quiet", "--eval", command]
        )
        run = subprocess.run(invocation, capture_output=True, text=True)
        (args.output / f"{recording_id.lower()}.log").write_text(
            run.stdout + run.stderr
        )
        record = {
            "recording_id": recording_id,
            "task": task,
            "engine": args.engine,
            "preprocessing": args.preprocess,
            "upstream_revision": revision,
            "feature_index": feature,
            "exit_code": run.returncode,
        }
        neural_files = list(data_dir.glob("dataSub*.mat"))
        if len(neural_files) != 1:
            parser.error(f"Expected one dataSub*.mat in {data_dir}")
        input_files = (neural_files[0], data_dir / "dataStim.mat")
        record["input_sha256"] = {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in input_files
        }
        if run.returncode == 0:
            record["result"] = json.loads(output.read_text())
        else:
            record["error"] = run.stderr[-4000:]
        results.append(record)
        (args.output / "run-summary.json").write_text(
            json.dumps(results, indent=2) + "\n"
        )
        print(
            f"{recording_id}: {'PASS' if run.returncode == 0 else 'FAIL'}",
            flush=True,
        )
    if any(r["exit_code"] for r in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
