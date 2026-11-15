"""Issue #276 Maya-side tests: one light payload for both producers.

Before this change, analyze_aesthetics() built a 13-field light payload and
scene_review()'s lighting check built a 7-field one from the same Maya
attributes. These tests pin the shared builder in scene_light_module: both
public paths call it, it writes every field for every light type, and one
unreadable light still does not hide the rest.
"""

from __future__ import annotations

import json


_LIGHT_PAYLOAD_KEYS = {
    "name",
    "type",
    "color",
    "intensity",
    "position",
    "rotation",
    "decay",
    "shadow",
    "cone_angle",
    "penumbra",
    "area_size",
    "diffuse",
    "specular",
}


class TestOneSharedPayload:
    def test_both_consumers_call_the_shared_builder(self, maya_env, monkeypatch):
        maya_env.scene.add_light("LGT_key", t=(0, 100, 0))

        calls = 0
        original = maya_env.module.collect_light_payloads

        def spy(*args):
            nonlocal calls
            calls += 1
            return original(*args)

        # The call sites reach the builder through globals(), which is the
        # module dict, so replacing the module attribute is what they see.
        monkeypatch.setattr(maya_env.module, "collect_light_payloads", spy)

        maya_env.module.analyze_aesthetics()
        maya_env.module.scene_review(["lighting"])

        assert calls == 2

    def test_the_payload_carries_every_field_for_every_light_type(self, maya_env):
        scene = maya_env.scene
        scene.add_light("LGT_spot", ltype="spotLight", t=(1.26, 2, 3), r=(0, 45, 0))
        scene.add_light("LGT_area", ltype="areaLight", t=(4, 5, 6))
        scene.add_light("LGT_dir", ltype="directionalLight", t=(7, 8, 9))

        payloads = {p["name"]: p for p in maya_env.module.collect_light_payloads()}

        assert set(payloads) == {"LGT_spot", "LGT_area", "LGT_dir"}
        for payload in payloads.values():
            assert set(payload) == _LIGHT_PAYLOAD_KEYS
            json.dumps(payload, allow_nan=False)

        assert payloads["LGT_spot"]["position"] == [1.3, 2.0, 3.0]
        assert payloads["LGT_spot"]["rotation"] == [0.0, 45.0, 0.0]
        assert payloads["LGT_spot"]["cone_angle"] == 40.0
        assert payloads["LGT_spot"]["penumbra"] == 10.0
        assert payloads["LGT_area"]["area_size"] == [10.0, 10.0]
        # A light type without the shape attributes reports null, not zero.
        assert payloads["LGT_dir"]["cone_angle"] is None
        assert payloads["LGT_dir"]["area_size"] is None

    def test_one_unreadable_light_does_not_hide_the_rest(self, maya_env, monkeypatch):
        maya_env.scene.add_light("LGT_ok", t=(0, 100, 0))
        maya_env.scene.add_light("LGT_bad", t=(100, 100, 0))
        real_node_type = maya_env.cmds.nodeType

        def node_type(name):
            if name == "LGT_badShape":
                raise RuntimeError("unreadable light")
            return real_node_type(name)

        monkeypatch.setattr(maya_env.cmds, "nodeType", node_type)

        payloads = maya_env.module.collect_light_payloads()

        assert [p["name"] for p in payloads] == ["LGT_ok"]

    def test_a_light_without_shadow_attributes_counts_as_shadowing(self, maya_env):
        # The shared builder inherited this reading from the aesthetic
        # engine, which was the richer of the two copies. Real lights carry
        # one of the two flags; this pins what happens when neither exists.
        maya_env.scene.add_light("LGT_dark", t=(0, 100, 0))
        shape = maya_env.scene.resolve("LGT_darkShape")
        shape.attrs.pop("useDepthMapShadow")

        payloads = maya_env.module.collect_light_payloads()

        assert payloads[0]["shadow"] is True

    def test_the_aesthetic_and_review_scores_agree(self, maya_env):
        scene = maya_env.scene
        scene.add_light("LGT_key", ltype="spotLight", t=(0, 100, 0), r=(-45, 0, 0))
        scene.add_light("LGT_fill", ltype="pointLight", t=(100, 100, 0))
        scene.add_light("LGT_rim", ltype="areaLight", t=(-100, 50, 0))

        aesthetic = maya_env.module.analyze_aesthetics()
        review = maya_env.module.scene_review(["lighting"])

        assert review["checks"]["lighting"] == aesthetic["detail"]["lighting_quality"]
