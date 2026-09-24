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

    def test_force_reimport_leaves_no_dg_orphans(self, asset_env):
        asset_env.module.import_asset(asset_env.descriptor)
        asset_env.module.import_asset(asset_env.descriptor, force=True)
        # a leaked first-import shading net (file_*/MAT_*/SG_* helpers,
        # FBX materials) resurfaces as auto-suffixed duplicates: name
        # ends in digits AND its stripped base name still exists
        names = asset_env.cmds.ls() or []
        leaked = [
            n for n in names if n != n.rstrip("0123456789") and n.rstrip("0123456789") in names
        ]
        assert not leaked, f"DG orphans leaked on force re-import: {leaked}"


# ------------------------------------------------------------------
# polycount gate
# ------------------------------------------------------------------


class TestPolycountGate:
    def test_over_limit_rejected_and_deleted(self, asset_env):
        asset_env.scene.fbx_fixture["meshes"][0]["faces"] = 150000
        res = asset_env.module.import_asset(asset_env.descriptor)
        assert res["error"]["code"] == "polycount_exceeded"
        assert "150000" in res["error"]["message"]
        # rejected import must not leave debris behind - neither the
        # DAG group nor its FBX-imported shading net (body/bodySG)
        assert not asset_env.cmds.objExists("GRP_asset_Camera_01")
        assert asset_env.cmds.ls("body") is None
        assert asset_env.cmds.ls("bodySG") is None

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

    def test_arm_wires_ao_to_diffuse(self, asset_env, tmp_path):
        # Live dogfood findings (T-19c): ARM packed map must not connect
        # scalar outColorR into the triple ambientColor - real Maya
        # rejects float -> double3; and ambientColor *adds* light so AO
        # there washes the model flat. AO -> material.diffuse (scalar
        # multiplier) is the legal, semantically correct target.
        arm = tmp_path / "body_arm_1k.jpg"
        arm.write_bytes(b"ARM")
        d = dict(asset_env.descriptor)
        d["texture_parts"] = dict(d["texture_parts"])
        d["texture_parts"]["body"] = dict(d["texture_parts"]["body"])
        d["texture_parts"]["body"]["arm"] = str(arm)
        res = asset_env.module.import_asset(d)
        assert "error" not in res, res
        parts = {p["part"]: p for p in res["texture_wiring"]["parts"]}
        wired = "\n".join(parts["body"]["wired"])
        assert "body_arm->body" in wired
        sc = asset_env.scene
        assert "file_Camera_01_body_arm" in sc.connections.get("|body.diffuse", [])
        f_arm = sc.resolve("file_Camera_01_body_arm")
        assert f_arm.attrs.get("colorSpace") == "Raw"

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
# displacement (D-082b) — graph contract only; render semantics stay
# on the gui/human_verify tier ("connected" != "renders correctly")
# ------------------------------------------------------------------


class TestDisplacement:
    def test_disp_wires_via_imported_sg(self, asset_env, tmp_path):
        """Positive case — live-verified shape (probe-displacement.json):
        file.outAlpha -> disp.displacement -> sg.displacementShader on
        the IMPORTED shading group."""
        disp = tmp_path / "body_disp_1k.jpg"
        disp.write_bytes(b"DISP")
        d = dict(asset_env.descriptor)
        d["texture_parts"] = dict(d["texture_parts"])
        d["texture_parts"]["body"] = dict(d["texture_parts"]["body"])
        d["texture_parts"]["body"]["disp"] = str(disp)
        res = asset_env.module.import_asset(d)
        assert "error" not in res, res
        parts = {p["part"]: p for p in res["texture_wiring"]["parts"]}
        assert "body_disp->body" in "\n".join(parts["body"]["wired"])
        sc = asset_env.scene
        assert sc.resolve("file_Camera_01_body_disp_disp").type == "displacementShader"
        assert "file_Camera_01_body_disp" in sc.connections.get(
            "file_Camera_01_body_disp_disp.displacement", []
        )
        assert "file_Camera_01_body_disp_disp" in sc.connections.get(
            "|bodySG.displacementShader", []
        )

    def test_disp_without_sg_unwired(self, asset_env, tmp_path):
        """Negative case — no shading group to hang the map on: reports
        unwired and creates NO displacementShader node."""
        tex = tmp_path / "x_disp.jpg"
        tex.write_bytes(b"X")
        fn = asset_env.module._file_node(str(tex), "file_nosg", "Raw")
        ok = asset_env.module._wire_map(fn, "displacement", "body", None)
        assert ok is False
        assert not asset_env.cmds.objExists("file_nosg_disp")
        assert asset_env.cmds.ls("*_disp") is None

    def test_disp_connect_failure_leaves_no_orphan(self, asset_env, monkeypatch, tmp_path):
        """D-082b — a connectAttr that dies mid-wiring must delete the
        half-created displacementShader, not orphan it in the scene."""
        tex = tmp_path / "x_disp.jpg"
        tex.write_bytes(b"X")
        asset_env.cmds.sets(renderable=True, empty=True, name="SG_test")
        fn = asset_env.module._file_node(str(tex), "file_orphan", "Raw")
        real_connect = asset_env.cmds.connectAttr

        def boom(src, dst, **kw):
            if str(dst).endswith(".displacementShader"):
                raise RuntimeError("SG.displacementShader not connectable")
            return real_connect(src, dst, **kw)

        monkeypatch.setattr(asset_env.cmds, "connectAttr", boom)
        ok = asset_env.module._wire_map(fn, "displacement", "body", "SG_test")
        assert ok is False
        assert not asset_env.cmds.objExists("file_orphan_disp")


# ------------------------------------------------------------------
# bump2d orphan cleanup (D-083) — same contract as displacement:
# a wiring failure at ANY point after shadingNode must not leave the
# half-created bump2d node behind.
# ------------------------------------------------------------------


class TestBumpOrphan:
    @pytest.mark.parametrize("fail_dst", [".bumpValue", ".normalCamera"])
    def test_bump_connect_failure_leaves_no_orphan(
        self, asset_env, monkeypatch, tmp_path, fail_dst
    ):
        """D-083 — a connectAttr that dies mid-wiring must delete the
        half-created bump2d, on BOTH connect paths (file -> bump and
        bump -> mat.normalCamera)."""
        tex = tmp_path / "x_nor.jpg"
        tex.write_bytes(b"X")
        fn = asset_env.module._file_node(str(tex), "file_orphan", "Raw")
        real_connect = asset_env.cmds.connectAttr

        def boom(src, dst, **kw):
            if str(dst).endswith(fail_dst):
                raise RuntimeError(f"{fail_dst} not connectable")
            return real_connect(src, dst, **kw)

        monkeypatch.setattr(asset_env.cmds, "connectAttr", boom)
        ok = asset_env.module._wire_map(fn, "normal", "body", None)
        assert ok is False
        assert not asset_env.cmds.objExists("file_orphan_bump")

    def test_bump_setattr_failure_leaves_no_orphan(self, asset_env, monkeypatch, tmp_path):
        """D-083 — setAttr(bumpInterp) dying between node creation and
        wiring must still delete the bump2d."""
        tex = tmp_path / "x_nor.jpg"
        tex.write_bytes(b"X")
        fn = asset_env.module._file_node(str(tex), "file_orphan", "Raw")
        real_setattr = asset_env.cmds.setAttr

        def boom(ref, *a, **kw):
            if str(ref).endswith(".bumpInterp"):
                raise RuntimeError("bumpInterp not settable")
            return real_setattr(ref, *a, **kw)

        monkeypatch.setattr(asset_env.cmds, "setAttr", boom)
        ok = asset_env.module._wire_map(fn, "normal", "body", None)
        assert ok is False
        assert not asset_env.cmds.objExists("file_orphan_bump")

    def test_bump_no_normalcamera_creates_nothing(self, asset_env, tmp_path):
        """Early-return path — a material without normalCamera reports
        unwired and creates NO bump2d node (mirrors the no-SG disp case)."""
        tex = tmp_path / "x_nor.jpg"
        tex.write_bytes(b"X")
        fn = asset_env.module._file_node(str(tex), "file_orphan", "Raw")
        ok = asset_env.module._wire_map(fn, "normal", "no_such_mat", None)
        assert ok is False
        assert not asset_env.cmds.objExists("file_orphan_bump")
        assert asset_env.cmds.ls("*_bump") is None


# ------------------------------------------------------------------
# standardSurface migration (D-082e) — attribute-aware mapping
# ------------------------------------------------------------------


class TestStandardSurface:
    def test_new_material_is_standard_surface(self, asset_env, tmp_path):
        """D-082e: _new_material creates standardSurface, not blinn —
        and the maps wire to the PBR attribute names."""
        extra = tmp_path / "strap_metallic_1k.jpg"
        extra.write_bytes(b"METL")
        d = dict(asset_env.descriptor)
        d["texture_parts"] = dict(d["texture_parts"])
        d["texture_parts"]["strap"] = {"metallic": str(extra)}
        res = asset_env.module.import_asset(d)
        assert "error" not in res, res
        mat = asset_env.scene.resolve("MAT_Camera_01_strap")
        assert mat.type == "standardSurface"
        # metallic lands on .metalness (PBR name), not reflectivity
        assert "file_Camera_01_strap_metallic" in asset_env.scene.connections.get(
            "MAT_Camera_01_strap.metalness", []
        )

    def test_ao_wires_to_base_on_standard_surface(self, asset_env, tmp_path):
        """AO drives a multiplier: standardSurface.base is the scalar
        weight over baseColor (legacy shaders still get .diffuse)."""
        ao = tmp_path / "strap_ao_1k.jpg"
        ao.write_bytes(b"AO")
        d = dict(asset_env.descriptor)
        d["texture_parts"] = dict(d["texture_parts"])
        d["texture_parts"]["strap"] = {"ao": str(ao)}
        res = asset_env.module.import_asset(d)
        assert "error" not in res, res
        assert "file_Camera_01_strap_ao" in asset_env.scene.connections.get(
            "MAT_Camera_01_strap.base", []
        )

    def test_metalness_never_wires_reflectivity(self, asset_env, tmp_path):
        """D-082e: on a legacy blinn (which DOES have reflectivity — live
        probe), a metalness map must stay unwired, never land on
        reflectivity. Specular strength is not metalness."""
        asset_env.scene.fbx_fixture["materials"][0]["type"] = "blinn"
        met = tmp_path / "body_metallic_1k.jpg"
        met.write_bytes(b"MET")
        d = dict(asset_env.descriptor)
        d["texture_parts"] = dict(d["texture_parts"])
        d["texture_parts"]["body"] = {"metallic": str(met)}
        res = asset_env.module.import_asset(d)
        assert "error" not in res, res
        parts = {p["part"]: p for p in res["texture_wiring"]["parts"]}
        assert "body_metallic->body" in parts["body"]["unwired"]
        sc = asset_env.scene
        assert sc.resolve("body").attrs.get("reflectivity") is not None  # fixture sanity
        assert "file_Camera_01_body_metallic" not in sc.connections.get("|body.reflectivity", [])


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
