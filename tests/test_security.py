"""Tests for security module."""

from __future__ import annotations

import ast
import logging

import pytest

from maya_mcp_server.security import (
    SAFE_DENIED_BUILTINS,
    SAFE_MODE_TOOLS,
    SAFE_RULE_BUILTIN,
    SAFE_RULE_BUILTINS,
    SAFE_RULE_DUNDER,
    SAFE_RULE_IMPORT,
    SAFE_RULE_NODE,
    SAFE_RULE_UNPARSEABLE,
    AuditLogger,
    InputValidationError,
    RateLimiter,
    SecurityConfig,
    compute_code_hash,
    sanitize_error_message,
    scan_for_dangerous_patterns,
    scan_safe_mode_code,
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


class TestScanSafeModeCode:
    """Seam A: the pure deny-by-default rule layer.

    Corpus sources, per the safe_mode spec: rule-table-derived accept/reject
    pairs, payloads that already live in the repo (the execute_code docstring
    examples, the pipeline-test cmds shapes), and researched escape shapes
    (mcp-for-blender #207 builtins illusion, dunder subclass chain,
    __import__). No invented samples.
    """

    def test_maya_import_is_allowed(self) -> None:
        assert scan_safe_mode_code("import maya.cmds as cmds; cmds.ls()") is None

    def test_from_maya_import_is_allowed(self) -> None:
        assert scan_safe_mode_code("from maya import cmds\ncmds.ls()") is None

    def test_allowlisted_helper_imports_are_allowed(self) -> None:
        code = "import json, math\nfrom typing import Any\nfrom functools import wraps"
        assert scan_safe_mode_code(code) is None

    def test_os_import_is_rejected(self) -> None:
        violation = scan_safe_mode_code("import os")
        assert violation is not None
        assert violation.rule_id == SAFE_RULE_IMPORT
        assert "os" in violation.message

    def test_from_os_import_is_rejected(self) -> None:
        violation = scan_safe_mode_code("from os import system")
        assert violation is not None
        assert violation.rule_id == SAFE_RULE_IMPORT

    def test_relative_import_is_rejected(self) -> None:
        violation = scan_safe_mode_code("from . import helpers")
        assert violation is not None
        assert violation.rule_id == SAFE_RULE_IMPORT

    def test_syntax_error_is_rejected_as_unparseable(self) -> None:
        violation = scan_safe_mode_code("def broken(")
        assert violation is not None
        assert violation.rule_id == SAFE_RULE_UNPARSEABLE

    def test_deep_traversal_is_rejected_as_unparseable(self) -> None:
        # Deep enough to exhaust NodeVisitor's recursive walk (Python's default
        # limit) but shallow enough to parse on supported versions, so this
        # exercises the traversal guard rather than the parse guard.
        code = "1" + " + 1" * 1500
        violation = scan_safe_mode_code(code)
        assert violation is not None
        assert violation.rule_id == SAFE_RULE_UNPARSEABLE

    def test_non_string_payload_is_rejected(self) -> None:
        violation = scan_safe_mode_code(None)
        assert violation is not None
        assert violation.rule_id == SAFE_RULE_UNPARSEABLE

    def test_safe_mode_tools_are_the_code_bearing_pair(self) -> None:
        assert SAFE_MODE_TOOLS == frozenset({"execute_code", "write_module"})

    # --- node allowlist (rule-table-derived pairs) ---

    @pytest.mark.parametrize(
        "code",
        [
            # the execute_code docstring payloads
            "cmds.ls(type='mesh')",
            "import maya.cmds as cmds; cmds.polyCube(name='GEO_cube')",
            # expression / assignment families from the pipeline-test corpus
            "x = 1\ny = 2\nx + y",
            "x = 1\nx += 1\nx",
            "x, y = 1, 2",
            "x: int = 1",
            "print('hello')",
            "[1, 2, 3]",
            "{'a': 1, 'b': 2}",
            "(x := 5)",
            "1 if True else 2",
            "lambda x: x + 1",
            "some_function(\n    arg1,\n    arg2,\n    arg3\n)",
            # control flow inside the allowlist
            "for i in range(10):\n    if i:\n        continue\n    else:\n        break",
            "while True:\n    break",
            "try:\n    cmds.polyCube()\nexcept Exception:\n    pass\nfinally:\n    pass",
            # comprehensions and f-strings
            "[x * 2 for x in range(10)]",
            "(x * 2 for x in range(10))",
            "{x: 1 for x in range(3)}",
            "{x for x in range(3)}",
            "f'cube_{name}'",
            # def / class bodies checked under the same rules
            "def foo():\n    return 1\nfoo()",
            "class Foo:\n    x = 1\nFoo.x",
            # dunder method NAMES are names, not attribute access
            "class Foo:\n    def __init__(self):\n        pass",
            # slicing / subscript / unpacking expression machinery
            "x[1:3]",
            "x[1, ...]",
            "a, *b = [1, 2, 3]",
            # allowlisted helper imports already covered; root 'maya' covers OpenMaya
            "import maya.OpenMaya as om",
            "from maya.OpenMaya import MPoint",
            "import collections, itertools, dataclasses",
        ],
    )
    def test_allowlisted_constructs_pass(self, code: str) -> None:
        assert scan_safe_mode_code(code) is None

    @pytest.mark.parametrize(
        "code",
        [
            "with open('f') as f:\n    pass",
            "with m:\n    pass",
            "raise ValueError('x')",
            "assert True",
            "del x",
            "def f():\n    global x\n    x = 1",
            "def f():\n    def g():\n        nonlocal x\n        x = 1",
            "def gen():\n    yield 42",
            "def gen():\n    yield from xs",
            "async def f():\n    return 1",
            "async def f():\n    await g()",
            "async def f():\n    async for x in y:\n        pass",
            "async def f():\n    async with m:\n        pass",
            "match x:\n    case 1:\n        pass",
            "async def f():\n    return await g()",
        ],
    )
    def test_non_allowlisted_nodes_reject_as_safe_mode_node(self, code: str) -> None:
        # deny-by-default: with/raise/assert/del/global/nonlocal/yield/async/
        # match are not in the v1 allowlist, so their presence denies.
        violation = scan_safe_mode_code(code)
        assert violation is not None, code
        assert violation.rule_id == SAFE_RULE_NODE

    def test_try_star_is_allowlisted_alongside_try(self) -> None:
        code = "try:\n    pass\nexcept* ValueError:\n    pass"
        try:
            ast.parse(code)
        except SyntaxError:
            pytest.skip("except* needs Python 3.11+")
        assert scan_safe_mode_code(code) is None

    # --- import allowlist ---

    def test_pymel_is_rejected_in_v1(self) -> None:
        violation = scan_safe_mode_code("import pymel.core as pm")
        assert violation is not None
        assert violation.rule_id == SAFE_RULE_IMPORT

    @pytest.mark.parametrize(
        "module",
        ["sys", "os", "subprocess", "socket", "ctypes", "shutil", "pathlib", "importlib"],
    )
    def test_escape_ladder_roots_reject(self, module: str) -> None:
        violation = scan_safe_mode_code(f"import {module}")
        assert violation is not None
        assert violation.rule_id == SAFE_RULE_IMPORT

    # --- denied builtin names (rule-table-derived) ---

    @pytest.mark.parametrize("name", sorted(SAFE_DENIED_BUILTINS))
    def test_denied_builtin_calls_reject(self, name: str) -> None:
        violation = scan_safe_mode_code(f"{name}('x')")
        assert violation is not None
        assert violation.rule_id == SAFE_RULE_BUILTIN
        assert name in violation.message

    @pytest.mark.parametrize("name", ["getattr", "eval", "super"])
    def test_denied_builtin_references_reject_not_just_calls(self, name: str) -> None:
        # Reference (alias) form is denied too, or `f = eval` would smuggle
        # the same escape past a call-shape check.
        violation = scan_safe_mode_code(f"f = {name}")
        assert violation is not None
        assert violation.rule_id == SAFE_RULE_BUILTIN

    def test_denied_builtin_shadowed_by_store_still_rejects(self) -> None:
        violation = scan_safe_mode_code("eval = lambda x: x")
        assert violation is not None
        assert violation.rule_id == SAFE_RULE_BUILTIN

    @pytest.mark.parametrize(
        "code",
        [
            "dir(x)",
            "hasattr(obj, 'name')",
            "len(cmds.ls())",
            "isinstance(x, int)",
            "print('hello')",
            "range(10)",
            "sorted(xs)",
            "type(x)",
        ],
    )
    def test_ordinary_builtins_pass(self, code: str) -> None:
        assert scan_safe_mode_code(code) is None

    # --- dunder attribute access ---

    def test_ordinary_attribute_access_passes(self) -> None:
        assert scan_safe_mode_code("cmds.polyCube(name='GEO_cube')") is None
        # `__x` without a trailing `__` is not a dunder under the __x__ shape.
        assert scan_safe_mode_code("obj.__mangled") is None

    @pytest.mark.parametrize(
        "code",
        [
            "x.__class__",
            "().__class__.__base__.__subclasses__()",
            "foo.__globals__['x']",
            "x.__dict__",
        ],
    )
    def test_dunder_attribute_access_rejects(self, code: str) -> None:
        violation = scan_safe_mode_code(code)
        assert violation is not None
        assert violation.rule_id == SAFE_RULE_DUNDER

    def test_from_import_of_dunder_name_rejects(self) -> None:
        violation = scan_safe_mode_code("from maya.cmds import __path__")
        assert violation is not None
        assert violation.rule_id == SAFE_RULE_DUNDER

    # --- __builtins__ ---

    @pytest.mark.parametrize(
        "code",
        [
            "__builtins__",
            "__builtins__['eval']('1+1')",
            "__builtins__.eval('1+1')",
            "x = __builtins__",
        ],
    )
    def test_builtins_reference_rejects(self, code: str) -> None:
        violation = scan_safe_mode_code(code)
        assert violation is not None
        assert violation.rule_id == SAFE_RULE_BUILTINS

    # --- researched escape shapes (mcp-for-blender #207 + families) ---

    def test_import_os_via_dunder_import_rejects(self) -> None:
        violation = scan_safe_mode_code("__import__('os')")
        assert violation is not None
        assert violation.rule_id == SAFE_RULE_BUILTIN

    def test_dunder_subclass_chain_rejects(self) -> None:
        code = "().__class__.__base__.__subclasses__()[1]('id')"
        violation = scan_safe_mode_code(code)
        assert violation is not None
        assert violation.rule_id == SAFE_RULE_DUNDER

    # --- recursion inside nested scopes (same rules, no exemption) ---

    @pytest.mark.parametrize(
        "code",
        [
            "def f():\n    import os",
            "def f():\n    eval('x')",
            "class C:\n    import os",
            "class C:\n    x = __builtins__",
            "f = lambda: getattr(x, 'y')",
            "def f():\n    x.__class__",
            "def outer():\n    def inner():\n        import subprocess\n    return inner",
        ],
    )
    def test_nested_scope_escapes_reject(self, code: str) -> None:
        assert scan_safe_mode_code(code) is not None

    @pytest.mark.parametrize(
        "code",
        [
            "def f():\n    import maya.cmds as cmds\n    return cmds.ls()",
            "class C:\n    def m(self):\n        return 1",
            "f = lambda x: x * 2",
        ],
    )
    def test_nested_scope_allowlisted_passes(self, code: str) -> None:
        assert scan_safe_mode_code(code) is None


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


# ---------------------------------------------------------------------------
# D-019 error contract, pinned generically. D-207 4 requires every documented
# code to carry a pytest node ID, and the base class plus server_not_started
# have no per-code raise test of their own - so pin the contract once for the
# whole set instead of writing a test per code that only restates the class.
# ---------------------------------------------------------------------------


def _pipeline_error_subclasses():
    import maya_mcp_server.security as sec

    return [
        obj
        for obj in vars(sec).values()
        if isinstance(obj, type)
        and issubclass(obj, sec.PipelineError)
        and obj is not sec.PipelineError
    ]


class TestErrorCodeContract:
    def test_every_error_class_renders_its_own_code_prefix(self):
        """The agent classifies a host failure from the isError text alone, so
        the [code] prefix is the contract - not the message text."""
        for cls in _pipeline_error_subclasses():
            err = cls("boom")
            assert str(err).startswith(f"[{cls.code}] "), cls.__name__

    def test_base_pipeline_error_carries_pipeline_error(self):
        from maya_mcp_server.security import PipelineError

        err = PipelineError("boom", suggestion="retry")
        assert str(err) == "[pipeline_error] boom (suggestion: retry)"

    def test_every_error_class_declares_a_snake_case_code(self):
        import re

        for cls in _pipeline_error_subclasses():
            assert re.fullmatch(r"[a-z][a-z0-9_]*", cls.code), cls.__name__

    def test_server_not_ready_before_lifespan_init(self):
        """The one place ServerNotReadyError is raised: a tool asking for the
        global session manager before startup finished."""
        from maya_mcp_server import server
        from maya_mcp_server.security import ServerNotReadyError

        assert server._session_manager is None, "test assumes a fresh process"
        with pytest.raises(ServerNotReadyError) as ei:
            server.get_session_manager()
        assert ei.value.code == "server_not_started"
