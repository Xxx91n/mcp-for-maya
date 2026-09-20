"""Real-Maya smoke tests — mayapy tier only.

Run inside a real Maya interpreter:

    set PYTHONPATH=<repo>\src;<repo>\tests
    mayapy -m pytest tests/ -m mayapy

Under vanilla python (or the stub) these skip — they exist so docs/testing.md
describes a real tier, not a hypothetical one.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.mayapy


@pytest.fixture(scope="session", autouse=True)
def _maya_standalone_init():
    """mayapy hard-crashes (Windows access violation) if maya.api.OpenMaya
    is imported before maya.standalone.initialize() — initialize once per
    tier run. Under vanilla python / the stub the import fails and this
    is a no-op; the real_maya fixture still gates the tests."""
    try:
        import maya.standalone
    except ImportError:
        return
    maya.standalone.initialize()


@pytest.fixture
def real_maya():
    cmds = pytest.importorskip("maya.cmds", reason="requires real Maya (mayapy)")
    f = getattr(cmds, "__file__", "") or ""
    if "maya_stub" in f or "tests" in f.replace("\\", "/"):
        pytest.skip("maya stub is installed — mayapy tier needs a real interpreter")
    return cmds


def test_scene_graph_runs_in_real_maya(real_maya):
    import maya_mcp_server.maya_scene_module as m

    real_maya.polyCube(name="GEO_probe")
    res = m.get_scene_graph("compact")
    assert "stats" in res
    assert res["stats"]["total"] >= 1


def test_measure_roundtrip_in_real_maya(real_maya):
    import maya_mcp_server.maya_scene_module as m

    a = real_maya.polyCube(name="GEO_a")[0]
    b = real_maya.polyCube(name="GEO_b")[0]
    real_maya.move(100, 0, 0, b)
    res = m.measure(a, b, "center")
    assert res["distance"] == pytest.approx(100, abs=0.01)


def test_checkpoint_rollback_reference_edit_roundtrip(real_maya, tmp_path):
    """ADR-0004/D-007: checkpoint->rollback roundtrip on a scene carrying a
    reference edit. exportAll flattens references into a self-contained
    snapshot; rollback must restore that state and rebind to the original
    scene path (S2). Manual tier — never CI.
    """
    import maya_mcp_server.maya_scene_module as m

    cmds = real_maya

    # referenced file with one cube
    ref_file = tmp_path / "ref_source.ma"
    cmds.polyCube(name="GEO_ref_cube")
    cmds.file(rename=str(ref_file))
    cmds.file(save=True, type="mayaAscii", force=True, prompt=False)
    cmds.file(new=True, force=True, prompt=False)

    # main scene references it, then a reference edit moves the node
    main_file = tmp_path / "main.ma"
    cmds.file(rename=str(main_file))
    cmds.file(str(ref_file), reference=True, namespace="t03ref", prompt=False)
    ref_node = "t03ref:GEO_ref_cube"
    assert cmds.objExists(ref_node)
    cmds.move(5, 0, 0, ref_node)  # the reference edit
    cmds.file(save=True, type="mayaAscii", force=True, prompt=False)

    res = m.save_checkpoint("with_ref")
    assert "error" not in res, res

    # mutate after checkpoint
    cmds.polyCube(name="GEO_after")

    rb = m.rollback_to_checkpoint(res["filename"])
    assert rb["success"] is True, rb
    assert rb["scene_name_after"] == str(main_file) or rb["scene_name_after"].endswith("main.ma")
    assert rb["scene_rebound_to"] is not None
    assert rb["safety_snapshot"] != "skipped_by_user"
    assert not cmds.objExists("GEO_after")
    # flattened reference content must survive the roundtrip.
    # Live-verified glob semantics: * never crosses the namespace
    # colon on real Maya — check both the flattened and the
    # still-namespaced shapes.
    survivors = (cmds.ls("*GEO_ref_cube*") or []) + (cmds.ls("*:*GEO_ref_cube*") or [])
    assert survivors, "referenced node content lost after rollback"


def test_visual_module_batch_gate_in_real_maya(real_maya):
    """D-024/D-025: mayapy is batch mode — the module must import cleanly
    inside a real interpreter and return the gui_session_required domain
    error rather than exploding on missing GUI deps.
    """
    import maya_mcp_server.visual_module as vm

    for fn in (vm.viewport_snapshot, vm.render_preview):
        res = fn()
        assert "error" in res, res
        assert res["error"]["code"] == "gui_session_required", res
        assert "suggestion" in res["error"]
