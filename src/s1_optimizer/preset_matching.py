"""Safe matching of discovered filament profiles to import targets."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Iterable

from .errors import PlanError
from .filaments import FilamentOption


def _diameter(value: object) -> Decimal:
    try:
        parsed = Decimal(str(value).strip())
    except (InvalidOperation, ValueError, TypeError):
        raise PlanError(f"Invalid nozzle diameter {value!r}; choose a numeric nozzle size") from None
    if not parsed.is_finite() or parsed <= 0:
        raise PlanError(f"Invalid nozzle diameter {value!r}; choose a positive finite nozzle size")
    return parsed


def match_filament_option(
    options: Iterable[FilamentOption], *, material: str, nozzle_diameter: object,
    selected_id: str | None = None,
) -> FilamentOption:
    """Return the uniquely suitable discovered profile for material and nozzle.

    Matching is restricted to exact material and numerically
    equal nozzle diameter.  A canonical Anycubic label wins when present;
    otherwise a single actual candidate is accepted.  Missing or ambiguous
    matches are deliberately rejected so callers cannot silently cross-select.
    """
    if not isinstance(material, str) or not material.strip():
        raise PlanError("Filament material is required to match an installed profile")
    requested_diameter = _diameter(nozzle_diameter)
    options = tuple(options)
    if selected_id is not None:
        selected = [option for option in options if option.filament_id == selected_id]
        if len(selected) != 1:
            raise PlanError("Explicit destination base is missing or ambiguous; select it again")
        choice = selected[0]
        if choice.material != material or _diameter(choice.nozzle_diameter) != requested_diameter:
            raise PlanError("Explicit destination base must match the source material and destination nozzle")
        return choice
    matches = [
        option for option in options
        if option.material == material
        and _diameter(option.nozzle_diameter) == requested_diameter
    ]
    if not matches:
        raise PlanError(
            f"No discovered filament profile matches material {material!r} "
            f"and {requested_diameter:g} mm nozzle"
        )
    diameter_label = format(requested_diameter.normalize(), "f")
    canonical = f"Anycubic {material} @Anycubic Kobra S1 {diameter_label} nozzle"
    canonical_matches = [option for option in matches if option.label == canonical]
    if len(canonical_matches) == 1:
        return canonical_matches[0]
    if len(matches) == 1:
        return matches[0]
    labels = ", ".join(repr(option.label) for option in matches)
    raise PlanError(
        f"Ambiguous filament profiles for material {material!r} and "
        f"{requested_diameter:g} mm nozzle; choose one explicitly: {labels}"
    )
