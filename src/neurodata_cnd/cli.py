"""Command-line entry point for reproducible CND builds."""

from __future__ import annotations

import argparse
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
        result = convert_recipe(
            arguments.recipe,
            cache_root=arguments.cache_root,
            output_root=arguments.output_root,
            source_override=arguments.source,
            overwrite=arguments.overwrite,
        )
        payload = asdict(result)
        for key, value in tuple(payload.items()):
            if isinstance(value, Path):
                payload[key] = str(value)
        print(json.dumps(payload, indent=2))
        return 0
    raise RuntimeError(f"Unhandled command {arguments.command!r}")


if __name__ == "__main__":
    raise SystemExit(main())
