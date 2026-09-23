"""Professional-grade aesthetic analysis engine for Maya scenes.

Implements 5 dimensions of design quality analysis:
1. Color Theory (60-30-10 rule, temperature, harmony, saturation)
2. Spatial Composition (golden ratio, rule of thirds, visual weight, symmetry)
3. Proportion & Scale (human scale, hierarchy, proportional relationships)
4. Lighting Quality (layer analysis, temperature, balance)
5. Visual Flow (sight lines, circulation, leading lines, rhythm)

DORMANT (T-11b/D-038): zero production references - the Maya-side inline
_score_* functions in maya_scene_module.py are the live implementation.
This module is kept for the T-06 consolidation decision (inject, or
rewrite from the inline implementation); until then it is material,
not a promise. See the ADR-0003 status note.

References:
- Itten, J. "The Art of Color" - color theory fundamentals
- Ching, F.D.K. "Architecture: Form, Space, & Order" - spatial composition
- Lynch, K. "The Image of the City" - wayfinding and visual flow
- Pheasant, S. "Anthropometry and Workspace Design" - human scale
- Neufert, E. "Architects' Data" - architectural standards
"""

import math
from typing import Any


# ============================================================
# Constants & Design Standards
# ============================================================

# Golden ratio
PHI = 1.618033988749895

# Human scale reference (cm)
HUMAN_EYE_HEIGHT = 150.0
HUMAN_REACH_HEIGHT = 200.0
HUMAN_AVG_HEIGHT = 170.0
HUMAN_SHOULDER_WIDTH = 45.0

# Color temperature thresholds (mired values)
COLOR_TEMP_WARM_THRESHOLD = 3700  # Kelvin - warm white
COLOR_TEMP_NEUTRAL_LOW = 3700
COLOR_TEMP_NEUTRAL_HIGH = 5000
COLOR_TEMP_COOL_THRESHOLD = 5000  # Kelvin - cool white

# Design rule weights for final score
DIMENSION_WEIGHTS = {
    "color_theory": 0.25,
    "spatial_composition": 0.25,
    "proportion_scale": 0.20,
    "lighting_quality": 0.15,
    "visual_flow": 0.15,
}


# ============================================================
# Color Theory Analysis
# ============================================================


def rgb_to_hsl(rgb: tuple[float, float, float]) -> tuple[float, float, float]:
    """Convert RGB [0-1] to HSL (H: 0-360, S: 0-1, L: 0-1)."""
    r, g, b = rgb
    mx = max(r, g, b)
    mn = min(r, g, b)
    l = (mx + mn) / 2.0

    if mx == mn:
        return (0.0, 0.0, l)

    d = mx - mn
    s = d / (2.0 - mx - mn) if l > 0.5 else d / (mx + mn)

    if mx == r:
        h = 60 * (((g - b) / d) % 6)
    elif mx == g:
        h = 60 * ((b - r) / d + 2)
    else:
        h = 60 * ((r - g) / d + 4)

    return (h % 360, s, l)


def rgb_to_hue(rgb: tuple[float, float, float]) -> float:
    """Extract hue (0-360) from RGB [0-1]."""
    return rgb_to_hsl(rgb)[0]


def color_temperature_k(rgb: tuple[float, float, float]) -> float:
    """Estimate color temperature in Kelvin from RGB.

    Uses McCamy's approximation adapted for RGB input.
    """
    r, g, b = rgb
    if r + g + b < 0.01:
        return 6500.0  # default neutral

    # Convert to 0-255 range
    r255 = r * 255
    g255 = g * 255
    b255 = b * 255

    # Approximate CCT using modified McCamy formula
    # Based on CIE 1931 chromaticity
    if r255 >= b255:
        # Warm (red-dominant)
        ratio = b255 / max(r255, 1)
        temp = 3000 + ratio * 3500
    else:
        # Cool (blue-dominant)
        ratio = r255 / max(b255, 1)
        temp = 6500 + (1 - ratio) * 3500

    return max(1000, min(12000, temp))


def analyze_60_30_10(
    colors: list[dict],
) -> dict[str, Any]:
    """Analyze adherence to the 60-30-10 color rule.

    Args:
        colors: list of {"color": [r,g,b], "weight": float, "name": str}

    Returns:
        dict with compliance score and breakdown.
    """
    if not colors:
        return {"score": 0, "compliance": "no_data", "ratios": []}

    # Sort by weight descending
    sorted_colors = sorted(colors, key=lambda c: c["weight"], reverse=True)
    total_weight = sum(c["weight"] for c in sorted_colors)

    if total_weight == 0:
        return {"score": 0, "compliance": "no_data", "ratios": []}

    # Calculate actual ratios
    ratios = []
    for i, c in enumerate(sorted_colors[:5]):
        pct = c["weight"] / total_weight
        ratios.append(
            {
                "name": c["name"],
                "ratio": round(pct, 3),
                "target": [0.60, 0.30, 0.10][i] if i < 3 else None,
            }
        )

    # Score based on how close to 60-30-10
    if len(ratios) >= 3:
        r60 = abs(ratios[0]["ratio"] - 0.60)
        r30 = abs(ratios[1]["ratio"] - 0.30)
        r10 = abs(ratios[2]["ratio"] - 0.10)
        deviation = (r60 + r30 + r10) / 3
        score = max(0, 100 - deviation * 200)  # 0 deviation = 100, 0.5 deviation = 0
        compliance = (
            "excellent"
            if score > 80
            else "good"
            if score > 60
            else "fair"
            if score > 40
            else "poor"
        )
    elif len(ratios) >= 2:
        # Partial compliance with 2 colors
        score = 50
        compliance = "partial"
    else:
        score = 30
        compliance = "monochromatic"

    return {
        "score": round(score, 1),
        "compliance": compliance,
        "ratios": ratios,
    }


def analyze_color_temperature(
    colors: list[dict],
) -> dict[str, Any]:
    """Analyze warm/cool balance of scene colors."""
    if not colors:
        return {"balance": "neutral", "warm_ratio": 0, "cool_ratio": 0, "score": 50}

    total_weight = sum(c["weight"] for c in colors)
    if total_weight == 0:
        return {"balance": "neutral", "warm_ratio": 0, "cool_ratio": 0, "score": 50}

    warm_weight = 0
    cool_weight = 0

    for c in colors:
        temp = color_temperature_k(tuple(c["color"]))
        if temp < COLOR_TEMP_NEUTRAL_LOW:
            warm_weight += c["weight"]
        elif temp > COLOR_TEMP_NEUTRAL_HIGH:
            cool_weight += c["weight"]
        else:
            # Neutral - split evenly
            warm_weight += c["weight"] * 0.5
            cool_weight += c["weight"] * 0.5

    warm_ratio = warm_weight / total_weight
    cool_ratio = cool_weight / total_weight

    # Balance score: 100 = perfect 50/50, 0 = all one side
    imbalance = abs(warm_ratio - 0.5) * 2
    score = max(0, 100 - imbalance * 50)

    if imbalance < 0.2:
        balance = "well_balanced"
    elif warm_ratio > cool_ratio:
        balance = "warm_dominant"
    else:
        balance = "cool_dominant"

    return {
        "balance": balance,
        "warm_ratio": round(warm_ratio, 3),
        "cool_ratio": round(cool_ratio, 3),
        "score": round(score, 1),
    }


def analyze_saturation_distribution(
    colors: list[dict],
) -> dict[str, Any]:
    """Analyze saturation distribution for visual interest."""
    if not colors:
        return {"score": 50, "distribution": "no_data"}

    saturations = []
    for c in colors:
        _, s, _ = rgb_to_hsl(tuple(c["color"]))
        saturations.append({"name": c["name"], "saturation": round(s, 3), "weight": c["weight"]})

    avg_sat = sum(s["saturation"] for s in saturations) / len(saturations)
    sat_range = max(s["saturation"] for s in saturations) - min(
        s["saturation"] for s in saturations
    )

    # Good design has varied saturation (not all flat or all vivid)
    if sat_range > 0.3:
        distribution = "varied"  # Good
        score = 85
    elif sat_range > 0.15:
        distribution = "moderate"
        score = 70
    else:
        distribution = "flat"
        score = 40

    # Penalize if everything is very desaturated (boring) or very saturated (chaotic)
    if avg_sat < 0.1:
        score = max(score - 20, 10)
        distribution += "_desaturated"
    elif avg_sat > 0.8:
        score = max(score - 15, 10)
        distribution += "_oversaturated"

    return {
        "score": round(score, 1),
        "distribution": distribution,
        "avg_saturation": round(avg_sat, 3),
        "saturation_range": round(sat_range, 3),
        "details": saturations[:8],
    }


def analyze_color_harmony(
    colors: list[dict],
) -> dict[str, Any]:
    """Analyze color harmony based on Itten's color wheel relationships."""
    if len(colors) < 2:
        return {"type": "monochromatic", "score": 60, "hue_angles": []}

    # Get hues of top colors
    hues = []
    for c in colors[:6]:
        h = rgb_to_hue(tuple(c["color"]))
        hues.append({"name": c["name"], "hue": round(h, 1)})

    # Analyze harmony type from top 2 hues
    h1, h2 = hues[0]["hue"], hues[1]["hue"]
    diff = abs(h1 - h2)
    if diff > 180:
        diff = 360 - diff

    if diff < 15:
        harmony_type = "monochromatic"
        score = 70
    elif diff < 45:
        harmony_type = "analogous"
        score = 85
    elif 150 < diff < 210:
        harmony_type = "complementary"
        score = 90
    elif 100 < diff < 140:
        harmony_type = "triadic"
        score = 80
    elif 60 < diff < 90:
        harmony_type = "split_complementary"
        score = 75
    else:
        harmony_type = "discordant"
        score = 40

    # Check if 3rd color supports the harmony
    if len(hues) >= 3:
        h3 = hues[2]["hue"]
        # For triadic: 3rd should be ~120 from both
        # For complementary: 3rd should be near one of them
        if harmony_type == "triadic":
            d13 = min(abs(h1 - h3), 360 - abs(h1 - h3))
            d23 = min(abs(h2 - h3), 360 - abs(h2 - h3))
            if 90 < d13 < 150 and 90 < d23 < 150:
                score += 10
        elif harmony_type == "complementary":
            d13 = min(abs(h1 - h3), 360 - abs(h1 - h3))
            if d13 < 30 or d13 > 330:
                score += 5  # 3rd supports primary

    return {
        "type": harmony_type,
        "score": min(100, round(score, 1)),
        "hue_angles": hues,
    }


def analyze_contrast(
    colors: list[dict],
) -> dict[str, Any]:
    """Analyze light/dark contrast (WCAG-inspired)."""
    if not colors:
        return {"ratio": 1, "score": 50, "level": "no_data"}

    # Relative luminance per WCAG 2.0
    def luminance(rgb):
        r, g, b = rgb
        # Linearize
        rl = r / 12.92 if r <= 0.03928 else ((r + 0.055) / 1.055) ** 2.4
        gl = g / 12.92 if g <= 0.03928 else ((g + 0.055) / 1.055) ** 2.4
        bl = b / 12.92 if b <= 0.03928 else ((b + 0.055) / 1.055) ** 2.4
        return 0.2126 * rl + 0.7152 * gl + 0.0722 * bl

    lum_values = [(c["name"], luminance(tuple(c["color"])), c["weight"]) for c in colors]
    lum_values.sort(key=lambda x: x[1])

    lightest_lum = lum_values[-1][1]
    darkest_lum = lum_values[0][1]

    ratio = (lightest_lum + 0.05) / (darkest_lum + 0.05) if darkest_lum > 0 else 21

    # Score: 4.5+ is AA standard (good), 7+ is AAA (excellent)
    if ratio >= 7:
        score, level = 100, "AAA_excellent"
    elif ratio >= 4.5:
        score, level = 85, "AA_good"
    elif ratio >= 3:
        score, level = 65, "adequate"
    elif ratio >= 2:
        score, level = 45, "low"
    else:
        score, level = 20, "insufficient"

    return {
        "ratio": round(ratio, 2),
        "score": score,
        "level": level,
        "lightest": lum_values[-1][0],
        "darkest": lum_values[0][0],
    }


def compute_color_theory_score(
    materials: list[dict],
) -> dict[str, Any]:
    """Compute overall color theory score from material data.

    Args:
        materials: list of {"name": str, "color": [r,g,b], "object_count": int}

    Returns:
        dict with sub-scores and overall color_theory score.
    """
    # Filter to active materials (assigned to objects)
    active = [m for m in materials if m.get("object_count", 0) > 0]
    if not active:
        return {"score": 0, "sub_scores": {}, "detail": "no_active_materials"}

    colors = [{"name": m["name"], "color": m["color"], "weight": m["object_count"]} for m in active]
    colors.sort(key=lambda c: c["weight"], reverse=True)

    rule_60_30_10 = analyze_60_30_10(colors)
    temperature = analyze_color_temperature(colors)
    saturation = analyze_saturation_distribution(colors)
    harmony = analyze_color_harmony(colors)
    contrast = analyze_contrast(colors)

    # Weighted sub-score average
    sub_scores = {
        "60_30_10_rule": rule_60_30_10["score"],
        "temperature_balance": temperature["score"],
        "saturation_variety": saturation["score"],
        "harmony_type": harmony["score"],
        "contrast_level": contrast["score"],
    }

    weights = {
        "60_30_10_rule": 0.20,
        "temperature_balance": 0.15,
        "saturation_variety": 0.15,
        "harmony_type": 0.25,
        "contrast_level": 0.25,
    }

    overall = sum(sub_scores[k] * weights[k] for k in sub_scores)

    return {
        "score": round(overall, 1),
        "sub_scores": sub_scores,
        "rule_60_30_10": rule_60_30_10,
        "temperature": temperature,
        "saturation": saturation,
        "harmony": harmony,
        "contrast": contrast,
        "top_colors": colors[:6],
    }


# ============================================================
# Spatial Composition Analysis
# ============================================================


def analyze_golden_ratio(
    objects: list[dict],
) -> dict[str, Any]:
    """Check if major proportional relationships approximate the golden ratio (1.618).

    Objects: list of {"name": str, "bbox_size": [x, y, z]}
    """
    if len(objects) < 2:
        return {"score": 50, "matches": [], "total_pairs": 0}

    # Calculate dominant dimension for each object
    sizes = []
    for obj in objects:
        bx, by, bz = obj["bbox_size"]
        dominant = max(bx, by, bz)
        if dominant > 0:
            sizes.append({"name": obj["name"], "size": dominant})

    if len(sizes) < 2:
        return {"score": 50, "matches": [], "total_pairs": 0}

    # Check ratios between object sizes
    matches = []
    total_checked = 0
    for i in range(len(sizes)):
        for j in range(i + 1, min(len(sizes), i + 20)):
            if sizes[j]["size"] > 0:
                ratio = sizes[i]["size"] / sizes[j]["size"]
                if ratio < 1:
                    ratio = 1 / ratio
                total_checked += 1
                deviation = abs(ratio - PHI)
                if deviation < 0.15:  # Within 15% of golden ratio
                    matches.append(
                        {
                            "a": sizes[i]["name"],
                            "b": sizes[j]["name"],
                            "ratio": round(ratio, 3),
                            "deviation": round(deviation, 3),
                        }
                    )

    if total_checked == 0:
        return {"score": 50, "matches": [], "total_pairs": 0}

    match_ratio = len(matches) / total_checked
    score = min(100, 50 + match_ratio * 100)

    return {
        "score": round(score, 1),
        "matches": matches[:5],
        "total_pairs": total_checked,
        "golden_ratio_pairs": len(matches),
    }


def analyze_rule_of_thirds(
    objects: list[dict],
    scene_bounds: dict,
) -> dict[str, Any]:
    """Check if key objects align with rule-of-thirds grid intersections.

    Objects: list of {"name": str, "position": [x, y, z], "visual_weight": float}
    scene_bounds: {"min": [x,y,z], "max": [x,y,z]}
    """
    if not objects or not scene_bounds:
        return {"score": 50, "aligned_objects": []}

    # Calculate thirds grid
    bmin = scene_bounds["min"]
    bmax = scene_bounds["max"]
    span_x = bmax[0] - bmin[0]
    span_z = bmax[2] - bmin[2]

    if span_x < 0.01 or span_z < 0.01:
        return {"score": 50, "aligned_objects": []}

    # Thirds grid points (4 intersections)
    thirds_x = [bmin[0] + span_x * i / 3 for i in range(1, 3)]
    thirds_z = [bmin[2] + span_z * i / 3 for i in range(1, 3)]
    grid_points = [(x, z) for x in thirds_x for z in thirds_z]

    # Tolerance: 10% of the smaller dimension
    tol = min(span_x, span_z) * 0.10

    aligned = []
    for obj in objects:
        px, pz = obj["position"][0], obj["position"][2]
        for gx, gz in grid_points:
            dist = math.sqrt((px - gx) ** 2 + (pz - gz) ** 2)
            if dist < tol:
                aligned.append(
                    {
                        "name": obj["name"],
                        "grid_point": [round(gx, 1), round(gz, 1)],
                        "distance": round(dist, 1),
                        "weight": obj.get("visual_weight", 1),
                    }
                )
                break

    # Score: weighted by visual importance
    if objects:
        aligned_weight = sum(a["weight"] for a in aligned)
        total_weight = sum(o.get("visual_weight", 1) for o in objects)
        coverage = aligned_weight / total_weight if total_weight > 0 else 0
        score = min(100, 40 + coverage * 120)
    else:
        score = 50

    return {
        "score": round(score, 1),
        "aligned_objects": aligned,
        "grid_points": [[round(x, 1), round(z, 1)] for x, z in grid_points],
    }


def analyze_visual_weight_balance(
    objects: list[dict],
    scene_bounds: dict,
) -> dict[str, Any]:
    """Analyze visual weight distribution for compositional balance.

    Objects: list of {"name": str, "position": [x,y,z], "size": float,
                       "color": [r,g,b] or None, "is_focal": bool}
    """
    if not objects:
        return {"score": 50, "quadrant_weights": {}}

    bmin = scene_bounds["min"]
    bmax = scene_bounds["max"]
    mid_x = (bmin[0] + bmax[0]) / 2
    mid_z = (bmin[2] + bmax[2]) / 2

    # Calculate visual weight for each object
    # Visual weight = size * luminance_contrast * focal_bonus
    quadrants = {"top_left": 0, "top_right": 0, "bottom_left": 0, "bottom_right": 0}

    for obj in objects:
        px, pz = obj["position"][0], obj["position"][2]
        size = obj.get("size", 100)
        is_focal = obj.get("is_focal", False)

        # Luminance contribution
        color = obj.get("color")
        if color:
            lum = 0.2126 * color[0] + 0.7152 * color[1] + 0.0722 * color[2]
        else:
            lum = 0.5

        # Visual weight calculation
        weight = size * (1 + lum * 0.5) * (1.5 if is_focal else 1.0)

        # Assign to quadrant
        if px <= mid_x and pz <= mid_z:
            quadrants["top_left"] += weight
        elif px > mid_x and pz <= mid_z:
            quadrants["top_right"] += weight
        elif px <= mid_x and pz > mid_z:
            quadrants["bottom_left"] += weight
        else:
            quadrants["bottom_right"] += weight

    total = sum(quadrants.values())
    if total == 0:
        return {"score": 50, "quadrant_weights": {}}

    # Normalize to ratios
    ratios = {k: round(v / total, 3) for k, v in quadrants.items()}

    # Balance score: ideal is 25% each (0.25 deviation = 0 score)
    max_deviation = max(abs(r - 0.25) for r in ratios.values())
    score = max(0, 100 - max_deviation * 400)

    # Check diagonal balance (top_left + bottom_right vs top_right + bottom_left)
    diag_a = ratios["top_left"] + ratios["bottom_right"]
    diag_b = ratios["top_right"] + ratios["bottom_left"]
    diag_balance = 1 - abs(diag_a - diag_b)

    return {
        "score": round(score, 1),
        "quadrant_weights": ratios,
        "diagonal_balance": round(diag_balance, 3),
    }


def compute_spatial_composition_score(
    objects: list[dict],
    scene_bounds: dict,
) -> dict[str, Any]:
    """Compute overall spatial composition score."""
    golden = analyze_golden_ratio(objects)
    thirds = analyze_rule_of_thirds(objects, scene_bounds)
    balance = analyze_visual_weight_balance(objects, scene_bounds)

    sub_scores = {
        "golden_ratio": golden["score"],
        "rule_of_thirds": thirds["score"],
        "visual_balance": balance["score"],
    }

    weights = {"golden_ratio": 0.30, "rule_of_thirds": 0.35, "visual_balance": 0.35}
    overall = sum(sub_scores[k] * weights[k] for k in sub_scores)

    return {
        "score": round(overall, 1),
        "sub_scores": sub_scores,
        "golden_ratio": golden,
        "rule_of_thirds": thirds,
        "visual_balance": balance,
    }


# ============================================================
# Proportion & Scale Analysis
# ============================================================


def analyze_human_scale_reference(
    objects: list[dict],
) -> dict[str, Any]:
    """Evaluate how well objects relate to human body dimensions.

    Checks display heights, counter heights, passage widths against ergonomic standards.
    """
    issues = []
    score = 100

    for obj in objects:
        name = obj["name"].lower()
        by = obj["bbox_size"][1]  # Height
        bx = obj["bbox_size"][0]  # Width

        # Display/counter objects should be in comfortable viewing range
        if any(kw in name for kw in ["display", "shelf", "counter", "kiosk", "vitrine"]):
            if by > HUMAN_REACH_HEIGHT:
                issues.append(
                    {
                        "type": "display_too_high",
                        "object": obj["name"],
                        "height": round(by, 1),
                        "max_recommended": HUMAN_REACH_HEIGHT,
                        "severity": "warning",
                    }
                )
                score -= 5
            elif by < 60:
                issues.append(
                    {
                        "type": "display_too_low",
                        "object": obj["name"],
                        "height": round(by, 1),
                        "min_recommended": 60,
                        "severity": "info",
                    }
                )
                score -= 2

        # Passage widths (aisles, corridors)
        if any(kw in name for kw in ["aisle", "corridor", "path", "passage", "walkway"]):
            if bx < 120:
                issues.append(
                    {
                        "type": "passage_too_narrow",
                        "object": obj["name"],
                        "width": round(bx, 1),
                        "min_wheelchair": 120,
                        "min_comfort": 150,
                        "severity": "error" if bx < 90 else "warning",
                    }
                )
                score -= 10

    return {
        "score": max(0, round(score, 1)),
        "issues": issues[:10],
        "reference_heights": {
            "eye_level": HUMAN_EYE_HEIGHT,
            "comfortable_reach": HUMAN_REACH_HEIGHT,
            "counter_standard": 90,
            "display_ideal": 130,
        },
    }


def analyze_scale_hierarchy(
    objects: list[dict],
) -> dict[str, Any]:
    """Check if objects have a clear size hierarchy (hero > secondary > tertiary).

    Good design has 3 clear tiers of visual importance.
    """
    if len(objects) < 3:
        return {"score": 50, "tiers": [], "hierarchy_clarity": "insufficient"}

    # Sort by size
    sorted_objs = sorted(objects, key=lambda o: max(o["bbox_size"]), reverse=True)
    sizes = [max(o["bbox_size"]) for o in sorted_objs]

    # Try to find natural tier breaks
    # Use a simple 3-tier classification
    max_size = sizes[0]
    tier_thresholds = [max_size * 0.6, max_size * 0.25]

    tiers = {"hero": [], "secondary": [], "tertiary": []}
    for obj in sorted_objs:
        s = max(obj["bbox_size"])
        if s >= tier_thresholds[0]:
            tiers["hero"].append(obj["name"])
        elif s >= tier_thresholds[1]:
            tiers["secondary"].append(obj["name"])
        else:
            tiers["tertiary"].append(obj["name"])

    # Score: ideal has 1-3 hero, 3-8 secondary, rest tertiary
    hero_count = len(tiers["hero"])
    sec_count = len(tiers["secondary"])

    score = 70  # base
    if 1 <= hero_count <= 3:
        score += 15
    elif hero_count == 0:
        score -= 20
    elif hero_count > 5:
        score -= 10  # Too many focal points

    if 2 <= sec_count <= 10:
        score += 15
    elif sec_count == 0:
        score -= 10

    # Check if hero is significantly larger than secondary (clear hierarchy)
    if tiers["hero"] and tiers["secondary"]:
        hero_size = max(max(o["bbox_size"]) for o in sorted_objs if o["name"] in tiers["hero"])
        sec_sizes = [max(o["bbox_size"]) for o in sorted_objs if o["name"] in tiers["secondary"]]
        if sec_sizes:
            ratio = hero_size / max(sec_sizes)
            if ratio > 1.5:
                score += 10  # Clear hierarchy
            elif ratio < 1.1:
                score -= 10  # Hierarchy too flat

    return {
        "score": min(100, max(0, round(score, 1))),
        "tiers": {
            "hero": tiers["hero"][:3],
            "secondary": tiers["secondary"][:5],
            "tertiary_count": len(tiers["tertiary"]),
        },
        "hierarchy_clarity": "clear" if score > 75 else "moderate" if score > 50 else "unclear",
    }


def compute_proportion_scale_score(
    objects: list[dict],
) -> dict[str, Any]:
    """Compute overall proportion & scale score."""
    human_ref = analyze_human_scale_reference(objects)
    hierarchy = analyze_scale_hierarchy(objects)

    sub_scores = {
        "human_scale": human_ref["score"],
        "hierarchy_clarity": hierarchy["score"],
    }

    weights = {"human_scale": 0.50, "hierarchy_clarity": 0.50}
    overall = sum(sub_scores[k] * weights[k] for k in sub_scores)

    return {
        "score": round(overall, 1),
        "sub_scores": sub_scores,
        "human_scale": human_ref,
        "hierarchy": hierarchy,
    }


# ============================================================
# Lighting Quality Analysis
# ============================================================


def classify_light_type(name: str) -> str:
    """Classify light by its role based on naming convention."""
    name_lower = name.lower()
    if any(kw in name_lower for kw in ["key", "main", "primary", "hero"]):
        return "key"
    elif any(kw in name_lower for kw in ["fill", "ambient", "bounce", "secondary"]):
        return "fill"
    elif any(kw in name_lower for kw in ["rim", "edge", "back", "kicker"]):
        return "rim"
    elif any(kw in name_lower for kw in ["accent", "spot", "highlight", "focus"]):
        return "accent"
    else:
        return "unclassified"


def analyze_lighting_layers(
    lights: list[dict],
) -> dict[str, Any]:
    """Analyze lighting setup for proper layer composition.

    Professional lighting has at least: key + fill + accent.
    """
    if not lights:
        return {"score": 0, "layers": {}, "missing": ["key", "fill", "accent"]}

    layers = {"key": [], "fill": [], "rim": [], "accent": [], "unclassified": []}
    for light in lights:
        role = classify_light_type(light["name"])
        layers[role].append(light)

    # Score based on layer completeness
    score = 30  # base for having any lights
    missing = []

    if layers["key"]:
        score += 25
    else:
        missing.append("key")

    if layers["fill"]:
        score += 20
    else:
        missing.append("fill")

    if layers["accent"]:
        score += 15
    else:
        missing.append("accent")

    if layers["rim"]:
        score += 10

    # Penalize unclassified lights (naming convention not followed)
    if len(layers["unclassified"]) > len(lights) * 0.5:
        score -= 10

    return {
        "score": min(100, max(0, round(score, 1))),
        "layers": {k: len(v) for k, v in layers.items()},
        "missing": missing,
        "total_lights": len(lights),
    }


def analyze_light_color_temperature(
    lights: list[dict],
) -> dict[str, Any]:
    """Analyze color temperature consistency of lights."""
    if not lights:
        return {"score": 50, "consistency": "no_lights"}

    temps = []
    for light in lights:
        color = light.get("color", [1, 1, 1])
        temp = color_temperature_k(tuple(color))
        temps.append({"name": light["name"], "temp_k": round(temp)})

    if len(temps) < 2:
        return {"score": 70, "consistency": "single_light", "temps": temps}

    temp_range = max(t["temp_k"] for t in temps) - min(t["temp_k"] for t in temps)

    # Good lighting has consistent temperature (within 1000K) or deliberate contrast
    if temp_range < 500:
        consistency = "very_consistent"
        score = 90
    elif temp_range < 1500:
        consistency = "consistent"
        score = 75
    elif temp_range < 3000:
        consistency = "mixed"
        score = 55
    else:
        consistency = "inconsistent"
        score = 30

    return {
        "score": round(score, 1),
        "consistency": consistency,
        "temp_range_k": temp_range,
        "temps": temps,
    }


def compute_lighting_quality_score(
    lights: list[dict],
) -> dict[str, Any]:
    """Compute overall lighting quality score with professional analysis.

    Sub-analyses:
    - Layer composition (key/fill/rim/accent)
    - Three-point lighting validation
    - Fill ratio (key:fill intensity, ideal 2:1 to 4:1)
    - Shadow quality
    - Color temperature grading & mood
    - Spatial coverage
    - Decay rate plausibility
    - Intensity distribution
    """
    if not lights:
        return {"score": 0, "sub_scores": {}, "detail": "no_lights"}

    layers = {"key": [], "fill": [], "rim": [], "accent": [], "unclassified": []}
    for light in lights:
        role = classify_light_type(light["name"])
        layers[role].append(light)

    sub_scores = {}

    # Layer completeness
    layer_score = 20
    if layers["key"]:
        layer_score += 30
    if layers["fill"]:
        layer_score += 25
    if layers["accent"]:
        layer_score += 15
    if layers["rim"]:
        layer_score += 10
    sub_scores["layers"] = min(100, layer_score)

    # Three-point validation
    has_key = len(layers["key"]) > 0
    has_fill = len(layers["fill"]) > 0
    has_rim_or_accent = len(layers["rim"]) > 0 or len(layers["accent"]) > 0
    tp_score = 0
    if has_key:
        tp_score += 40
    if has_fill:
        tp_score += 30
    if has_rim_or_accent:
        tp_score += 20
    if has_key and has_fill and has_rim_or_accent:
        tp_score += 10
    sub_scores["three_point"] = min(100, tp_score)

    # Fill ratio
    key_int = sum(l.get("intensity", 1) for l in layers["key"])
    fill_int = sum(l.get("intensity", 1) for l in layers["fill"])
    if key_int > 0 and fill_int > 0:
        ratio = key_int / fill_int
        if 1.5 <= ratio <= 4.0:
            sub_scores["fill_ratio"] = 90
        elif 1.0 <= ratio <= 6.0:
            sub_scores["fill_ratio"] = 70
        else:
            sub_scores["fill_ratio"] = 50
    elif key_int > 0:
        sub_scores["fill_ratio"] = 40
    else:
        sub_scores["fill_ratio"] = 30

    # Shadow quality
    shadow_count = sum(1 for l in lights if l.get("shadow", False))
    shadow_ratio = shadow_count / len(lights)
    if 0.3 <= shadow_ratio <= 0.8:
        sub_scores["shadow_quality"] = 90
    elif shadow_ratio > 0.8:
        sub_scores["shadow_quality"] = 70
    elif shadow_ratio > 0:
        sub_scores["shadow_quality"] = 60
    else:
        sub_scores["shadow_quality"] = 30

    # Color temperature
    if len(lights) >= 2:
        temps = []
        for light in lights:
            c = light.get("color", [1, 1, 1])
            temps.append(color_temperature_k(tuple(c)))
        temp_range = max(temps) - min(temps)
        avg_temp = sum(temps) / len(temps)
        if temp_range < 500:
            sub_scores["temperature"] = 90
        elif temp_range < 1500:
            sub_scores["temperature"] = 75
        elif temp_range < 3000:
            sub_scores["temperature"] = 55
        else:
            sub_scores["temperature"] = 30
        # Mood
        if avg_temp < 3500:
            mood = "warm_intimate"
        elif avg_temp < 4500:
            mood = "warm_neutral"
        elif avg_temp < 5500:
            mood = "neutral"
        elif avg_temp < 6500:
            mood = "cool_professional"
        else:
            mood = "cool_dramatic"
    else:
        sub_scores["temperature"] = 60
        mood = "unknown"

    # Coverage
    if len(lights) >= 2:
        positions = [l.get("position", [0, 0, 0]) for l in lights]
        xs = [p[0] for p in positions]
        zs = [p[2] for p in positions]
        x_range = max(xs) - min(xs) if len(xs) > 1 else 0
        z_range = max(zs) - min(zs) if len(zs) > 1 else 0
        if x_range > 100 and z_range > 100:
            sub_scores["coverage"] = 85
        elif x_range > 50 or z_range > 50:
            sub_scores["coverage"] = 65
        else:
            sub_scores["coverage"] = 40
    else:
        sub_scores["coverage"] = 40

    # Decay
    decay_scores = []
    for light in lights:
        decay = light.get("decay", 0)
        ltype = light.get("type", "")
        if ltype in ("pointLight", "spotLight", "areaLight"):
            if decay == 2:
                decay_scores.append(100)
            elif decay == 1:
                decay_scores.append(70)
            else:
                decay_scores.append(30)
        else:
            decay_scores.append(80)
    sub_scores["decay"] = sum(decay_scores) / len(decay_scores) if decay_scores else 50

    # Intensity distribution
    intensities = [l.get("intensity", 1) for l in lights]
    max_int = max(intensities)
    min_int = min(intensities)
    if max_int > 0:
        contrast = max_int / max(min_int, 0.001)
        if 2 <= contrast <= 10:
            sub_scores["intensity_dist"] = 85
        elif contrast > 10:
            sub_scores["intensity_dist"] = 60
        else:
            sub_scores["intensity_dist"] = 65
    else:
        sub_scores["intensity_dist"] = 30

    weights = {
        "layers": 0.15,
        "three_point": 0.20,
        "fill_ratio": 0.15,
        "shadow_quality": 0.10,
        "temperature": 0.10,
        "coverage": 0.10,
        "decay": 0.10,
        "intensity_dist": 0.10,
    }
    overall = sum(sub_scores[k] * weights[k] for k in sub_scores)

    return {
        "score": round(overall, 1),
        "sub_scores": {k: round(v, 1) for k, v in sub_scores.items()},
        "mood": mood,
        "layer_breakdown": {k: len(v) for k, v in layers.items()},
    }


def analyze_sight_lines(
    objects: list[dict],
    entrance_pos: list[float] | None = None,
) -> dict[str, Any]:
    """Analyze if key focal objects are visible from entrance/main viewpoints.

    Checks for blocking objects in line of sight.
    """
    if not objects:
        return {"score": 50, "blocked_lines": []}

    # Find focal/hero objects
    focal_objects = [o for o in objects if o.get("is_focal", False)]
    if not focal_objects:
        # Use largest objects as implicit focal points
        sorted_by_size = sorted(objects, key=lambda o: max(o["bbox_size"]), reverse=True)
        focal_objects = sorted_by_size[:2]

    if not focal_objects:
        return {"score": 50, "blocked_lines": []}

    # Default entrance position
    if entrance_pos is None:
        entrance_pos = [0, 0, -500]  # Assume entrance at -Z

    blocked = []
    clear = []

    for focal in focal_objects:
        fp = focal["position"]
        # Simple ray check: are there objects between entrance and focal?
        dx = fp[0] - entrance_pos[0]
        dz = fp[2] - entrance_pos[2]
        ray_length = math.sqrt(dx * dx + dz * dz)

        if ray_length < 1:
            clear.append(focal["name"])
            continue

        # Normalize ray direction
        ndx = dx / ray_length
        ndz = dz / ray_length

        is_blocked = False
        for obj in objects:
            if obj["name"] == focal["name"]:
                continue
            if obj.get("is_focal", False):
                continue  # Don't count other focal objects as blockers

            op = obj["position"]
            # Project object center onto ray
            t = (op[0] - entrance_pos[0]) * ndx + (op[2] - entrance_pos[2]) * ndz
            if 0.1 < t < ray_length * 0.95:
                # Closest point on ray to object
                closest_x = entrance_pos[0] + ndx * t
                closest_z = entrance_pos[2] + ndz * t
                dist = math.sqrt((op[0] - closest_x) ** 2 + (op[2] - closest_z) ** 2)

                # If object is within its own size of the ray line, it's blocking
                obj_size = max(obj["bbox_size"]) * 0.3
                if dist < obj_size:
                    is_blocked = True
                    blocked.append(
                        {
                            "focal": focal["name"],
                            "blocked_by": obj["name"],
                            "distance_from_entrance": round(t, 1),
                        }
                    )
                    break

        if not is_blocked:
            clear.append(focal["name"])

    total_focal = len(focal_objects)
    clear_ratio = len(clear) / total_focal if total_focal > 0 else 0
    score = 40 + clear_ratio * 60

    return {
        "score": round(score, 1),
        "clear_sight_lines": clear,
        "blocked_lines": blocked,
        "entrance_pos": entrance_pos,
    }


def analyze_circulation_clarity(
    objects: list[dict],
    zone_map: dict | None = None,
) -> dict[str, Any]:
    """Analyze if circulation paths are clear and intuitive.

    Checks for:
    - Path objects exist and have adequate width
    - No objects blocking designated paths
    - Clear flow from entrance to destination
    """
    score = 70  # base
    issues = []

    # Find path-related objects
    path_objects = [
        o
        for o in objects
        if any(
            kw in o["name"].lower()
            for kw in ["path", "aisle", "corridor", "walkway", "route", "passage"]
        )
    ]

    if not path_objects:
        score = 40
        issues.append(
            {
                "type": "no_designated_paths",
                "severity": "warning",
                "msg": "No path/aisle objects found. Consider naming circulation elements.",
            }
        )
    else:
        # Check path widths
        for path in path_objects:
            width = min(path["bbox_size"][0], path["bbox_size"][2])
            if width < 90:
                issues.append(
                    {
                        "type": "path_too_narrow",
                        "object": path["name"],
                        "width": round(width, 1),
                        "min_recommended": 90,
                        "severity": "error",
                    }
                )
                score -= 10
            elif width < 120:
                issues.append(
                    {
                        "type": "path_narrow",
                        "object": path["name"],
                        "width": round(width, 1),
                        "recommended": 120,
                        "severity": "warning",
                    }
                )
                score -= 5

    return {
        "score": max(0, round(score, 1)),
        "path_objects": len(path_objects),
        "issues": issues[:5],
    }


def analyze_visual_rhythm(
    objects: list[dict],
) -> dict[str, Any]:
    """Analyze repetition and rhythm in object placement.

    Good rhythm creates predictable patterns that guide the eye.
    """
    if len(objects) < 3:
        return {"score": 50, "pattern": "insufficient_objects"}

    # Group objects by similar size (potential repeating elements)
    sorted_objs = sorted(objects, key=lambda o: max(o["bbox_size"]), reverse=True)

    # Find groups of similarly-sized objects
    groups = []
    current_group = [sorted_objs[0]]

    for i in range(1, len(sorted_objs)):
        size_ratio = max(sorted_objs[i]["bbox_size"]) / max(current_group[0]["bbox_size"])
        if 0.7 < size_ratio < 1.4:  # Similar size
            current_group.append(sorted_objs[i])
        else:
            if len(current_group) >= 2:
                groups.append(current_group)
            current_group = [sorted_objs[i]]

    if len(current_group) >= 2:
        groups.append(current_group)

    # Check spacing regularity within groups
    rhythm_score = 50
    patterns_found = 0

    for group in groups:
        if len(group) < 2:
            continue

        # Check spacing between consecutive objects in group
        positions = [o["position"] for o in group]
        spacings = []
        for i in range(len(positions) - 1):
            dist = math.sqrt(
                (positions[i + 1][0] - positions[i][0]) ** 2
                + (positions[i + 1][2] - positions[i][2]) ** 2
            )
            spacings.append(dist)

        if len(spacings) >= 2:
            avg_spacing = sum(spacings) / len(spacings)
            if avg_spacing > 0:
                spacing_variance = sum((s - avg_spacing) ** 2 for s in spacings) / len(spacings)
                cv = math.sqrt(spacing_variance) / avg_spacing  # Coefficient of variation

                if cv < 0.15:  # Very regular spacing
                    rhythm_score += 20
                    patterns_found += 1
                elif cv < 0.30:
                    rhythm_score += 10
                    patterns_found += 1

    return {
        "score": min(100, max(0, round(rhythm_score, 1))),
        "repeating_groups": len(groups),
        "patterns_found": patterns_found,
        "group_sizes": [len(g) for g in groups[:5]],
    }


def compute_visual_flow_score(
    objects: list[dict],
    zone_map: dict | None = None,
    entrance_pos: list[float] | None = None,
) -> dict[str, Any]:
    """Compute overall visual flow score."""
    sight_lines = analyze_sight_lines(objects, entrance_pos)
    circulation = analyze_circulation_clarity(objects, zone_map)
    rhythm = analyze_visual_rhythm(objects)

    sub_scores = {
        "sight_lines": sight_lines["score"],
        "circulation": circulation["score"],
        "visual_rhythm": rhythm["score"],
    }

    weights = {"sight_lines": 0.40, "circulation": 0.35, "visual_rhythm": 0.25}
    overall = sum(sub_scores[k] * weights[k] for k in sub_scores)

    return {
        "score": round(overall, 1),
        "sub_scores": sub_scores,
        "sight_lines": sight_lines,
        "circulation": circulation,
        "rhythm": rhythm,
    }


# ============================================================
# Master Aesthetic Score
# ============================================================


def compute_aesthetic_score(
    materials: list[dict],
    objects: list[dict],
    scene_bounds: dict,
    lights: list[dict],
    zone_map: dict | None = None,
    entrance_pos: list[float] | None = None,
) -> dict[str, Any]:
    """Compute comprehensive aesthetic score across all 5 dimensions.

    Returns:
        dict with overall score (0-100), dimension scores, and detailed analysis.
    """
    color = compute_color_theory_score(materials)
    spatial = compute_spatial_composition_score(objects, scene_bounds)
    proportion = compute_proportion_scale_score(objects)
    lighting = compute_lighting_quality_score(lights)
    flow = compute_visual_flow_score(objects, zone_map, entrance_pos)

    dimensions = {
        "color_theory": color,
        "spatial_composition": spatial,
        "proportion_scale": proportion,
        "lighting_quality": lighting,
        "visual_flow": flow,
    }

    # Weighted overall score
    overall = sum(dimensions[dim]["score"] * DIMENSION_WEIGHTS[dim] for dim in dimensions)

    # Grade
    if overall >= 90:
        grade = "S"
    elif overall >= 80:
        grade = "A"
    elif overall >= 70:
        grade = "B"
    elif overall >= 60:
        grade = "C"
    elif overall >= 50:
        grade = "D"
    else:
        grade = "F"

    # Top improvement suggestions
    suggestions = []
    for dim_name, dim_data in sorted(dimensions.items(), key=lambda x: x[1]["score"]):
        if dim_data["score"] < 70:
            suggestions.append(
                {
                    "dimension": dim_name,
                    "score": dim_data["score"],
                    "priority": "high" if dim_data["score"] < 50 else "medium",
                }
            )

    return {
        "overall_score": round(overall, 1),
        "grade": grade,
        "dimensions": {k: v["score"] for k, v in dimensions.items()},
        "detail": dimensions,
        "improvement_suggestions": suggestions[:3],
    }
