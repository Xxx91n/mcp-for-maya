"""Bootstrap code management for Maya sessions.

Maya's command port has specific behavior:
- Each command runs in a fresh local namespace
- Statements with `;` return the result of the FIRST statement, not the last
- Modules stored in sys.modules persist between commands
- Use `__import__('module')` to access persistent modules in single expressions

This module provides functions to load bootstrap code and templates for
accessing the persistent `_mcp` module in Maya sessions.
"""

from __future__ import annotations

import importlib.resources
from pathlib import Path


def _get_code(module_name: str) -> str:
    """
    Get the bootstrap code that creates the _mcp module in Maya.

    The code is loaded from maya_bootstrap.py and must be executed via
    exec(code, globals()) to persist definitions in Maya's global namespace.

    Returns:
        Python source code as a string
    """
    # Try modern importlib.resources API first (Python 3.9+)
    try:
        if hasattr(importlib.resources, "files"):
            # Python 3.9+
            bootstrap_file = importlib.resources.files("maya_mcp_server") / f"{module_name}.py"
            return bootstrap_file.read_text(encoding="utf-8")
    except (AttributeError, TypeError):
        pass

    # Fallback: use __file__ to locate maya_bootstrap.py
    bootstrap_path = Path(__file__).parent / f"{module_name}.py"
    return bootstrap_path.read_text(encoding="utf-8")


def get_bootstrap_code() -> str:
    """
    Get the bootstrap code that creates the _mcp module in Maya.

    The code is loaded from maya_bootstrap.py and must be executed via
    exec(code, globals()) to persist definitions in Maya's global namespace.

    Returns:
        Python source code as a string
    """
    # Known limitation: create_module lives in maya_bootstrap.py, and this
    # function ships that file whole. The injection unit is a file read verbatim
    # and hashed as part of the payload; extracting just its lines with inspect
    # would hand back the same text through a runtime import of this package, so
    # the file stays the unit.
    return _get_code("maya_bootstrap")


def get_helper_module_code() -> str:
    """
    Get the helper code that becomes the maya_mcp module in Maya.

    Returns:
        Python source code as a string
    """
    return _get_code("maya_mcp_helper") + _get_code("maya_bootstrap")
