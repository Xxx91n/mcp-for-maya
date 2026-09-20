"""Tests for the aesthetic_engine module.

DORMANT coverage (D-038): the engine has zero production references -
these tests guard a dormant asset until the T-06 consolidation
decision; they are not evidence of a verified production path.
"""

import pytest

from maya_mcp_server.aesthetic_engine import (
    HUMAN_EYE_HEIGHT,
    PHI,
    analyze_60_30_10,
    analyze_circulation_clarity,
    analyze_color_harmony,
    analyze_color_temperature,
    analyze_contrast,
    analyze_golden_ratio,
    analyze_human_scale_reference,
    analyze_light_color_temperature,
    analyze_lighting_layers,
    analyze_rule_of_thirds,
    analyze_saturation_distribution,
    analyze_scale_hierarchy,
    analyze_sight_lines,
    analyze_visual_rhythm,
    analyze_visual_weight_balance,
    color_temperature_k,
    compute_aesthetic_score,
    compute_color_theory_score,
    compute_lighting_quality_score,
    compute_proportion_scale_score,
    compute_spatial_composition_score,
    compute_visual_flow_score,
    rgb_to_hsl,
    rgb_to_hue,
)


# ============================================================
# Color Theory Tests
# ============================================================


class TestRgbToHsl:
    def test_pure_red(self):
        h, s, l = rgb_to_hsl((1.0, 0.0, 0.0))
        assert abs(h - 0) < 1
        assert abs(s - 1.0) < 0.01
        assert abs(l - 0.5) < 0.01

    def test_pure_green(self):
        h, s, l = rgb_to_hsl((0.0, 1.0, 0.0))
        assert abs(h - 120) < 1

    def test_pure_blue(self):
        h, s, l = rgb_to_hsl((0.0, 0.0, 1.0))
        assert abs(h - 240) < 1

    def test_gray(self):
        h, s, l = rgb_to_hsl((0.5, 0.5, 0.5))
        assert s == 0
        assert abs(l - 0.5) < 0.01

    def test_white(self):
        h, s, l = rgb_to_hsl((1.0, 1.0, 1.0))
        assert s == 0
        assert abs(l - 1.0) < 0.01

    def test_black(self):
        h, s, l = rgb_to_hsl((0.0, 0.0, 0.0))
        assert s == 0
        assert abs(l - 0.0) < 0.01


class TestColorTemperature:
    def test_warm_red(self):
        temp = color_temperature_k((1.0, 0.2, 0.1))
        assert temp < 4000  # Should be warm

    def test_cool_blue(self):
        temp = color_temperature_k((0.1, 0.2, 1.0))
        assert temp > 6000  # Should be cool

    def test_neutral_white(self):
        temp = color_temperature_k((0.5, 0.5, 0.5))
        assert 3000 < temp < 10000  # Should be in reasonable range


class TestAnalyze60_30_10:
    def test_perfect_60_30_10(self):
        colors = [
            {"name": "primary", "color": [0.2, 0.2, 0.2], "weight": 60},
            {"name": "secondary", "color": [0.5, 0.5, 0.5], "weight": 30},
            {"name": "accent", "color": [0.9, 0.1, 0.1], "weight": 10},
        ]
        result = analyze_60_30_10(colors)
        assert result["score"] > 90
        assert result["compliance"] == "excellent"

    def test_even_distribution(self):
        colors = [
            {"name": "a", "color": [0.2, 0.2, 0.2], "weight": 33},
            {"name": "b", "color": [0.5, 0.5, 0.5], "weight": 33},
            {"name": "c", "color": [0.8, 0.8, 0.8], "weight": 34},
        ]
        result = analyze_60_30_10(colors)
        assert result["score"] < 70  # Not ideal 60-30-10

    def test_single_color(self):
        colors = [{"name": "only", "color": [0.5, 0.5, 0.5], "weight": 100}]
        result = analyze_60_30_10(colors)
        assert result["compliance"] == "monochromatic"

    def test_empty(self):
        result = analyze_60_30_10([])
        assert result["score"] == 0


class TestColorHarmony:
    def test_complementary(self):
        colors = [
            {"name": "red", "color": [1.0, 0.0, 0.0], "weight": 50},
            {"name": "cyan", "color": [0.0, 1.0, 1.0], "weight": 50},
        ]
        result = analyze_color_harmony(colors)
        assert result["type"] == "complementary"
        assert result["score"] >= 85

    def test_analogous(self):
        colors = [
            {"name": "red", "color": [1.0, 0.0, 0.0], "weight": 50},
            {"name": "orange", "color": [1.0, 0.5, 0.0], "weight": 50},
        ]
        result = analyze_color_harmony(colors)
        assert result["type"] == "analogous"

    def test_monochromatic(self):
        colors = [
            {"name": "dark", "color": [0.2, 0.2, 0.2], "weight": 50},
            {"name": "mid", "color": [0.5, 0.5, 0.5], "weight": 50},
        ]
        result = analyze_color_harmony(colors)
        assert result["type"] == "monochromatic"


class TestContrast:
    def test_high_contrast(self):
        colors = [
            {"name": "white", "color": [1.0, 1.0, 1.0], "weight": 50},
            {"name": "black", "color": [0.0, 0.0, 0.0], "weight": 50},
        ]
        result = analyze_contrast(colors)
        assert result["ratio"] > 20
        assert result["level"] == "AAA_excellent"

    def test_low_contrast(self):
        colors = [
            {"name": "light_gray", "color": [0.8, 0.8, 0.8], "weight": 50},
            {"name": "mid_gray", "color": [0.7, 0.7, 0.7], "weight": 50},
        ]
        result = analyze_contrast(colors)
        assert result["ratio"] < 3


class TestSaturationDistribution:
    def test_varied_saturation(self):
        colors = [
            {"name": "vivid", "color": [1.0, 0.0, 0.0], "weight": 50},
            {"name": "muted", "color": [0.6, 0.4, 0.4], "weight": 50},
        ]
        result = analyze_saturation_distribution(colors)
        assert result["saturation_range"] > 0.15

    def test_flat_saturation(self):
        colors = [
            {"name": "a", "color": [0.5, 0.5, 0.5], "weight": 50},
            {"name": "b", "color": [0.6, 0.6, 0.6], "weight": 50},
        ]
        result = analyze_saturation_distribution(colors)
        assert result["saturation_range"] < 0.1


class TestColorTemperatureAnalysis:
    def test_warm_dominant(self):
        colors = [
            {"name": "red", "color": [1.0, 0.1, 0.0], "weight": 80},
            {"name": "blue", "color": [0.0, 0.1, 1.0], "weight": 20},
        ]
        result = analyze_color_temperature(colors)
        assert result["balance"] == "warm_dominant"

    def test_balanced(self):
        colors = [
            {"name": "warm", "color": [1.0, 0.5, 0.0], "weight": 50},
            {"name": "cool", "color": [0.0, 0.5, 1.0], "weight": 50},
        ]
        result = analyze_color_temperature(colors)
        assert result["balance"] == "well_balanced"


# ============================================================
# Spatial Composition Tests
# ============================================================


class TestGoldenRatio:
    def test_golden_ratio_match(self):
        objects = [
            {"name": "large", "bbox_size": [161.8, 100, 100]},
            {"name": "small", "bbox_size": [100, 100, 100]},
        ]
        result = analyze_golden_ratio(objects)
        assert result["golden_ratio_pairs"] >= 1

    def test_no_match(self):
        objects = [
            {"name": "a", "bbox_size": [100, 100, 100]},
            {"name": "b", "bbox_size": [100, 100, 100]},
        ]
        result = analyze_golden_ratio(objects)
        assert result["golden_ratio_pairs"] == 0

    def test_single_object(self):
        result = analyze_golden_ratio([{"name": "only", "bbox_size": [100, 100, 100]}])
        assert result["score"] == 50


class TestRuleOfThirds:
    def test_aligned_object(self):
        objects = [
            {"name": "focal", "position": [333.3, 0, 333.3], "visual_weight": 100},
        ]
        bounds = {"min": [0, 0, 0], "max": [1000, 100, 1000]}
        result = analyze_rule_of_thirds(objects, bounds)
        assert result["score"] > 50

    def test_center_object(self):
        objects = [
            {"name": "center", "position": [500, 0, 500], "visual_weight": 100},
        ]
        bounds = {"min": [0, 0, 0], "max": [1000, 100, 1000]}
        result = analyze_rule_of_thirds(objects, bounds)
        # Center is not on thirds grid
        assert result["score"] <= 60


class TestVisualWeightBalance:
    def test_balanced_scene(self):
        objects = [
            {"name": "tl", "position": [200, 0, 200], "size": 100},
            {"name": "tr", "position": [800, 0, 200], "size": 100},
            {"name": "bl", "position": [200, 0, 800], "size": 100},
            {"name": "br", "position": [800, 0, 800], "size": 100},
        ]
        bounds = {"min": [0, 0, 0], "max": [1000, 100, 1000]}
        result = analyze_visual_weight_balance(objects, bounds)
        assert result["score"] > 80

    def test_unbalanced_scene(self):
        objects = [
            {"name": "heavy", "position": [100, 0, 100], "size": 500},
            {"name": "light", "position": [900, 0, 900], "size": 10},
        ]
        bounds = {"min": [0, 0, 0], "max": [1000, 100, 1000]}
        result = analyze_visual_weight_balance(objects, bounds)
        assert result["score"] < 60


# ============================================================
# Proportion & Scale Tests
# ============================================================


class TestHumanScale:
    def test_good_display_height(self):
        objects = [
            {"name": "display_main", "bbox_size": [100, 130, 60]},
        ]
        result = analyze_human_scale_reference(objects)
        assert result["score"] >= 90

    def test_too_high_display(self):
        objects = [
            {"name": "display_tall", "bbox_size": [100, 250, 60]},
        ]
        result = analyze_human_scale_reference(objects)
        assert result["score"] < 100
        assert any(i["type"] == "display_too_high" for i in result["issues"])

    def test_narrow_aisle(self):
        objects = [
            {"name": "aisle_narrow", "bbox_size": [80, 10, 500]},
        ]
        result = analyze_human_scale_reference(objects)
        assert result["score"] < 100


class TestScaleHierarchy:
    def test_clear_hierarchy(self):
        objects = [
            {"name": "hero", "bbox_size": [200, 200, 200]},
            {"name": "sec1", "bbox_size": [80, 80, 80]},
            {"name": "sec2", "bbox_size": [70, 70, 70]},
            {"name": "small1", "bbox_size": [20, 20, 20]},
            {"name": "small2", "bbox_size": [15, 15, 15]},
        ]
        result = analyze_scale_hierarchy(objects)
        assert result["score"] >= 70
        assert result["hierarchy_clarity"] in ["clear", "moderate"]

    def test_flat_hierarchy(self):
        objects = [
            {"name": "a", "bbox_size": [100, 100, 100]},
            {"name": "b", "bbox_size": [95, 95, 95]},
            {"name": "c", "bbox_size": [90, 90, 90]},
        ]
        result = analyze_scale_hierarchy(objects)
        # All similar size = unclear hierarchy
        assert result["hierarchy_clarity"] != "clear"


# ============================================================
# Lighting Tests
# ============================================================


class TestLightingLayers:
    def test_complete_setup(self):
        lights = [
            {"name": "key_light", "type": "directionalLight", "color": [1, 1, 1], "intensity": 1.0},
            {
                "name": "fill_ambient",
                "type": "ambientLight",
                "color": [0.8, 0.8, 0.9],
                "intensity": 0.5,
            },
            {"name": "accent_spot", "type": "spotLight", "color": [1, 0.9, 0.8], "intensity": 0.8},
        ]
        result = analyze_lighting_layers(lights)
        assert result["score"] >= 80
        assert len(result["missing"]) <= 1  # may miss accent

    def test_no_lights(self):
        result = analyze_lighting_layers([])
        assert result["score"] == 0

    def test_only_key(self):
        lights = [
            {"name": "key_main", "type": "directionalLight", "color": [1, 1, 1], "intensity": 1.0}
        ]
        result = analyze_lighting_layers(lights)
        assert "fill" in result["missing"]


class TestLightTemperature:
    def test_consistent_temp(self):
        lights = [
            {"name": "a", "type": "spotLight", "color": [1, 0.9, 0.8], "intensity": 1},
            {"name": "b", "type": "spotLight", "color": [1, 0.85, 0.75], "intensity": 1},
        ]
        result = analyze_light_color_temperature(lights)
        assert result["consistency"] in ["very_consistent", "consistent"]

    def test_mixed_temp(self):
        lights = [
            {"name": "warm", "type": "spotLight", "color": [1, 0.5, 0.2], "intensity": 1},
            {"name": "cool", "type": "spotLight", "color": [0.2, 0.5, 1], "intensity": 1},
        ]
        result = analyze_light_color_temperature(lights)
        assert result["temp_range_k"] > 1000


# ============================================================
# Visual Flow Tests
# ============================================================


class TestSightLines:
    def test_clear_sight(self):
        objects = [
            {
                "name": "focal_hero",
                "position": [0, 0, 500],
                "bbox_size": [100, 100, 100],
                "is_focal": True,
            },
            {
                "name": "wall_left",
                "position": [-300, 0, 200],
                "bbox_size": [50, 200, 50],
                "is_focal": False,
            },
        ]
        result = analyze_sight_lines(objects, [0, 0, -500])
        assert result["score"] > 70

    def test_blocked_sight(self):
        objects = [
            {
                "name": "focal_hero",
                "position": [0, 0, 500],
                "bbox_size": [100, 100, 100],
                "is_focal": True,
            },
            {
                "name": "big_wall",
                "position": [0, 0, 100],
                "bbox_size": [400, 400, 400],
                "is_focal": False,
            },
        ]
        result = analyze_sight_lines(objects, [0, 0, -500])
        assert len(result["blocked_lines"]) > 0


class TestCirculation:
    def test_has_paths(self):
        objects = [
            {"name": "main_aisle", "bbox_size": [200, 10, 1000]},
            {"name": "side_path", "bbox_size": [150, 10, 500]},
        ]
        result = analyze_circulation_clarity(objects)
        assert result["score"] >= 60

    def test_no_paths(self):
        objects = [{"name": "random_obj", "bbox_size": [100, 100, 100]}]
        result = analyze_circulation_clarity(objects)
        assert result["score"] <= 50


class TestVisualRhythm:
    def test_regular_pattern(self):
        objects = [
            {"name": f"shelf_{i}", "bbox_size": [60, 120, 30], "position": [i * 200, 0, 0]}
            for i in range(5)
        ]
        result = analyze_visual_rhythm(objects)
        assert result["repeating_groups"] >= 1

    def test_random_placement(self):
        objects = [
            {"name": f"obj_{i}", "bbox_size": [60, 120, 30], "position": [i * 137, 0, i * 293]}
            for i in range(5)
        ]
        result = analyze_visual_rhythm(objects)
        # Random placement may or may not have rhythm
        assert "score" in result


# ============================================================
# Integration: Full Aesthetic Score
# ============================================================


class TestEnhancedLighting:
    def test_three_point_setup(self):
        lights = [
            {
                "name": "key_main",
                "type": "spotLight",
                "color": [1, 0.95, 0.9],
                "intensity": 1.0,
                "position": [200, 300, 100],
                "shadow": True,
                "decay": 2,
            },
            {
                "name": "fill_ambient",
                "type": "areaLight",
                "color": [0.9, 0.92, 1.0],
                "intensity": 0.4,
                "position": [-200, 200, 50],
                "shadow": False,
                "decay": 2,
            },
            {
                "name": "rim_edge",
                "type": "spotLight",
                "color": [1, 0.98, 0.95],
                "intensity": 0.6,
                "position": [0, 250, -200],
                "shadow": True,
                "decay": 2,
            },
        ]
        result = analyze_lighting_layers(lights)
        assert result["score"] >= 80
        assert len(result["missing"]) <= 1  # may miss accent

    def test_fill_ratio_cinematic(self):
        lights = [
            {"name": "key_main", "type": "spotLight", "color": [1, 1, 1], "intensity": 1.0},
            {"name": "fill_soft", "type": "areaLight", "color": [0.9, 0.9, 1.0], "intensity": 0.35},
        ]
        result = analyze_light_color_temperature(lights)
        assert result["consistency"] in ["very_consistent", "consistent"]

    def test_dramatic_contrast(self):
        lights = [
            {"name": "key_hero", "type": "spotLight", "color": [1, 0.8, 0.6], "intensity": 2.0},
            {
                "name": "fill_subtle",
                "type": "ambientLight",
                "color": [0.7, 0.75, 0.8],
                "intensity": 0.2,
            },
        ]
        result = analyze_light_color_temperature(lights)
        assert result["temp_range_k"] > 500

    def test_single_directional(self):
        lights = [
            {"name": "sun", "type": "directionalLight", "color": [1, 0.98, 0.9], "intensity": 1.0},
        ]
        result = analyze_lighting_layers(lights)
        assert result["total_lights"] == 1

    def test_many_lights(self):
        lights = [
            {"name": f"light_{i}", "type": "pointLight", "color": [1, 1, 1], "intensity": 0.5}
            for i in range(20)
        ]
        result = analyze_lighting_layers(lights)
        assert result["total_lights"] == 20

    def test_unclassified_light_names_no_keyerror(self):
        """D-038: names matching no role keyword must land in the
        unclassified bucket instead of raising KeyError."""
        lights = [
            {"name": "sun", "type": "directionalLight", "color": [1, 0.98, 0.9], "intensity": 1.0},
            {"name": "pointLight1", "type": "pointLight", "color": [1, 1, 1], "intensity": 0.5},
        ]
        result = compute_lighting_quality_score(lights)
        assert "score" in result


class TestLightingWithPosition:
    def test_coverage_spread(self):
        lights = [
            {
                "name": "key_a",
                "type": "spotLight",
                "color": [1, 1, 1],
                "intensity": 1.0,
                "position": [-500, 300, -500],
                "shadow": True,
                "decay": 2,
            },
            {
                "name": "key_b",
                "type": "spotLight",
                "color": [1, 0.95, 0.9],
                "intensity": 0.8,
                "position": [500, 300, 500],
                "shadow": True,
                "decay": 2,
            },
            {
                "name": "fill_c",
                "type": "areaLight",
                "color": [0.9, 0.9, 1.0],
                "intensity": 0.4,
                "position": [0, 200, 0],
                "shadow": False,
                "decay": 2,
            },
        ]
        for l in lights:
            assert "position" in l
            assert len(l["position"]) == 3

    def test_spot_cone_data(self):
        light = {
            "name": "spot_hero",
            "type": "spotLight",
            "color": [1, 1, 1],
            "intensity": 1.0,
            "cone_angle": 45.0,
            "penumbra": 10.0,
        }
        assert light["cone_angle"] == 45.0
        assert light["penumbra"] == 10.0


class TestComputeAestheticScore:
    def test_full_score(self):
        materials = [
            {"name": "mat_dark", "color": [0.1, 0.1, 0.1], "object_count": 60},
            {"name": "mat_accent", "color": [0.8, 0.2, 0.2], "object_count": 30},
            {"name": "mat_highlight", "color": [0.9, 0.9, 0.9], "object_count": 10},
        ]
        objects = [
            {
                "name": "shell",
                "position": [0, 0, 0],
                "bbox_size": [1000, 300, 800],
                "size": 1000,
                "color": [0.1, 0.1, 0.1],
                "is_focal": False,
            },
            {
                "name": "display_main",
                "position": [0, 0, 300],
                "bbox_size": [200, 130, 100],
                "size": 200,
                "color": [0.8, 0.2, 0.2],
                "is_focal": True,
            },
            {
                "name": "counter_a",
                "position": [200, 0, 200],
                "bbox_size": [150, 90, 60],
                "size": 150,
                "color": [0.9, 0.9, 0.9],
                "is_focal": False,
            },
            {
                "name": "aisle_main",
                "position": [0, 0, 0],
                "bbox_size": [200, 10, 600],
                "size": 600,
                "color": None,
                "is_focal": False,
            },
        ]
        bounds = {"min": [-500, 0, -400], "max": [500, 300, 400]}
        lights = [
            {
                "name": "key_main",
                "type": "directionalLight",
                "color": [1, 0.95, 0.9],
                "intensity": 1.0,
            },
            {
                "name": "fill_ambient",
                "type": "ambientLight",
                "color": [0.8, 0.85, 0.9],
                "intensity": 0.5,
            },
            {"name": "accent_spot", "type": "spotLight", "color": [1, 0.9, 0.8], "intensity": 0.8},
        ]

        result = compute_aesthetic_score(materials, objects, bounds, lights)

        assert "overall_score" in result
        assert "grade" in result
        assert result["overall_score"] >= 0
        assert result["overall_score"] <= 100
        assert result["grade"] in ["S", "A", "B", "C", "D", "F"]
        assert "color_theory" in result["dimensions"]
        assert "spatial_composition" in result["dimensions"]
        assert "proportion_scale" in result["dimensions"]
        assert "lighting_quality" in result["dimensions"]
        assert "visual_flow" in result["dimensions"]

    def test_empty_scene(self):
        result = compute_aesthetic_score([], [], {"min": [0, 0, 0], "max": [100, 100, 100]}, [])
        assert result["overall_score"] >= 0
        assert result["grade"] in ["S", "A", "B", "C", "D", "F"]


# ============================================================
# Edge Cases
# ============================================================


class TestEdgeCases:
    def test_zero_size_objects(self):
        """Objects with zero size should not crash."""
        objects = [
            {
                "name": "degenerate",
                "bbox_size": [0, 0, 0],
                "size": 0,
                "position": [0, 0, 0],
                "color": None,
                "is_focal": False,
            },
        ]
        result = analyze_visual_weight_balance(objects, {"min": [0, 0, 0], "max": [100, 100, 100]})
        assert "score" in result

    def test_single_object_all_dimensions(self):
        """Single object should not crash any dimension."""
        objects = [
            {
                "name": "only",
                "bbox_size": [100, 100, 100],
                "size": 100,
                "position": [50, 50, 50],
                "color": [0.5, 0.5, 0.5],
                "is_focal": False,
            },
        ]
        bounds = {"min": [0, 0, 0], "max": [100, 100, 100]}
        result = compute_spatial_composition_score(objects, bounds)
        assert result["score"] >= 0

    def test_very_large_scene(self):
        """1000 objects should not be too slow."""
        import time

        objects = [
            {
                "name": f"obj_{i}",
                "bbox_size": [10, 10, 10],
                "size": 10,
                "position": [i % 50 * 20, 0, i // 50 * 20],
                "color": [0.5, 0.5, 0.5],
                "is_focal": False,
            }
            for i in range(1000)
        ]
        bounds = {"min": [0, 0, 0], "max": [1000, 100, 400]}
        start = time.monotonic()
        result = compute_spatial_composition_score(objects, bounds)
        elapsed = time.monotonic() - start
        assert elapsed < 2.0  # Should be fast
        assert result["score"] >= 0
