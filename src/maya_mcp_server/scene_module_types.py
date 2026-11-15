"""Type-only declarations for the injected ``_mcp_scene`` module.

Why this file exists: ``maya_scene_module.py`` sits at its
``.github/monolith-budget.json`` line cap, so declarations that only the type
checker needs live here instead of widening that cap. Nothing here runs
inside Maya. The Maya-side payload is one concatenated module, and
``maya_scene_module.py`` keeps ``from __future__ import annotations``, so every
annotation below stays a string at Maya runtime and the payload never imports
this host-side file.

``MayaStandards`` gives each ``_MAYA_STANDARDS`` key its real value type.
Without it mypy infers the mixed-value dict literal as ``dict[str, object]``,
and every threshold comparison, ``%d`` interpolation and iteration over the
prefix list reports ``object`` (issue #255). All 26 keys are declared, not
only the six the scene checks read today: mypy checks the annotated literal
key by key, so a missing key turns the assignment itself into an error, and
the class is also the written record of what the container holds.
"""

from __future__ import annotations

from typing import Any, TypedDict


# Container shapes shared by the aesthetic scoring chain.
_Objs = list[dict[str, Any]]
_Bounds = dict[str, list[float]]
_Zones = dict[str, Any]


class MayaStandards(TypedDict):
    """Shape of ``_MAYA_STANDARDS``: production thresholds read by scene checks."""

    forbidden_prefixes: list[str]
    required_group_prefix: str
    max_nesting_depth: int
    max_objects_soft: int
    max_objects_hard: int
    max_cameras_keep: int
    min_lights: int
    min_objects_per_group: int
    require_groups_for: list[str]
    min_clearance_cm: int
    overlap_tolerance_cm: int
    aisle_main_min_cm: int
    aisle_secondary_min_cm: int
    aisle_display_min_cm: int
    wheelchair_turn_cm: int
    display_height_min_cm: int
    display_height_max_cm: int
    display_height_ideal_cm: int
    ceiling_min_cm: int
    ceiling_ideal_cm: int
    entrance_width_min_cm: int
    entrance_decompression_cm: int
    max_main_colors: int
    min_contrast_ratio: float
    focal_min: int
    focal_max: int
