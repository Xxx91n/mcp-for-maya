"""Tests for security module."""

from __future__ import annotations

import logging

import pytest

from maya_mcp_server.security import (
    AuditLogger,
    InputValidationError,
    RateLimiter,
    SecurityConfig,
    compute_code_hash,
    sanitize_error_message,
    scan_for_dangerous_patterns,
    scan_tool_params,
    validate_code_size,
    validate_module_name,
    validate_session_key,
)


class TestValidateCodeSize:
    """Test code size validation."""

    def test_valid_code(self) -> None:
        """Test that normal code passes validation."""
        validate_code_size("print('hello')")

    def test_empty_code(self) -> None:
        """Test that empty code passes validation."""
        validate_code_size("")

    def test_large_code_raises(self) -> None:
        """Test that code exceeding max size raises error."""
        large_code = "x = 1\n" * 200_000
        with pytest.raises(InputValidationError, match="exceeds maximum"):
            validate_code_size(large_code, max_size=1000)

    def test_custom_max_size(self) -> None:
        """Test custom max size parameter."""
        with pytest.raises(InputValidationError):
            validate_code_size("x" * 101, max_size=100)


class TestValidateModuleName:
    """Test module name validation."""

    def test_valid_simple_name(self) -> None:
        """Test simple valid module name."""
        validate_module_name("mytools")

    def test_valid_dotted_name(self) -> None:
        """Test dotted module name."""
        validate_module_name("mypackage.mymodule")

    def test_valid_deep_dotted_name(self) -> None:
        """Test deeply dotted module name."""
        validate_module_name("a.b.c.d")

    def test_empty_name_raises(self) -> None:
        """Test that empty name raises error."""
        with pytest.raises(InputValidationError, match="cannot be empty"):
            validate_module_name("")

    def test_invalid_name_raises(self) -> None:
        """Test that invalid name raises error."""
        with pytest.raises(InputValidationError, match="Invalid module name"):
            validate_module_name("my-module")

    def test_name_starting_with_digit_raises(self) -> None:
        """Test that name starting with digit raises error."""
        with pytest.raises(InputValidationError, match="Invalid module name"):
            validate_module_name("1module")

    def test_long_name_raises(self) -> None:
        """Test that excessively long name raises error."""
        with pytest.raises(InputValidationError, match="exceeds maximum"):
            validate_module_name("a" * 300)


class TestValidateSessionKey:
    """Test session key validation."""

    def test_none_key(self) -> None:
        """Test that None is valid (auto-select)."""
        assert validate_session_key(None) is None

    def test_valid_key(self) -> None:
        """Test valid session key."""
        assert validate_session_key("127.0.0.1:50000") == "127.0.0.1:50000"

    def test_localhost_key(self) -> None:
        """Test localhost key."""
        assert validate_session_key("localhost:7001") == "localhost:7001"

    def test_invalid_format_raises(self) -> None:
        """Test invalid format raises error."""
        with pytest.raises(InputValidationError, match="Invalid session key"):
            validate_session_key("no-port")

    def test_invalid_port_raises(self) -> None:
        """Test invalid port raises error."""
        with pytest.raises(InputValidationError, match="Invalid port"):
            validate_session_key("host:99999")

    def test_non_string_raises(self) -> None:
        """Test non-string raises error."""
        with pytest.raises(InputValidationError, match="must be a string"):
            validate_session_key(12345)


class TestScanForDangerousPatterns:
    """Test dangerous pattern scanning."""

    def test_safe_code(self) -> None:
        """Test that safe code produces no warnings."""
        warnings = scan_for_dangerous_patterns("import maya.cmds as cmds; cmds.ls()")
        assert len(warnings) == 0

    def test_subprocess_import(self) -> None:
        """Test detection of subprocess import."""
        warnings = scan_for_dangerous_patterns('__import__("subprocess")')
        assert any("subprocess" in w for w in warnings)

    def test_os_system(self) -> None:
        """Test detection of os.system."""
        warnings = scan_for_dangerous_patterns("os.system('ls')")
        assert any("os command" in w for w in warnings)

    def test_eval_usage(self) -> None:
        """Test detection of eval."""
        warnings = scan_for_dangerous_patterns("eval('1+1')")
        assert any("eval" in w for w in warnings)


class TestComputeCodeHash:
    """Test code hashing."""

    def test_deterministic(self) -> None:
        """Test that hash is deterministic."""
        assert compute_code_hash("test") == compute_code_hash("test")

    def test_different_code_different_hash(self) -> None:
        """Test that different code produces different hash."""
        assert compute_code_hash("a") != compute_code_hash("b")

    def test_hash_length(self) -> None:
        """Test hash length."""
        assert len(compute_code_hash("test")) == 32


class TestSanitizeErrorMessage:
    """Test error message sanitization."""

    def test_windows_path(self) -> None:
        """Test Windows path sanitization."""
        msg = "Error at C:\\Users\\admin\\project\\file.py"
        sanitized = sanitize_error_message(msg)
        assert "C:\\Users\\admin" not in sanitized

    def test_unix_path(self) -> None:
        """Test Unix path sanitization."""
        msg = "Error at /home/user/project/file.py"
        sanitized = sanitize_error_message(msg)
        assert "/home/user/" not in sanitized

    def test_no_path(self) -> None:
        """Test message without path."""
        msg = "Some error message"
        assert sanitize_error_message(msg) == msg


class TestRateLimiter:
    """Test rate limiter."""

    def test_allows_within_limit(self) -> None:
        """Test that calls within limit are allowed."""
        limiter = RateLimiter(max_calls=5, window=60.0)
        for _ in range(5):
            assert limiter.try_consume("session1") is True

    def test_blocks_over_limit(self) -> None:
        """Test that calls over limit are blocked."""
        limiter = RateLimiter(max_calls=3, window=60.0)
        for _ in range(3):
            assert limiter.try_consume("session1") is True
        assert limiter.try_consume("session1") is False

    def test_separate_sessions(self) -> None:
        """Test that different sessions have separate limits."""
        limiter = RateLimiter(max_calls=2, window=60.0)
        assert limiter.try_consume("session1") is True
        assert limiter.try_consume("session1") is True
        assert limiter.try_consume("session1") is False
        # Different session should still be allowed
        assert limiter.try_consume("session2") is True

    def test_get_remaining(self) -> None:
        """Test remaining count."""
        limiter = RateLimiter(max_calls=5, window=60.0)
        assert limiter.get_remaining("session1") == 5
        limiter.try_consume("session1")
        assert limiter.get_remaining("session1") == 4


# ------------------------------------------------------------
# T-04: D-018 pipeline primitives
# ------------------------------------------------------------


class TestPipelineErrorContract:
    """D-019: host-side failures carry [code] prefixes."""

    def test_input_validation_error_code(self) -> None:
        err = InputValidationError("bad thing")
        assert str(err).startswith("[invalid_input]")
        assert err.message == "bad thing"

    def test_rate_limit_error_code(self) -> None:
        from maya_mcp_server.security import RateLimitExceededError

        err = RateLimitExceededError("slow down")
        assert str(err).startswith("[rate_limited]")

    def test_pattern_blocked_error_code(self) -> None:
        from maya_mcp_server.security import PatternBlockedError

        err = PatternBlockedError("nope", suggestion="rephrase")
        assert str(err).startswith("[blocked_pattern]")
        assert "rephrase" in str(err)

    def test_suggestion_rendered(self) -> None:
        err = InputValidationError("bad", suggestion="try X")
        assert "try X" in str(err)

    def test_gui_session_required_error_code(self) -> None:
        from maya_mcp_server.security import GuiSessionRequiredError

        err = GuiSessionRequiredError("headless", suggestion="use a GUI session")
        assert str(err).startswith("[gui_session_required]")
        assert "use a GUI session" in str(err)

    def test_capture_empty_error_code(self) -> None:
        from maya_mcp_server.security import CaptureEmptyError

        err = CaptureEmptyError("no bytes", suggestion="retry with GUI")
        assert str(err).startswith("[capture_empty]")
        assert "retry with GUI" in str(err)

    def test_capture_invalid_error_code(self) -> None:
        from maya_mcp_server.security import InvalidCaptureError

        err = InvalidCaptureError("not an image", suggestion="check decoder")
        assert str(err).startswith("[capture_invalid]")
        assert "check decoder" in str(err)


class TestTokenBucket:
    """Real token bucket semantics (D-018)."""

    def test_starts_full(self) -> None:
        from maya_mcp_server.security import TokenBucket

        b = TokenBucket(capacity=3, refill_per_sec=1)
        assert b.take() and b.take() and b.take()
        assert not b.take()

    def test_refills_over_time(self) -> None:
        import time

        from maya_mcp_server.security import TokenBucket

        b = TokenBucket(capacity=2, refill_per_sec=50)
        b.take()
        b.take()
        assert not b.take()
        time.sleep(0.05)  # tokens accrue, capped at capacity
        assert b.take()
        assert b.take()
        assert not b.take()

    def test_retry_after_positive_when_empty(self) -> None:
        from maya_mcp_server.security import TokenBucket

        b = TokenBucket(capacity=1, refill_per_sec=10)
        b.take()
        wait = b.retry_after()
        assert 0 < wait <= 0.2


class TestRateLimiterBuckets:
    """RateLimiter now wraps per-session token buckets."""

    def test_burst_then_wait(self) -> None:
        limiter = RateLimiter(max_calls=2, window=60.0)
        assert limiter.try_consume("s") is True
        assert limiter.try_consume("s") is True
        assert limiter.try_consume("s") is False

    def test_retry_after_reported(self) -> None:
        limiter = RateLimiter(max_calls=1, window=60.0)
        limiter.try_consume("s")
        assert limiter.retry_after("s") > 0


class TestScanToolParams:
    """rule_id x tool x param pattern scanning (D-018)."""

    def test_block_rule_on_code(self) -> None:
        from maya_mcp_server.security import scan_tool_params

        w, b = scan_tool_params("execute_code", {"code": "os.system('x')"})
        assert any(h["rule_id"] == "code-os-system" for h in b)
        assert any(h["rule_id"] == "warn-os-exec" for h in w)

    def test_traversal_blocked_only_on_filename(self) -> None:
        from maya_mcp_server.security import scan_tool_params

        _w, b1 = scan_tool_params("scene_rollback", {"filename": "../x.ma"})
        assert b1 and b1[0]["rule_id"] == "file-traversal"
        _w, b2 = scan_tool_params("scene_inspect", {"target": "../x"})
        assert b2 == []

    def test_exclusion_table(self) -> None:
        from maya_mcp_server.security import scan_tool_params

        excl = {("code-eval", "execute_code", "code")}
        _w, b = scan_tool_params("execute_code", {"code": "eval('1')"}, exclusions=excl)
        assert b == []
        _w, b2 = scan_tool_params("write_module", {"code": "eval('1')"}, exclusions=excl)
        assert b2

    def test_non_string_params_ignored(self) -> None:
        from maya_mcp_server.security import scan_tool_params

        w, b = scan_tool_params("t", {"port": 1234, "flag": True})
        assert w == [] and b == []


class TestSummarizeParams:
    def test_short_values_verbatim(self) -> None:
        from maya_mcp_server.security import summarize_params

        s = summarize_params({"a": 1, "b": "x"})
        assert "a=1" in s and 'b="x"' in s

    def test_long_string_hashed_with_preview(self) -> None:
        from maya_mcp_server.security import summarize_params

        s = summarize_params({"code": "z" * 500})
        assert "sha:" in s and "(500B" in s

    def test_credentials_redacted(self) -> None:
        from maya_mcp_server.security import summarize_params

        s = summarize_params({"api_key": "sekret", "note": "hi"})
        assert "sekret" not in s and "<redacted>" in s

    def test_capped_at_200(self) -> None:
        from maya_mcp_server.security import summarize_params

        s = summarize_params({f"p{i}": "v" * 100 for i in range(20)})
        assert len(s) <= 200


class TestAuditLogger:
    def _events(self, path):
        import json

        return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]

    def test_writes_jsonl(self, tmp_path) -> None:
        from maya_mcp_server.security import AuditLogger, build_audit_event

        log = tmp_path / "sub" / "audit.jsonl"
        audit = AuditLogger(log)
        audit.record(
            build_audit_event(
                session_id="s1",
                tool_name="t",
                params={"a": 1},
                outcome="success",
                duration_ms=1.5,
            )
        )
        ev = self._events(log)[0]
        for key in (
            "event_id",
            "timestamp",
            "session_id",
            "tool_name",
            "input_summary",
            "outcome",
            "duration_ms",
            "warnings",
        ):
            assert key in ev, key

    def test_rejected_outcome_recorded(self, tmp_path) -> None:
        from maya_mcp_server.security import AuditLogger, build_audit_event

        log = tmp_path / "audit.jsonl"
        audit = AuditLogger(log)
        audit.record(
            build_audit_event(
                session_id="s",
                tool_name="t",
                params={},
                outcome="rejected",
                duration_ms=0.1,
                warnings=[{"rule_id": "r", "param": "p", "snippet": "x", "message": "m"}],
            )
        )
        ev = self._events(log)[0]
        assert ev["outcome"] == "rejected"
        assert ev["warnings"][0]["rule_id"] == "r"

    def test_rotation(self, tmp_path) -> None:
        from maya_mcp_server.security import AuditLogger, build_audit_event

        log = tmp_path / "audit.jsonl"
        audit = AuditLogger(log, max_bytes=200, backup_count=3)
        for _ in range(20):
            audit.record(
                build_audit_event(
                    session_id="s",
                    tool_name="t",
                    params={},
                    outcome="success",
                    duration_ms=0.1,
                )
            )
        rotated = tmp_path / "audit.jsonl.1"
        assert rotated.exists()
        assert log.exists()

    def test_write_failure_non_blocking(self, tmp_path) -> None:
        from maya_mcp_server.security import AuditLogger

        audit = AuditLogger(tmp_path / "audit.jsonl")
        blocker = tmp_path / "blocker"
        blocker.write_text("x")  # a FILE where a dir is needed -> mkdir fails
        audit.path = blocker / "audit.jsonl"
        audit.record({"a": 1})  # must not raise
        assert audit._warned is True  # failure streak started, not latched

    def test_posix_0600(self, tmp_path) -> None:
        import os
        import stat

        from maya_mcp_server.security import AuditLogger

        log = tmp_path / "audit.jsonl"
        AuditLogger(log).record({"a": 1})
        if os.name != "nt":
            mode = stat.S_IMODE(log.stat().st_mode)
            assert mode == 0o600, oct(mode)
        else:
            assert log.exists()  # best-effort on Windows


class TestSanitizeErrorMessagePaths:
    """rui.txt P2: Windows regex previously only matched trailing-slash paths."""

    def test_windows_path_with_filename(self) -> None:
        msg = r"error at C:\Users\alice\secret.ma line 3"
        out = sanitize_error_message(msg)
        assert "alice" not in out
        assert "secret.ma" not in out

    def test_windows_path_no_trailing_backslash(self) -> None:
        msg = "failed: C:\\tmp\\one.ma"
        out = sanitize_error_message(msg)
        assert "C:\\tmp" not in out


class TestFileTraversalPrecision:
    """F-4: file-traversal blocks only '../'-style sequences — the rule
    must stay inside the zero-false-positive boundary (D-018)."""

    def test_double_dot_filename_not_blocked(self) -> None:
        _w, blocked = scan_tool_params("x", {"filename": "v1..2.ma"})
        assert blocked == []

    def test_bare_double_dot_not_blocked(self) -> None:
        _w, blocked = scan_tool_params("x", {"filename": ".."})
        assert blocked == []

    def test_parent_dir_prefix_blocked(self) -> None:
        _w, blocked = scan_tool_params("x", {"filename": "../evil.ma"})
        assert blocked and blocked[0]["rule_id"] == "file-traversal"

    def test_embedded_traversal_blocked(self) -> None:
        _w, blocked = scan_tool_params("x", {"filename": "scenes/../evil.ma"})
        assert blocked and blocked[0]["rule_id"] == "file-traversal"

    def test_windows_separator_traversal_blocked(self) -> None:
        _w, blocked = scan_tool_params("x", {"filename": "a\\..\\b.ma"})
        assert blocked and blocked[0]["rule_id"] == "file-traversal"


class TestAuditDualWrite:
    """F-5: a failed JSONL write must not kill the logger sink, and the
    file sink recovers on the next writable attempt (no permanent latch)."""

    def test_failed_write_still_logs_and_recovers(self, tmp_path, caplog) -> None:
        log_path = tmp_path / "audit" / "audit.jsonl"
        audit = AuditLogger(log_path)
        audit.record({"event_id": "e1", "outcome": "success"})
        assert log_path.exists()

        audit.path = tmp_path  # a directory: os.open(O_WRONLY) fails
        caplog.clear()
        with caplog.at_level(logging.INFO, logger="maya_mcp_server.security"):
            audit.record({"event_id": "e2", "outcome": "success"})
            audit.record({"event_id": "e3", "outcome": "success"})
        dual = [
            r
            for r in caplog.records
            if r.levelno == logging.INFO and r.message.startswith("audit ")
        ]
        assert len(dual) == 2  # logger dual-write survived the file failure
        warn = [r for r in caplog.records if "write failed" in r.message]
        assert len(warn) == 1  # throttled: once per failure streak

        audit.path = log_path  # writable again -> latch must be gone
        audit.record({"event_id": "e4", "outcome": "success"})
        lines = [line for line in log_path.read_text().splitlines() if line.strip()]
        assert len(lines) == 2
        assert any('"e4"' in line for line in lines)
