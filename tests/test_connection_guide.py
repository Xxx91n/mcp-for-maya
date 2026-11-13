"""Tests for connection_guide module \u2014 incl. D-017 A' managed-block semantics."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from maya_mcp_server.connection_guide import (
    DEFAULT_COMMAND_PORT,
    MARKER_BEGIN,
    MARKER_END,
    MayaInstallInfo,
    _marker_block,
    find_maya_installations,
    generate_user_setup_content,
    get_agent_connection_instructions,
    get_connection_diagnostics,
    get_fallback_instructions,
    install_user_setup,
    uninstall_user_setup,
)
from maya_mcp_server.utils import get_platform


def _install(tmp_path: Path, name: str = "userSetup.py") -> MayaInstallInfo:
    """A fake installation rooted under tmp_path."""
    scripts_dir = tmp_path / "2024" / "scripts"
    scripts_dir.mkdir(parents=True)
    return MayaInstallInfo(
        version="2024",
        scripts_dir=scripts_dir,
        user_setup_path=scripts_dir / name,
        platform="windows",
        maya_app_dir=str(tmp_path),
        is_valid=True,
        notes=["test"],
    )


class TestPlatformDetection:
    """Platform detection delegates to utils.get_platform."""

    def test_get_platform_returns_string(self):
        result = get_platform()
        assert isinstance(result, str)
        assert result in ("windows", "linux", "macos")

    @patch("maya_mcp_server.utils.platform")
    def test_get_platform_windows(self, mock_platform):
        mock_platform.system.return_value = "Windows"
        assert get_platform() == "windows"

    @patch("maya_mcp_server.utils.platform")
    def test_get_platform_linux(self, mock_platform):
        mock_platform.system.return_value = "Linux"
        assert get_platform() == "linux"

    @patch("maya_mcp_server.utils.platform")
    def test_get_platform_macos(self, mock_platform):
        mock_platform.system.return_value = "Darwin"
        assert get_platform() == "macos"


class TestMarkerBlock:
    """The managed block itself (D-017)."""

    def test_has_both_markers(self):
        block = _marker_block(7001)
        assert MARKER_BEGIN in block
        assert MARKER_END in block
        assert block.index(MARKER_BEGIN) < block.index(MARKER_END)

    def test_is_valid_python(self):
        compile(_marker_block(7001), "<block>", "exec")

    def test_self_protecting(self):
        block = _marker_block(7001)
        assert "try:" in block and "except" in block

    def test_idempotent_port_check(self):
        block = _marker_block(7001)
        assert "listPorts" in block  # checks existing ports first

    def test_uses_evaldeferred(self):
        assert "evalDeferred" in _marker_block(7001)

    def test_custom_port(self):
        block = _marker_block(9999)
        assert "9999" in block and ":9999" in block

    def test_generate_content_equals_block(self):
        """Manual block == tool-written content, byte-identical (D-017)."""
        assert generate_user_setup_content(7001) == _marker_block(7001)


class TestInstallMarkerBlock:
    """install_user_setup A' semantics."""

    def test_missing_file_created_directly(self, tmp_path):
        fake = _install(tmp_path)
        with patch(
            "maya_mcp_server.connection_guide.find_maya_installations",
            return_value=[fake],
        ):
            res = install_user_setup(port=7001)
        entry = res["results"][0]
        assert res["success"] is True
        assert entry["action"] == "created"
        content = fake.user_setup_path.read_text(encoding="utf-8")
        assert content == _marker_block(7001)

    def test_existing_no_marker_needs_confirm(self, tmp_path):
        fake = _install(tmp_path)
        fake.user_setup_path.write_text("# user's own code\n", encoding="utf-8")
        with patch(
            "maya_mcp_server.connection_guide.find_maya_installations",
            return_value=[fake],
        ):
            res = install_user_setup(port=7001)
        entry = res["results"][0]
        assert entry["action"] == "needs_confirm"
        assert entry["success"] is False
        # nothing written, no backup yet
        assert fake.user_setup_path.read_text() == "# user's own code\n"
        assert not list(fake.scripts_dir.glob("*.bak.*"))
        assert entry["proposed_block"] == _marker_block(7001)

    def test_existing_no_marker_confirm_merges(self, tmp_path):
        fake = _install(tmp_path)
        fake.user_setup_path.write_text("# user's own code\n", encoding="utf-8")
        with patch(
            "maya_mcp_server.connection_guide.find_maya_installations",
            return_value=[fake],
        ):
            res = install_user_setup(port=7001, confirm=True)
        entry = res["results"][0]
        assert entry["action"] == "merged"
        assert entry["success"] is True
        content = fake.user_setup_path.read_text(encoding="utf-8")
        assert content.startswith("# user's own code")
        assert MARKER_BEGIN in content and MARKER_END in content
        # backup written and preserves original
        bak = Path(entry["backup"])
        assert bak.exists() and bak.name.startswith("userSetup.py.bak.")
        assert bak.read_text(encoding="utf-8") == "# user's own code\n"

    def test_existing_marker_replaced_in_place(self, tmp_path):
        fake = _install(tmp_path)
        old = "# header\n" + _marker_block(7001) + "# footer stays\n"
        fake.user_setup_path.write_text(old, encoding="utf-8")
        with patch(
            "maya_mcp_server.connection_guide.find_maya_installations",
            return_value=[fake],
        ):
            res = install_user_setup(port=9999)
        entry = res["results"][0]
        assert entry["action"] == "updated"
        content = fake.user_setup_path.read_text(encoding="utf-8")
        assert "9999" in content and ":9999" in content
        assert content.startswith("# header")
        assert content.rstrip().endswith("# footer stays")
        assert Path(entry["backup"]).exists()

    def test_existing_marker_idempotent(self, tmp_path):
        fake = _install(tmp_path)
        fake.user_setup_path.write_text(_marker_block(7001), encoding="utf-8")
        with patch(
            "maya_mcp_server.connection_guide.find_maya_installations",
            return_value=[fake],
        ):
            res = install_user_setup(port=7001)
        assert res["results"][0]["action"] == "already_current"

    def test_unparseable_file_refused(self, tmp_path):
        fake = _install(tmp_path)
        fake.user_setup_path.write_text("def broken(\n", encoding="utf-8")
        with patch(
            "maya_mcp_server.connection_guide.find_maya_installations",
            return_value=[fake],
        ):
            res = install_user_setup(port=7001, confirm=True)
        entry = res["results"][0]
        assert entry["action"] == "refused"
        assert entry["error"]["code"] == "unparseable_file"
        assert "fallback" in entry
        assert fake.user_setup_path.read_text() == "def broken(\n"

    def test_unterminated_marker_refused(self, tmp_path):
        fake = _install(tmp_path)
        fake.user_setup_path.write_text(f"x = 1\n{MARKER_BEGIN}\nstuff\n", encoding="utf-8")
        with patch(
            "maya_mcp_server.connection_guide.find_maya_installations",
            return_value=[fake],
        ):
            res = install_user_setup(port=7001, confirm=True)
        entry = res["results"][0]
        assert entry["action"] == "refused"
        assert entry["error"]["code"] == "unterminated_marker"

    def test_dry_run_reports_intent(self, tmp_path):
        fake = _install(tmp_path)
        with patch(
            "maya_mcp_server.connection_guide.find_maya_installations",
            return_value=[fake],
        ):
            res = install_user_setup(port=7001, dry_run=True)
        assert res["results"][0]["action"] == "would_create"
        assert not fake.user_setup_path.exists()

    def test_no_maya_found_error_shape(self):
        with patch(
            "maya_mcp_server.connection_guide.find_maya_installations",
            return_value=[],
        ):
            res = install_user_setup(port=7001)
        assert res["success"] is False
        assert res["error"]["code"] == "no_maya_found"


class TestUninstallMarkerBlock:
    """uninstall_user_setup strips only the managed region."""

    def test_not_installed(self, tmp_path):
        fake = _install(tmp_path)
        with patch(
            "maya_mcp_server.connection_guide.find_maya_installations",
            return_value=[fake],
        ):
            res = uninstall_user_setup()
        assert res["results"][0]["action"] == "not_installed"

    def test_no_block_is_noop(self, tmp_path):
        fake = _install(tmp_path)
        fake.user_setup_path.write_text("# user code\n", encoding="utf-8")
        with patch(
            "maya_mcp_server.connection_guide.find_maya_installations",
            return_value=[fake],
        ):
            res = uninstall_user_setup()
        entry = res["results"][0]
        assert entry["action"] == "no_block"
        assert fake.user_setup_path.read_text() == "# user code\n"

    def test_block_removed_keeps_rest(self, tmp_path):
        fake = _install(tmp_path)
        fake.user_setup_path.write_text(
            "# mine\n" + _marker_block(7001) + "# also mine\n",
            encoding="utf-8",
        )
        with patch(
            "maya_mcp_server.connection_guide.find_maya_installations",
            return_value=[fake],
        ):
            res = uninstall_user_setup()
        entry = res["results"][0]
        assert entry["action"] == "block_removed"
        content = fake.user_setup_path.read_text(encoding="utf-8")
        assert MARKER_BEGIN not in content
        assert "# mine" in content and "# also mine" in content
        assert Path(entry["backup"]).exists()

    def test_only_block_file_reports_empty_not_deleted(self, tmp_path):
        fake = _install(tmp_path)
        fake.user_setup_path.write_text(_marker_block(7001), encoding="utf-8")
        with patch(
            "maya_mcp_server.connection_guide.find_maya_installations",
            return_value=[fake],
        ):
            res = uninstall_user_setup()
        entry = res["results"][0]
        assert entry["action"] == "block_removed"
        assert entry["file_now_empty"] is True
        assert fake.user_setup_path.exists()  # not deleted without consent

    def test_only_block_file_removed_with_flag(self, tmp_path):
        fake = _install(tmp_path)
        fake.user_setup_path.write_text(_marker_block(7001), encoding="utf-8")
        with patch(
            "maya_mcp_server.connection_guide.find_maya_installations",
            return_value=[fake],
        ):
            res = uninstall_user_setup(remove_empty_file=True)
        entry = res["results"][0]
        assert entry["action"] == "file_removed"
        assert not fake.user_setup_path.exists()
        assert Path(entry["backup"]).exists()  # recovery path kept


class TestFallbackInstructions:
    """Honest copy: nothing claims a file was already generated."""

    def test_contains_key_sections(self):
        instructions = get_fallback_instructions(7001)
        assert "Script Editor" in instructions
        assert "Python" in instructions
        assert "commandPort" in instructions
        assert "7001" in instructions

    def test_contains_marker_block_verbatim(self):
        instructions = get_fallback_instructions(7001)
        assert _marker_block(7001) in instructions

    def test_no_false_generated_claim(self):
        instructions = get_fallback_instructions(7001)
        assert "\u5df2\u751f\u6210" not in instructions
        assert "has been placed" not in instructions

    def test_no_hardcoded_user_path(self):
        instructions = get_fallback_instructions(7001)
        assert "Administrator" not in instructions

    def test_custom_port(self):
        instructions = get_fallback_instructions(8888)
        assert "8888" in instructions


class TestConnectionDiagnostics:
    """Test connection diagnostics."""

    def test_returns_dict_structure(self):
        diag = get_connection_diagnostics(7001)
        assert isinstance(diag, dict)
        for k in (
            "platform",
            "port",
            "maya_running",
            "port_open",
            "issues",
            "suggestions",
            "user_setup_found",
        ):
            assert k in diag

    def test_port_value(self):
        diag = get_connection_diagnostics(9999)
        assert diag["port"] == 9999


class TestAgentInstructions:
    """Agent-facing connection instructions."""

    def test_contains_diagnostics(self):
        instructions = get_agent_connection_instructions(7001)
        assert "7001" in instructions
        assert "Maya" in instructions

    def test_mentions_marker_install(self):
        instructions = get_agent_connection_instructions(7001)
        assert "maya_setup_guide" in instructions


class TestFindMayaInstallations:
    """Single unified scanner behind find_maya_installations."""

    def test_linux_finds_home_maya(self, tmp_path):
        scripts_dir = tmp_path / "maya" / "2024" / "scripts"
        scripts_dir.mkdir(parents=True)
        with (
            patch("maya_mcp_server.utils.get_platform", return_value="linux"),
            patch(
                "maya_mcp_server.connection_guide.get_platform",
                return_value="linux",
            ),
            patch.object(Path, "home", return_value=tmp_path),
        ):
            results = find_maya_installations()
        assert any(r.version == "2024" for r in results)


def test_quoted_marker_text_is_not_a_region(tmp_path):
    """F-6: a comment mentioning the marker text inside another line must
    not be treated as a real marker line (substring-match forgery)."""
    fake = _install(tmp_path)
    fake.user_setup_path.write_text(
        f"# docs say the block starts with '{MARKER_BEGIN}'\nimport maya.cmds\n",
        encoding="utf-8",
    )
    with patch(
        "maya_mcp_server.connection_guide.find_maya_installations",
        return_value=[fake],
    ):
        res = install_user_setup(port=7001)
    entry = res["results"][0]
    assert entry["action"] == "needs_confirm"
    assert "proposed_block" in entry


def test_uninstall_keeps_lines_quoting_marker(tmp_path):
    """F-6: uninstall removes the real block but preserves comment lines
    that merely quote the marker text."""
    fake = _install(tmp_path)
    quoted = f"# remember: '{MARKER_BEGIN}' marks the managed block\n"
    fake.user_setup_path.write_text(quoted + _marker_block(7001), encoding="utf-8")
    with patch(
        "maya_mcp_server.connection_guide.find_maya_installations",
        return_value=[fake],
    ):
        res = uninstall_user_setup()
    entry = res["results"][0]
    assert entry["action"] == "block_removed"
    content = fake.user_setup_path.read_text(encoding="utf-8")
    assert quoted in content
    assert MARKER_END not in content
