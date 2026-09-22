"""Version unification regression (D-060③ / T-13 drift pin).

serverInfo.version must report the product version - the MCP spec puts
the protocol version on a separate protocolVersion field, so leaking the
FastMCP framework version was a defect, not a dual track.
"""

from __future__ import annotations

import importlib.metadata

import pytest

import maya_mcp_server
from maya_mcp_server import server


def test_version_literal_matches_dist_metadata() -> None:
    try:
        dist_version = importlib.metadata.version("mcp-for-maya")
    except importlib.metadata.PackageNotFoundError:
        pytest.skip("mcp-for-maya dist not installed (source-tree run)")
    assert maya_mcp_server.__version__ == dist_version


def test_server_info_uses_product_version() -> None:
    expected = maya_mcp_server.__version__
    try:
        expected = importlib.metadata.version("mcp-for-maya")
    except importlib.metadata.PackageNotFoundError:
        pass
    assert server._product_version() == expected
    assert server.mcp.version == expected
