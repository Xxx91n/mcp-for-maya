"""T-23b tests: _mcp_export.export_scene on the maya stub.

D-092 contract coverage: format inference/conflict mirror rules,
exists->domain error, parent auto-create, objects pre-validation,
selection save/restore on success AND failure, plugin load attempt,
prompt=False/force=True pinned, real duration_ms/size_bytes, and the
scene modified flag left untouched.
"""

from __future__ import annotations

import json

import maya_stub
import pytest


@pytest.fixture
def env(maya_env, tmp_path):
    """Stub scene + freshly imported export_module bound to it."""
    module = maya_stub.load_export_module()
    maya_env.scene.add_mesh("GEO_box")
    maya_env.scene.add_mesh("GEO_ball")
    maya_env.scene.modified = False  # clean baseline for dirty-flag tests
    return maya_env, module, tmp_path


def _calls(env):
    return env[0].scene.file_calls


class TestFormatResolution:
    def test_extension_inference_all_formats(self, env):
        _, module, tmp = env
        for fmt, maya_type in (
            ("fbx", "FBX export"),
            ("obj", "OBJexport"),
            ("usd", "USD Export"),
        ):
            out = module.export_scene(str(tmp / f"scene.{fmt}"))
            assert "error" not in out, out
            assert out["format"] == fmt
            call = _calls(env)[-1]
            assert call["kwargs"]["type"] == maya_type

    def test_explicit_format_appends_missing_extension(self, env):
        _, module, tmp = env
        out = module.export_scene(str(tmp / "scene"), format="fbx")
        assert "error" not in out, out
        assert out["path"].endswith(".fbx")
        assert out["format"] == "fbx"

    def test_explicit_format_matching_extension_ok(self, env):
        _, module, tmp = env
        out = module.export_scene(str(tmp / "scene.obj"), format="obj")
        assert "error" not in out, out
        assert out["format"] == "obj"

    def test_conflict_errors_both_directions(self, env):
        """Mirror rule: ext!=format fails whichever side is explicit."""
        _, module, tmp = env
        out = module.export_scene(str(tmp / "scene.obj"), format="fbx")
        assert out["error"]["code"] == "invalid_format"
        out = module.export_scene(str(tmp / "scene.fbx"), format="usd")
        assert out["error"]["code"] == "invalid_format"
        # and an unrecognized extension still conflicts with an explicit format
        out = module.export_scene(str(tmp / "scene.ma"), format="obj")
        assert out["error"]["code"] == "invalid_format"

    def test_invalid_format_value(self, env):
        _, module, tmp = env
        out = module.export_scene(str(tmp / "scene.abc"), format="abc")
        assert out["error"]["code"] == "invalid_format"

    def test_no_format_no_extension_errors(self, env):
        _, module, tmp = env
        out = module.export_scene(str(tmp / "scene"))
        assert out["error"]["code"] == "invalid_format"

    def test_no_format_unknown_extension_errors(self, env):
        _, module, tmp = env
        out = module.export_scene(str(tmp / "scene.ma"))
        assert out["error"]["code"] == "invalid_format"


class TestPathHandling:
    def test_missing_path(self, env):
        _, module, _ = env
        for bad in (None, "", "   "):
            out = module.export_scene(bad, format="fbx")
            assert out["error"]["code"] == "invalid_path"

    def test_parent_dir_auto_created(self, env):
        _, module, tmp = env
        target = tmp / "deep" / "nested" / "dir" / "scene.fbx"
        out = module.export_scene(str(target))
        assert "error" not in out, out
        assert target.exists()

    def test_exists_rejected_without_overwrite(self, env):
        _, module, tmp = env
        target = tmp / "scene.fbx"
        target.write_bytes(b"OLD")
        out = module.export_scene(str(target))
        assert out["error"]["code"] == "invalid_path"
        assert target.read_bytes() == b"OLD"

    def test_overwrite_replaces_existing(self, env):
        _, module, tmp = env
        target = tmp / "scene.fbx"
        target.write_bytes(b"OLD")
        out = module.export_scene(str(target), overwrite=True)
        assert "error" not in out, out
        assert target.read_bytes() != b"OLD"

    def test_normalized_absolute_returned(self, env):
        _, module, tmp = env
        out = module.export_scene(str(tmp / "sub" / ".." / "scene.fbx"))
        assert "error" not in out, out
        assert ".." not in out["path"]
        assert out["path"] == str(tmp / "scene.fbx")


class TestObjectsExport:
    def test_none_exports_all_via_export_all(self, env):
        scene, module, tmp = env
        out = module.export_scene(str(tmp / "all.fbx"))
        assert "error" not in out, out
        call = _calls(env)[-1]
        assert call["kwargs"]["exportAll"] is True
        assert out["objects_exported"] == len(
            [n for n in scene.scene.all_nodes() if n.parent is None]
        )
        assert out["objects_exported"] == 2

    def test_list_exports_via_export_selected(self, env):
        scene, module, tmp = env
        out = module.export_scene(str(tmp / "sel.fbx"), objects=["GEO_box"])
        assert "error" not in out, out
        call = _calls(env)[-1]
        assert call["kwargs"]["exportSelected"] is True
        assert out["objects_exported"] == 1
        payload = json.loads((tmp / "sel.fbx").read_text().split("\n", 1)[1])
        assert payload["exported"] == ["GEO_box"]

    def test_selection_restored_on_success(self, env):
        scene, module, tmp = env
        scene.cmds.select(["GEO_ball"])
        module.export_scene(str(tmp / "sel.fbx"), objects=["GEO_box"])
        assert scene.scene.selection == ["GEO_ball"]

    def test_selection_restored_on_export_failure(self, env, monkeypatch):
        scene, module, tmp = env
        scene.cmds.select(["GEO_ball"])

        def boom(*a, **k):
            raise RuntimeError("disk full")

        monkeypatch.setattr(scene.cmds, "file", boom)
        out = module.export_scene(str(tmp / "sel.fbx"), objects=["GEO_box"])
        assert out["error"]["code"] == "export_failed"
        assert scene.scene.selection == ["GEO_ball"]

    def test_empty_selection_cleared_and_restored(self, env):
        scene, module, tmp = env
        # nothing selected beforehand -> post-export selection is empty
        module.export_scene(str(tmp / "sel.fbx"), objects=["GEO_box"])
        assert scene.scene.selection == []

    def test_missing_object_aborts_no_partial(self, env):
        scene, module, tmp = env
        out = module.export_scene(str(tmp / "sel.fbx"), objects=["GEO_box", "GEO_ghost"])
        assert out["error"]["code"] == "missing_objects"
        assert "GEO_ghost" in out["error"]["message"]
        assert not (tmp / "sel.fbx").exists()
        assert scene.scene.selection == []

    def test_empty_objects_list(self, env):
        _, module, tmp = env
        out = module.export_scene(str(tmp / "sel.fbx"), objects=[])
        assert out["error"]["code"] == "empty_objects"

    def test_non_list_objects(self, env):
        _, module, tmp = env
        out = module.export_scene(str(tmp / "sel.fbx"), objects="GEO_box")
        assert out["error"]["code"] == "empty_objects"


class TestPluginAndFlags:
    def test_missing_plugin_is_domain_error(self, env):
        scene, module, tmp = env
        scene.scene.plugins_available.discard("objExport")
        scene.scene.loaded_plugins.discard("objExport")
        out = module.export_scene(str(tmp / "scene.obj"))
        assert out["error"]["code"] == "plugin_missing"

    def test_unloaded_plugin_auto_loaded_with_warning(self, env):
        scene, module, tmp = env
        scene.scene.plugins_available.add("objExport")
        scene.scene.loaded_plugins.discard("objExport")
        out = module.export_scene(str(tmp / "scene.obj"))
        assert "error" not in out, out
        assert "objExport" in scene.scene.loaded_plugins
        assert any("objExport" in w for w in out["warnings"])

    def test_prompt_false_and_force_pinned(self, env):
        _, module, tmp = env
        module.export_scene(str(tmp / "a.fbx"))
        module.export_scene(str(tmp / "b.fbx"), objects=["GEO_box"])
        for call in _calls(env)[-2:]:
            assert call["kwargs"]["prompt"] is False
            assert call["kwargs"]["force"] is True

    def test_modified_flag_untouched(self, env):
        scene, module, tmp = env
        module.export_scene(str(tmp / "a.fbx"), objects=["GEO_box"])
        assert scene.scene.modified is False
        scene.scene.modified = True
        module.export_scene(str(tmp / "b.fbx"))
        assert scene.scene.modified is True


class TestResultShape:
    def test_result_contract(self, env):
        _, module, tmp = env
        out = module.export_scene(str(tmp / "scene.fbx"))
        assert set(out) == {
            "path",
            "format",
            "objects_exported",
            "size_bytes",
            "duration_ms",
            "warnings",
        }
        assert isinstance(out["objects_exported"], int)
        assert out["size_bytes"] == (tmp / "scene.fbx").stat().st_size
        assert out["size_bytes"] > 0
        assert isinstance(out["duration_ms"], float)
        assert out["duration_ms"] >= 0.0
        assert isinstance(out["warnings"], list)

    def test_zero_byte_export_warns(self, env, monkeypatch):
        scene, module, tmp = env
        target = tmp / "empty.fbx"
        target.write_bytes(b"")

        def fake_file(*a, **k):
            target.touch()  # exporter "succeeds" but writes nothing

        monkeypatch.setattr(scene.cmds, "file", fake_file)
        out = module.export_scene(str(target), overwrite=True)
        assert "error" not in out, out
        assert "0-byte" in out["warnings"][0]
