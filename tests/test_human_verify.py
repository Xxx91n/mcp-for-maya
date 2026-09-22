"""human_verify tier (D-049a): the versioned manual checklist.

Each test exists so ``pytest --collect-only -m human_verify`` enumerates
the human-eye acceptance list and ``-s`` prints the manual steps. They
never assert — a fake red/green on viewport state is worse than an
honestly-skipped box. Terminal state is always SKIP with the steps
printed; a human ticks the upstream checklist after doing them.
"""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.human_verify


def _steps(*lines: str) -> None:
    print("\nMANUAL CHECK — do this in the live GUI session, then tick upstream:")
    for line in lines:
        print("  " + line)


def test_viewport_snapshot_orientation():
    """verticalFlip direction (testing.md Tier-3): image must be
    right-side-up, not mirrored vertically."""
    _steps(
        "call scene_viewport_snapshot on a scene with asymmetric content",
        "open the returned image: text/logos read normally, ground is DOWN",
        "if upside-down, the verticalFlip() in visual_module is wrong",
    )
    pytest.skip("human-eye check — steps printed above")


def test_viewport_snapshot_matches_active_view():
    """WYSIWYG contract: HUD/selection ornaments visible in capture."""
    _steps(
        "select an object and enable a viewport HUD, then snapshot",
        "capture shows the selection highlight + HUD (feature, not bug)",
        "content must match what the artist currently sees",
    )
    pytest.skip("human-eye check — steps printed above")


def test_viewport_snapshot_vp2_nonblack():
    """VP2 kFloat path produces a non-black image (official patch).

    Maya 2024 verified locally; 2025/2026 coverage is PARTIAL until a
    machine with those versions runs this."""
    _steps(
        "snapshot on a VP2 viewport with lit content",
        "image is not all-black (kFloat -> kByte conversion worked)",
        "NOTE: only Maya 2024 covered on this machine; 2025/2026 = partial",
    )
    pytest.skip("human-eye check — steps printed above")


def test_render_preview_framing_matches_camera():
    """playblast output matches the requested camera's framing."""
    _steps(
        "render_preview(camera=X), then compare the image to a manual",
        "lookThru X capture — framing must match the camera, not the",
        "whatever panel happened to be active",
    )
    pytest.skip("human-eye check — steps printed above")


def test_multi_client_imagecontent_rendering():
    """D-025: [ImageContent, TextContent] renders in multiple MCP clients.

    Devin/1mcp seat is agent-covered; Inspector / Claude Code / Codex
    seats are BLOCKED pending user environment."""
    _steps(
        "call scene_viewport_snapshot + scene_render_preview via each client",
        "Devin (1mcp): verified by agent reading ImageContent this round",
        "Inspector / Claude Code / Codex: BLOCKED — needs user environment",
    )
    pytest.skip("multi-client seats beyond Devin are blocked on user env")


def test_modelpanel_camera_flag_2025_2026():
    """modelPanel -camera call form on Maya 2025/2026 (D-039 follow-up).

    Verified on 2024 this round; newer versions are PARTIAL until run."""
    _steps(
        "on Maya 2025 and 2026: render_preview(camera=X) switches and",
        "restores the panel camera correctly (no lookThru fallback path)",
        "this box only has Maya 2024 — mark partial until then",
    )
    pytest.skip("needs Maya 2025/2026 — partial on this machine")


def test_callform_checklist_gui_tier():
    """D-056②: the viewport-dependent call-form checklist, versioned.

    Official signatures + verdicts live in docs/visual-callform-matrix.md
    (evidence layer); docs/testing.md Tier-3 holds the same list. The
    machine-assertable subset runs under `pytest -m gui` as
    test_callform_surface_probe — this entry keeps the eyeball tier
    honest about what it covers."""
    _steps(
        "cmds.getPanel(withFocus=True) -> str|None; may return a",
        "  non-modelPanel — confirm via objectTypeUI == 'modelEditor'",
        "cmds.getPanel(type='modelPanel') -> list of str",
        "cmds.modelPanel(p, q, camera) -> str; e+camera -> None; ex -> bool",
        "cmds.modelEditor(ed, q, camera/activeView) -> str/bool",
        "cmds.lsUI(editors=True) -> list; objectTypeUI(name) -> str",
        "cmds.currentTime(q) -> float; currentTime(v, edit) -> None",
        "cmds.refresh(force=True) -> None",
        "M3dView.getRendererName() -> 'vp2Renderer' under VP2",
        "cmds.playblast(completeFilename=F, frame=[t]) -> F verbatim",
        "om.MImage.floatPixels() -> pointer (long), wrapped via MScriptUtil",
    )
    pytest.skip("human-eye check — steps printed above")


def test_callform_checklist_mayapy_tier():
    """D-056②: viewport-independent call forms are booked to mayapy —
    skeleton asserts exist in test_mayapy_smoke.py and run whenever a
    healthy interpreter is available (env-blocked on this box)."""
    _steps(
        "run mayapy -m pytest tests/ -m mayapy on a healthy box",
        "cmds.camera(name=X) -> [transform, shape] list",
        "cmds.ls(type='camera') -> includes 'perspShape' shape",
        "cmds.file(rename=X)+sceneName — rename+prompt form (0.1.1 hang)",
        "MSelectionList.add('*') pulls non-DAG -> getDagPath TypeError",
        "cmds.about(batch=True) -> True under mayapy",
    )
    pytest.skip("mayapy env-blocked on this box — booked, not claimed")
