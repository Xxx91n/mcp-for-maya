# --- _mcp_scene scene state file (issue #206): own file, one injected module ---
#
# scene_tools._ensure_module_injected appends this file after
# zone_geometry_module.py and injects the whole assembly as _mcp_scene.
# It is not a separate injected module.
#
# Why a separate file: maya_scene_module.py is capped by
# .github/monolith-budget.json, so a new read lands here instead of pushing
# that cap up.
#
# Runtime floor: Maya >=2023 (Python 3.9). No __future__ import here: it would
# land mid-file in the assembled payload.

from typing import Any

import maya.cmds as cmds


def get_scene_modified() -> dict[str, Any]:
    """Report whether the open scene has changes that were never saved.

    Returns {"scene_modified": bool} and nothing else. True means Maya's own
    unsaved-changes flag is on; false means it is off. The flag does not
    record who made the change: a script and a person both turn it on, and no
    Maya API can tell them apart. This function only reads the flag and never
    changes it. If Maya cannot answer, the call fails like any other failed
    Maya query; it never reports a made-up "clean" in that case.
    """
    return {"scene_modified": bool(cmds.file(query=True, modified=True))}
