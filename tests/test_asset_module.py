"""T-19a tests: _mcp_asset Maya-side importer (D-074/D-075).

Runs the real asset_module against the stub scene: the fbx_fixture
teaches the stub what 'the FBX contained', so the tests verify the
importer's own logic - plugin gate, unit globals, diff/group, polycount
gate, texture wiring, dedup, dims sanity - not the FBX binary itself
(that is the real-Maya window's job).
"""

from __future__ import annotations

from types import SimpleNamespace

import maya_stub
import pytest


@pytest.fixture
def asset_env(maya_env, tmp_path):
    """Stub scene + bound _mcp_asset + on-disk descriptor files."""
    module = maya_stub.load_asset_module()

    fbx = tmp_path / "Camera_01_1k.fbx"
    fbx.write_bytes(b"FBX!!")
    tex = tmp_path / "body_diff_1k.jpg"
    tex.write_bytes(b"DIFF")
    nor = tmp_path / "body_nor_gl_1k.jpg"
    nor.write_bytes(b"NGL")

    descriptor = {
        "asset_id": "Camera_01",
        "resolution": "1k",
        "fbx_path": str(fbx),
        "texture_parts": {
            "body": {"diff": str(tex), "nor_gl": str(nor)},
        },
        "license": "CC0-1.0",
        "source": "download",
    }

    maya_env.scene.fbx_fixture = {
        "materials": [{"name": "body", "type": "phong"}],
        "meshes": [
            {"name": "Camera_01_body", "faces": 1200, "material": "body"},
        ],
    }
    return SimpleNamespace(
        scene=maya_env.scene,
        cmds=maya_env.cmds,
        module=module,
        descriptor=descriptor,
        tmp_path=tmp_path,
    )


# ------------------------------------------------------------------
# happy path
# ------------------------------------------------------------------


class TestImportHappyPath:
    def test_import_groups_and_reports(self, asset_env):
        res = asset_env.module.import_asset(asset_env.descriptor)
        assert "error" not in res, res
        assert res["group"].startswith("GRP_asset_Camera_01")
        assert res["meshes"] == 1
        assert res["polycount"] == 1200
        assert res["license"] == "CC0-1.0"
        assert res["source"] == "download"
        assert res["bbox"] is not None
        # group really exists and parents the mesh
        assert asset_env.cmds.objExists(res["group"])
        parent = asset_env.cmds.listRelatives("|" + res["group"] + "|Camera_01_body", parent=True)
        assert parent == [res["group"]]

    def test_unit_globals_set_via_mel(self, asset_env):
        asset_env.module.import_asset(asset_env.descriptor)
        assert any("FBXImportConvertUnitString m" in c for c in asset_env.scene.mel_calls), (
            asset_env.scene.mel_calls
        )

    def test_plugin_load_idempotent(self, asset_env):
        asset_env.scene.loaded_plugins = set()  # present but unloaded
        res = asset_env.module.import_asset(asset_env.descriptor)
        assert "error" not in res, res
        assert "fbxmaya" in asset_env.scene.loaded_plugins
        # second import path: plugin already loaded, no re-load needed

    def test_plugin_unavailable_is_domain_error(self, asset_env):
        asset_env.scene.loaded_plugins = set()
        asset_env.scene.plugins_available = set()
        res = asset_env.module.import_asset(asset_env.descriptor)
        assert res["error"]["code"] == "plugin_unavailable"

    def test_import_failed_is_domain_error(self, asset_env):
        asset_env.scene.fbx_fixture_error = "corrupt FBX header"
        res = asset_env.module.import_asset(asset_env.descriptor)
        assert res["error"]["code"] == "import_failed"
        assert "corrupt FBX header" in res["error"]["message"]

    def test_empty_import_is_domain_error(self, asset_env):
        asset_env.scene.fbx_fixture = None
        res = asset_env.module.import_asset(asset_env.descriptor)
        assert res["error"]["code"] == "import_empty"

    def test_missing_fbx_path_is_domain_error(self, asset_env):
        d = dict(asset_env.descriptor)
        d["fbx_path"] = str(asset_env.tmp_path / "nonexistent.fbx")
        res = asset_env.module.import_asset(d)
        assert res["error"]["code"] == "files_missing"


# ------------------------------------------------------------------
# dedup (idempotentHint depends on it)
# ------------------------------------------------------------------


class TestDedup:
    def test_second_call_dedupes(self, asset_env):
        res1 = asset_env.module.import_asset(asset_env.descriptor)
        res2 = asset_env.module.import_asset(asset_env.descriptor)
        assert res2.get("deduped") is True
        assert res2["group"] == res1["group"]
        # still exactly one group + one mesh
        assert len(asset_env.scene.transforms()) == 2  # grp + mesh tr

    def test_force_reimports(self, asset_env):
        asset_env.module.import_asset(asset_env.descriptor)
        res = asset_env.module.import_asset(asset_env.descriptor, force=True)
        assert res.get("deduped") is not True
        assert res["group"].startswith("GRP_asset_Camera_01")


# ------------------------------------------------------------------
# polycount gate
# ------------------------------------------------------------------


class TestPolycountGate:
    def test_over_limit_rejected_and_deleted(self, asset_env):
        asset_env.scene.fbx_fixture["meshes"][0]["faces"] = 150000
        res = asset_env.module.import_asset(asset_env.descriptor)
        assert res["error"]["code"] == "polycount_exceeded"
        assert "150000" in res["error"]["message"]
        # rejected import must not leave debris behind
        assert not asset_env.cmds.objExists("GRP_asset_Camera_01")

    def test_override_keeps_import(self, asset_env):
        asset_env.scene.fbx_fixture["meshes"][0]["faces"] = 150000
        res = asset_env.module.import_asset(asset_env.descriptor, allow_high_polycount=True)
        assert "error" not in res, res
        assert res["polycount"] == 150000


# ------------------------------------------------------------------
# texture wiring
# ------------------------------------------------------------------


class TestTextureWiring:
    def test_diff_and_normal_wired(self, asset_env):
        res = asset_env.module.import_asset(asset_env.descriptor)
        assert "error" not in res, res
        parts = res["texture_wiring"]["parts"]
        body = next(p for p in parts if p["part"] == "body")
        assert body["materials"] == ["body"]
        wired = "\n".join(body["wired"])
        assert "body_diff->body" in wired
        assert "body_nor_gl->body" in wired

        sc = asset_env.scene
        # file node for diff exists, sRGB, connected to material.color
        f_diff = sc.resolve("file_Camera_01_body_diff")
        assert f_diff.attrs.get("colorSpace") == "sRGB"
        assert "file_Camera_01_body_diff" in sc.connections.get(
            "|body.color",
            [],  # DG material sits at root -> long name key
        )
        # normal goes through a bump2d into normalCamera
        bump_targets = [k for k in sc.connections if k.endswith(".bumpValue")]
        assert bump_targets, sc.connections
        bump_node = bump_targets[0].split(".")[0]
        assert sc.resolve(bump_node).type == "bump2d"
        assert "file_Camera_01_body_nor_gl" in sc.connections[bump_targets[0]]
        assert bump_node in [c for c in sc.connections.get("|body.normalCamera", [])]
        # normal map file is Raw, not sRGB
        f_nor = sc.resolve("file_Camera_01_body_nor_gl")
        assert f_nor.attrs.get("colorSpace") == "Raw"

    def test_unmatched_part_creates_material_and_assigns(self, asset_env, tmp_path):
        # a second texture family with no matching imported material
        extra = tmp_path / "strap_metallic_1k.jpg"
        extra.write_bytes(b"METL")
        d = dict(asset_env.descriptor)
        d["texture_parts"] = dict(d["texture_parts"])
        d["texture_parts"]["strap"] = {"metallic": str(extra)}
        res = asset_env.module.import_asset(d)
        assert "error" not in res, res
        parts = {p["part"]: p for p in res["texture_wiring"]["parts"]}
        strap = parts["strap"]
        assert strap["materials"] == ["MAT_Camera_01_strap"]
        # strap meshes don't exist in the fixture -> no assignments
        assert strap["assigned"] == []
        # dedicated material + SG really exist
        assert asset_env.cmds.objExists("MAT_Camera_01_strap")
        assert asset_env.cmds.objExists("SG_Camera_01_strap")

    def test_missing_texture_file_unwired(self, asset_env):
        d = dict(asset_env.descriptor)
        d["texture_parts"] = {"body": {"diff": str(asset_env.tmp_path / "gone.jpg")}}
        res = asset_env.module.import_asset(d)
        assert "error" not in res, res
        body = res["texture_wiring"]["parts"][0]
        assert body["wired"] == []
        assert body["unwired"] == ["body_diff"]


# ------------------------------------------------------------------
# defensive input
# ------------------------------------------------------------------


class TestDefensive:
    def test_bad_descriptor_type(self, asset_env):
        res = asset_env.module.import_asset("not-a-dict")
        assert res["error"]["code"] == "bad_descriptor"

    def test_descriptor_missing_fbx_path(self, asset_env):
        res = asset_env.module.import_asset({"asset_id": "x"})
        assert res["error"]["code"] == "bad_descriptor"

    def test_never_raises_on_odd_input(self, asset_env):
        res = asset_env.module.import_asset(None)
        assert "error" in res
