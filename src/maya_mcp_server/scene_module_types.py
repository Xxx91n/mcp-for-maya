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
_Bounds = dict[str, list[float]]


class ObjectPayload(TypedDict):
    """One entry of ``analyze_aesthetics``'s objects payload.

    The scorer reads these fields by name, so a typo in ``bbox_size`` or
    ``is_focal`` used to pass unnoticed; declaring them here makes mypy
    read the same field list the scorer does.
    """

    name: str
    position: list[float]
    bbox_size: list[float]
    size: float
    # No shader assignment and no matching material entry are both normal:
    # the payload keeps going with an empty colour and material name.
    color: list[float] | None
    material: str | None
    is_focal: bool


class LightCore(TypedDict):
    """The frame every lighting read needs; LightPayload adds the shape fields."""

    name: str
    type: str
    color: list[float]
    intensity: float
    position: list[float]
    decay: int
    shadow: bool


class LightPayload(LightCore):
    """The one light payload both producers build (issue #276).

    Every field is required. The scene review check used to carry only the
    seven LightCore fields, and the missing shape fields were the drift #276
    removed: one builder now writes all of them for both consumers.
    """

    rotation: list[float]
    cone_angle: float | None
    penumbra: float | None
    area_size: list[float] | None
    diffuse: bool
    specular: bool


class MaterialPayload(TypedDict):
    """One entry of the material mapping's materials list."""

    name: str
    color: list[float]
    objects: list[str]
    object_count: int
    shader_group: str


class DimensionScore(TypedDict):
    """Shape every design-dimension score shares: the number plus its parts."""

    score: float
    sub_scores: dict[str, float]


class ColorTheoryScore(DimensionScore, total=False):
    """Color theory result; ``detail`` replaces the numbers when nothing is scorable."""

    detail: str
    top_colors: list[dict[str, Any]]


class ProportionScore(DimensionScore, total=False):
    """Proportion result; carries the scale problems it found, if any."""

    issues: list[dict[str, Any]]


class LightingScore(DimensionScore, total=False):
    """Lighting result; ``detail`` marks an empty scene, the rest describe the setup."""

    detail: str
    layer_breakdown: dict[str, int]
    mood: str
    fill_ratio: float | None
    temp_consistency: str


class ScoredResult(TypedDict):
    """The one number every research helper always returns."""

    score: float


class SilhouetteResult(TypedDict):
    """Silhouette analysis: the clarity average plus the per-object rows."""

    avg_clarity: float
    details: list[dict[str, Any]]


class CurvatureResult(ScoredResult, total=False):
    """Curvature analysis; ``detail`` replaces the numbers when data is short."""

    detail: str
    size_cv: float
    avg_size: float
    interpretation: str


class RhythmResult(ScoredResult, total=False):
    """Rhythm analysis; ``detail`` marks too few objects to read a pattern."""

    detail: str
    repeating_groups: int
    patterns_found: int


class StyleConsistencyResult(ScoredResult, total=False):
    """Style consistency; ``detail`` marks too few objects to compare."""

    detail: str
    form_consistency: float
    size_hierarchy: float
    material_consistency: float


class MergedColorTheory(ColorTheoryScore):
    """Color theory as the merge leaves it: the score plus the style read folded in."""

    style_consistency: StyleConsistencyResult


class MergedProportion(ProportionScore):
    """Proportion as the merge leaves it: the scale numbers plus the two shape reads."""

    silhouette: SilhouetteResult
    curvature: CurvatureResult


class MergedVisualFlow(DimensionScore):
    """Visual flow as the merge leaves it: the score plus the rhythm read."""

    rhythm_enhanced: RhythmResult


class AestheticDimensions(TypedDict):
    """The five dimension records after the research helpers are folded in.

    Five exact shapes, not one wide optional-key dict. Only three dimensions
    gain a research read, and each gains a different one, so a single
    optional-key type would mark always-present keys optional and still could
    not say which dimension carries which read. Building this in one literal
    at the merge step also means a forgotten read is a missing-key error, not
    a key that quietly never appears in the payload.
    """

    color_theory: MergedColorTheory
    spatial_composition: DimensionScore
    proportion_scale: MergedProportion
    lighting_quality: LightingScore
    visual_flow: MergedVisualFlow


class ImprovementSuggestion(TypedDict):
    """One entry of the result's ``improvement_suggestions`` list."""

    dimension: str
    score: float
    priority: str


class AestheticScore(TypedDict):
    """What ``_compute_full_aesthetic_score`` produces, before sampling counts.

    ``dimensions`` is the flat name-to-score view the review reads;
    ``detail`` keeps each dimension's full record, whose extra keys differ
    per dimension.
    """

    overall_score: float
    grade: str
    dimensions: dict[str, float]
    detail: AestheticDimensions
    improvement_suggestions: list[ImprovementSuggestion]


class SamplingInfo(TypedDict):
    """How much of the scene the sampled pass actually looked at."""

    checked: int
    skipped: int
    object_limit: int


class AestheticScoreResult(AestheticScore):
    """Public ``analyze_aesthetics`` output: the score plus the sampling counts."""

    sampling: SamplingInfo


class ZoneCore(TypedDict):
    """Zone record as ``get_zone_map`` first builds it, before any object is filed.

    Mirrors ``spatial_types.ZoneInfo`` as a plain dict on purpose: this one
    crosses into Maya as the JSON payload of ``get_zone_map``.
    """

    name: str
    pattern_matched: str
    objects: list[str]
    bbox_min: list[float]
    bbox_max: list[float]


class ZoneRecord(ZoneCore, total=False):
    """Finished zone record: count and center only exist once a zone has objects.

    ``unit`` is present only when the record was converted out of Maya's
    internal centimetres for display.
    """

    object_count: int
    center: list[float]
    unit: str


class ShotSpec(TypedDict):
    """One ``SHOT_TYPES`` entry: the framing numbers ``create_camera_shot`` reads."""

    distance_mult: float
    focal_length: int
    desc: str


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
