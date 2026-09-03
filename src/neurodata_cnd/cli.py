"""Command-line tools for converting public EEG to CND."""

from __future__ import annotations

import argparse
import importlib.util
import json
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="neurodata-to-cnd")
    subparsers = parser.add_subparsers(dest="command", required=True)
    convert = subparsers.add_parser("convert", help="execute one pinned recipe")
    convert.add_argument("recipe", type=Path)
    convert.add_argument("--cache-root", type=Path, default=Path("cache"))
    convert.add_argument("--output-root", type=Path, default=Path("outputs"))
    convert.add_argument("--source", type=Path, help="verified local source override")
    convert.add_argument("--overwrite", action="store_true")
    plan = subparsers.add_parser("plan", help="create a pinned corpus job plan")
    plan.add_argument("recipe", type=Path)
    plan.add_argument("--output", type=Path, required=True)
    plan.add_argument("--overwrite", action="store_true")
    batch = subparsers.add_parser("batch", help="run resumable corpus jobs")
    batch.add_argument("plan", type=Path)
    batch.add_argument("--cache-root", type=Path, default=Path("cache"))
    batch.add_argument("--output-root", type=Path, default=Path("outputs"))
    batch.add_argument("--recording", action="append", dest="recordings")
    batch.add_argument("--pilot", action="store_true")
    batch.add_argument("--keep-source", action="store_true")
    status = subparsers.add_parser("status", help="show corpus conversion status")
    status.add_argument("corpus_directory", type=Path)
    retry = subparsers.add_parser("retry", help="retry failed corpus jobs")
    retry.add_argument("plan", type=Path)
    retry.add_argument("--cache-root", type=Path, default=Path("cache"))
    retry.add_argument("--output-root", type=Path, default=Path("outputs"))
    retry.add_argument("--keep-source", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    if arguments.command == "convert":
        try:
            from .pipeline import convert_recipe
        except ModuleNotFoundError as error:
            if error.name == "cnd_mne":
                raise SystemExit(
                    "Conversion requires the companion CND-MNE package. "
                    "Install this project with its 'conversion' extra."
                ) from error
            raise
        conversion_result = convert_recipe(
            arguments.recipe,
            cache_root=arguments.cache_root,
            output_root=arguments.output_root,
            source_override=arguments.source,
            overwrite=arguments.overwrite,
        )
        payload = asdict(conversion_result)
        for key, value in tuple(payload.items()):
            if isinstance(value, Path):
                payload[key] = str(value)
        print(json.dumps(payload, indent=2))
        return 0
    if arguments.command == "plan":
        from .corpus import plan_corpus

        plan_result = plan_corpus(
            arguments.recipe, arguments.output, overwrite=arguments.overwrite
        )
        print(
            json.dumps(
                {
                    "plan": str(arguments.output.resolve()),
                    "recording_count": plan_result["recording_count"],
                    "source_bytes": plan_result["source_bytes"],
                    "pilot_recording_ids": plan_result["pilot_recording_ids"],
                },
                indent=2,
            )
        )
        return 0
    if arguments.command in {"batch", "retry"}:
        if importlib.util.find_spec("cnd_mne") is None:
            raise SystemExit(
                "Batch conversion requires the companion CND-MNE package. "
                "Install this project with its 'conversion' extra."
            )
        try:
            from .corpus import run_batch
        except ModuleNotFoundError as error:
            if error.name == "cnd_mne":
                raise SystemExit(
                    "Batch conversion requires the companion CND-MNE package. "
                    "Install this project with its 'conversion' extra."
                ) from error
            raise
        batch_result = run_batch(
            arguments.plan,
            cache_root=arguments.cache_root,
            output_root=arguments.output_root,
            recording_ids=(
                set(arguments.recordings)
                if arguments.command == "batch" and arguments.recordings
                else None
            ),
            pilot=arguments.command == "batch" and arguments.pilot,
            cleanup_source=not arguments.keep_source,
            retry_failed=arguments.command == "retry",
        )
        print(json.dumps(batch_result, indent=2))
        return 1 if batch_result["summary"]["status_counts"].get("failed", 0) else 0
    if arguments.command == "status":
        from .corpus import corpus_status

        print(json.dumps(corpus_status(arguments.corpus_directory), indent=2))
        return 0
    raise RuntimeError(f"Unhandled command {arguments.command!r}")


if __name__ == "__main__":
    raise SystemExit(main())
