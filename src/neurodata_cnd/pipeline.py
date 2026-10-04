"""Convert one recording, check it, write a manifest."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .output import write_verified_conversion
from .preparation import prepare_conversion
from .publication import staged_directory
from .recipe import ConversionRecipe, load_recipe


@dataclass(slots=True, frozen=True)
class ConversionResult:
    output_directory: Path
    neural_path: Path
    stimulus_path: Path
    manifest_path: Path
    source_path: Path
    source_reused_cache: bool
    n_channels: int
    n_samples: int
    n_features: int
    event_counts: dict[str, int]


def convert_recipe(
    recipe: str | Path | ConversionRecipe,
    *,
    cache_root: str | Path,
    output_root: str | Path,
    source_override: str | Path | None = None,
    overwrite: bool = False,
    destination: str | Path | None = None,
) -> ConversionResult:
    """Execute one pinned single-recording recipe and verify its CND round trip."""
    resolved_recipe = (
        load_recipe(recipe) if not isinstance(recipe, ConversionRecipe) else recipe
    )
    if resolved_recipe.status != "active":
        raise ValueError(
            f"Recipe status {resolved_recipe.status!r} is not directly executable"
        )
    prepared = prepare_conversion(resolved_recipe, cache_root, source_override)

    resolved_destination = (
        Path(destination).expanduser().resolve()
        if destination is not None
        else Path(output_root).expanduser().resolve()
        / resolved_recipe.source.dataset_id
        / resolved_recipe.recipe_version
    )
    with staged_directory(resolved_destination, overwrite=overwrite) as staging:
        neural, stimulus = write_verified_conversion(prepared, staging)

    neural_path = resolved_destination / "dataCND" / neural.name
    stimulus_path = resolved_destination / "dataCND" / stimulus.name
    manifest_path = resolved_destination / "manifest.json"
    return ConversionResult(
        output_directory=resolved_destination,
        neural_path=neural_path,
        stimulus_path=stimulus_path,
        manifest_path=manifest_path,
        source_path=prepared.snapshot.path,
        source_reused_cache=prepared.snapshot.reused_cache,
        n_channels=len(prepared.raw.ch_names),
        n_samples=int(prepared.raw.n_times),
        n_features=len(prepared.extracted.names),
        event_counts=prepared.extracted.event_counts,
    )
