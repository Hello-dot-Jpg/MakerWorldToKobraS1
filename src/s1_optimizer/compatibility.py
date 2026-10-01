"""Narrow, evidence-backed JSON shape translations, not a generic schema rewrite."""
from decimal import Decimal, InvalidOperation


# PrintConfig.cpp scalar declarations corroborated by installed 2.0.0.2
# profiles (flush_multiplier is source-schema evidence only); see
# docs/DOWNLOAD_SETTINGS_AUDIT.md. Never flatten filament slots,
# coordinates, or machine-mode arrays merely because their values agree.
NUMERIC_SCALAR_KEYS = frozenset({
    "bridge_speed", "default_acceleration", "gap_infill_speed", "flush_multiplier",
    "initial_layer_acceleration", "initial_layer_infill_speed",
    "initial_layer_speed", "inner_wall_acceleration", "inner_wall_speed",
    "internal_solid_infill_speed", "outer_wall_acceleration", "outer_wall_speed",
    "overhang_1_4_speed", "overhang_2_4_speed", "overhang_3_4_speed",
    "overhang_4_4_speed", "small_perimeter_speed", "small_perimeter_threshold",
    "sparse_infill_acceleration", "sparse_infill_speed", "support_interface_speed",
    "support_speed", "top_solid_infill_flow_ratio", "top_surface_acceleration",
    "top_surface_speed", "travel_acceleration", "travel_speed", "travel_speed_z",
})
PERCENT_SCALAR_KEYS = frozenset({
    "overhang_1_4_speed", "overhang_2_4_speed", "overhang_3_4_speed",
    "overhang_4_4_speed", "small_perimeter_speed", "sparse_infill_acceleration",
})
SCALAR_KEYS = NUMERIC_SCALAR_KEYS | {"enable_overhang_speed"}


def scalarize(key: str, value: object) -> tuple[object, str | None]:
    """Only unanimous, valid values can be represented without choosing a tool."""
    if key not in SCALAR_KEYS:
        return value, None
    if isinstance(value, list):
        items = value
    elif isinstance(value, str) and "," in value:
        items = [part.strip() for part in value.split(",")]
    else:
        return value, None
    if items and all(isinstance(item, str) for item in items) and len(set(items)) == 1:
        item = items[0]
        if key == "enable_overhang_speed":
            valid = item in {"0", "1"}
        else:
            number = item[:-1] if item.endswith("%") and key in PERCENT_SCALAR_KEYS else item
            try:
                valid = bool(number.strip()) and Decimal(number).is_finite() and Decimal(number) >= 0
            except InvalidOperation:
                valid = False
        if valid:
            return item, None
    label = "single overhang-slowdown switch" if key == "enable_overhang_speed" else "single scalar setting"
    return value, f"Mixed or invalid {key} values cannot be represented by the destination's {label}"
