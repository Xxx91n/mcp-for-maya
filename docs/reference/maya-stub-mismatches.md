# Where `types-maya-strict` disagrees with a shipped Maya call

**What this file is:** the per-spot record behind the type-checking batch in
#229. For each place where the third-party Maya type definitions disagree with
a call the code already ships, it states the stub's claim, what the call
really sends, the evidence for the call form, the handling, and what a live
Maya interpreter still has to confirm. It is the list to read the next time
`types-maya-strict` is upgraded.

**What it is not:** proof of live Maya behaviour *from the batch alone*. No
Maya session was run for that batch: running the tests under mayapy was not
possible on the box that measured it (`docs/testing.md`, the real-Maya
section, records the native access violation when `maya.standalone` is
imported and the `maya.exe -batch` hang), so every live cell below was open
at the time. The fake Maya test layer
(`tests/maya_stub/`) accepts these same calls, but that proves the calls match
the fake, not the real command; the real-interpreter test
(`tests/test_mayapy_smoke.py::test_callform_stub_disagreement_forms`) is what
turns a cell into a result, and it skips honestly on this box. None of the six
stub forms needs GUI eyes — all six are assertable in a real interpreter,
which is why their live column says `mayapy`.

**Live status (2026-11-15, issue #253):** the six forms were run on Maya 2024
through a GUI session, because that box's mayapy fails at
`import maya.standalone` (`ImportError: DLL load failed while importing
standalone`). All six pass, and so does the `#229` test function when handed
real `maya.cmds`. See "Live results" at the bottom; the table above keeps the
batch-time wording as history.

**Measured environment:** `types-maya-strict==2025.0.6`, `mypy==2.3.1`,
`mypy-baseline==0.7.4`, Python from `uv sync --frozen`, base commit `1ece725`
(#227 merged), Windows 11 x64, 2026-11-14.

## The six stub disagreements (17 errors) and the one mixed finding

| Spot | Stub claims | Call sends | If the stub were right | Evidence for the call form | Handling | Live check |
|---|---|---|---|---|---|---|
| `xform` query reads — `analyze_aesthetics`, `scene_review` | flags are `query`/`worldSpace`/`translation`/`rotation` only | `q=`, `ws=`, `t=`, `ro=` | every read would raise a flag error and the lighting scores would lose world positions | Command reference (Maya 2024): `worldSpace(ws)`, `translation(t)`, `rotation(ro)` are the flag's own short names, and the command is queryable | Call unchanged; `cast(Any, cmds.xform)` at the three call sites | `mayapy` — still open; a GUI session passed it 2026-11-15 (below) |
| `rename` — `create_camera_shot`, `create_orbit_camera` | returns `None` | uses the return value (`... or name`) | the camera keeps the auto-generated name instead of the requested one | Command reference returns "the new name" as a string | Call unchanged; `cast(str, ...)` states the return type | `mayapy` — still open; a GUI session passed it 2026-11-15 (below) |
| `keyTangent` — `create_orbit_camera` | flags are `inTangentType`/`outTangentType` only | `itt=`, `ott=` | the tangent edit would raise a flag error and the orbit keys stay flat | Command reference lists `inTangentType(itt)` and `outTangentType(ott)`; both are also on its global-flag list | Call unchanged; `# type: ignore[call-overload]` on that line | `mayapy` — still open; a GUI session passed it 2026-11-15 (below) |
| `playbackOptions` — `create_orbit_camera` | flags are `minTime`/`maxTime` only | `min=`, `max=` | the playback range would raise a flag error and stay at the scene default | Command reference lists `min` -> `minTime` and `max` -> `maxTime` | Call unchanged; `# type: ignore[call-overload]` on that line | `mayapy` — still open; a GUI session passed it 2026-11-15 (below) |
| `aimConstraint` — `create_camera_shot`, `create_orbit_camera` | `aimVector`/`upVector` are `tuple[float, float, float]` | three-number lists `[0, 0, -1]`, `[0, 1, 0]` | the constraint call would reject the arguments and the camera would fall back to manual rotation | Command reference types both flags as three doubles; a Python list of three numbers is the same flag value | Call unchanged; `# type: ignore[call-overload]` on each call line | `mayapy` — still open; a GUI session passed it 2026-11-15 (below) |
| `MFnMesh.getPoint` — `get_scene_graph` full detail | parameter is `MSpace`, but `MSpace.kWorld` is declared `ClassVar[int]` in the same stub file | `om2.MSpace.kWorld` | the vertex dump would lose its world-space points (the call is inside a `try`) | The stub contradicts itself: the value it declares `int` is the value its own parameter type expects | Call unchanged; `cast(om2.MSpace, ...)` records the value Maya really passes | `mayapy` — still open; a GUI session passed it 2026-11-15 (below) |
| `cmds.camera` — `create_camera_shot` (the mixed one) | overloads are narrow but usable | `focalLength=shot["focal_length"]` was inferred `object` | nothing — the `object` came from the local `SHOT_TYPES` literal, and the stub was not the cause | The five focal lengths in `SHOT_TYPES` are ints; the cast states the argument type at the one place it is used | `cast(float, shot["focal_length"])`; `SHOT_TYPES` stays an unannotated literal | none |

Sources for the evidence column, all Maya 2024 Python command reference pages:

- <https://help.autodesk.com/cloudhelp/2024/ENU/Maya-Tech-Docs/CommandsPython/xform.html>
- <https://help.autodesk.com/cloudhelp/2024/ENU/Maya-Tech-Docs/CommandsPython/rename.html>
- <https://help.autodesk.com/cloudhelp/2024/ENU/Maya-Tech-Docs/CommandsPython/keyTangent.html>
- <https://help.autodesk.com/cloudhelp/2024/ENU/Maya-Tech-Docs/CommandsPython/playbackOptions.html>
- stub side: `.venv/Lib/site-packages/maya-stubs/cmds/__init__.pyi` (`xform`, `rename`,
  `keyTangent`, `playbackOptions`, `aimConstraint`) and
  `maya-stubs/api/OpenMaya.pyi` (`MFnMesh.getPoint`, `MSpace`), package
  `types-maya-strict==2025.0.6`.

Why the three `xform` sites use a cast instead of an ignore: an inline
`# type: ignore[call-arg]` needs about 27 more columns than those lines have
under the repository's 100-column limit, and reformatting them would push the
line-capped module over its budget. The cast is the narrowest form that fits:
it silences one call's flag checking, keeps the same values, and adds no
module-level name. The other four stub gaps sit on short lines, so they carry
the ignore with its error code.

## Before and after

```
uv run python -m mypy src/ > mypy-report.txt 2>&1   # exit 1, both runs
```

| | Before | After |
|---|---|---|
| Errors / files | 85 / 1 | 67 / 1 |
| Notes | 15 | 0 |
| `arg-type` | 1 | 0 |
| `call-arg` | 9 | 0 |
| `call-overload` | 6 | 0 |
| `func-returns-value` | 2 | 0 |
| `assignment` | 1 | 1 |
| `attr-defined` | 1 | 1 |
| `no-untyped-call` | 23 | 23 |
| `no-untyped-def` | 31 | 31 |
| `operator` | 7 | 7 |
| `str-format` | 3 | 3 |
| `var-annotated` | 1 | 1 |

The two reports were compared as multisets of `(file, message, code)`, not by
total: 18 entries removed, 0 message counts added, so no new finding hid
behind an old message. The baseline diff also shows one identical
`no-untyped-def` line changing position — the sync tool rewrites the file in
error order, and an identical neighbouring line shifted into its place; the
source diff adds and removes no function definition, so that is a move, not a
finding. `uv run mypy-baseline sync < mypy-report.txt` regenerated
`mypy-baseline.txt` (100 lines -> 67); `mypy-baseline filter` then reported
`new 0`, `fixed 0`, exit 0.

The raw reports themselves are not stored here: `docs/evidence/README.md`
keeps raw output out of the repo and admits only frozen evidence with
provenance. The command above reproduces both on the base commit and on this
one, and the `mypy-baseline.txt` diff is the in-repo record of what left.

## What the remaining 67 baseline entries were

The split below is the snapshot from the stub-disagreement batch (#229, commit
`e019954`), not the current count: #252 then took it to 45, #251 to 20, and
#255 to 10 — that last one is the section after this.

- 54 missing annotations: `no-untyped-def` 31, `no-untyped-call` 23.
- 13 container/inference findings with local causes, not stub causes:
  `operator` 7, `str-format` 3, `attr-defined` 1, `var-annotated` 1,
  `assignment` 1. Most come from `_MAYA_STANDARDS`, an untyped dict whose
  values are inferred `object`; #213 named that root and singled out
  `scene_review`'s `sub_scores["decay"]` (a float stored into a dict first
  inferred `int`) as its own thing to look at.
- Keeping the baseline is still reasonable: the remaining errors are local
  typing gaps with no evidence of runtime faults, and the stub disputes are
  now either cast or ignored at single points, each with the reason above.

## After #255 (2026-11-15): the container group is gone

`_MAYA_STANDARDS` now has a declared shape (`scene_module_types.MayaStandards`,
a `TypedDict`), so the dict literal no longer infers `dict[str, object]`. That
one annotation removed all 10 container findings still in the baseline:
`operator` 6, `str-format` 3, `attr-defined` 1. `var-annotated` and
`assignment` had already left with the scoring-chain work (#251, #252), so the
ticket's historical 7/3/1/1/1 split was down to 6/3/0/0/1 when measured on
main at `983c496`.

Which value reaches which output, for the keys `scene_review` actually reads:

| Key | Allowed value | Where it ends up |
|---|---|---|
| `max_objects_soft`, `max_objects_hard` | `int` | compared with `len(transforms)`; the message prints that measured count |
| `max_cameras_keep` | `int` | compared with `cam_count`; the message prints that measured count |
| `min_lights` | `int` | compared with `light_count`, and printed as the required minimum |
| `forbidden_prefixes` | `list[str]` | iterated, each entry goes to `str.startswith` |
| `max_nesting_depth` | `int` | compared with the sampled depth, `+ 2` against the full depth, printed as the allowed maximum, and compared against the full depth again in the organization health score |

The soft object-count warning, the camera, light, naming and nesting messages
are pinned by `tests/test_maya_scene_module.py::TestSceneReviewStandards`. The
hard object-count error (`Excessive objects`, past 2000 transforms) has no test
in this batch and is not covered by that class.

Related check (ticket AC 5): #245 (`finite_float` in `numeric.py`, merged as
`34966c5`) is untouched. This batch changes only how the constants dict is
typed, not how any number is validated or converted, so no numeric-validation
code is rebuilt here.

What is left is the annotation lane only: `no-untyped-def` 9 and
`no-untyped-call` 1, all in `maya_scene_module.py`, baseline 20 lines -> 10.
Those stay for the convergence ticket; they are not part of #255.

## When the stub is upgraded

The `# type: ignore[...]` comments fail the build if the stub starts accepting
the call (`warn_unused_ignores = true`). The `cast(...)` sites do not — remove
each one by hand once the stub declares the shape above, then delete the row
here. Keep the `getPoint` cast until the stub's `getPoint` parameter accepts
the `int` that `MSpace.kWorld` really is (the live run below shows the constant
is a plain `int`, so waiting for it to be declared an enum would wait forever).

## Live results (2026-11-15, issue #253)

Run inside a real Maya 2024 GUI session (24.0.0.4640, Windows 11, Maya-side
Python 3.10.8) with `docs/reference/six_callform_gui_driver.py`, in a fresh
instance with an empty scene. No row is blocked: each one below is a measured
value, not a skip. Artifact:
`docs/evidence/probes/probe-253-six-callforms-gui-maya2024-v2.json`; the
earlier versions stay beside it as `...-v1.json` and `...json`, each marked
superseded.

The shipped test was tightened in the same pass: it now sets
`linear`/`step` and reads both back, because `auto` — which it used
before — is Maya's own default and would read the same on a call that did
nothing. Its `playbackOptions` step sets `min=2, max=12` for the same
reason: a `min` that matched the scene's own start would prove nothing.

| Spot | Live result | What Maya actually returned |
|---|---|---|
| `xform` `q/ws/t/ro` | pass | world translation `[10.0, 0.0, 0.0]`, rotation `[0.0, 0.0, 0.0]` |
| `rename` | pass | returns `str`: `GEO_cf253_name_holder1`; the node already holding the name kept it |
| `keyTangent` `itt/ott` | pass | set to `linear`/`step` (not the default `auto`) and read back as exactly those two |
| `playbackOptions` `min/max` | pass | playback range went `1.0-120.0` to `2.0-12.0`; both ends moved off the scene's own range |
| `aimConstraint` lists | pass | returned `['GEO_cf253_aimed_aimConstraint1']`, the constraint exists |
| `MFnMesh.getPoint` `MSpace.kWorld` | pass | world `[9.5, -0.5, 0.5, 1.0]` vs object `[-0.5, -0.5, 0.5, 1.0]`, a 10.0 gap |

Two details worth carrying into a future stub upgrade:

- `om2.MSpace.kWorld` really is a plain `int` in Maya 2024 (`type()` says
  `int`), and `getPoint` accepts it. The stub is wrong about the parameter
  type, not about the constant — so the cast stays until the parameter is
  declared to take the int the constant is.
- `rename` onto a taken name yields a numbered name (`GEO_cf253_name_holder1`
  in the run above) and does not delete the node that held it first. Code
  must use the returned string, never the name it asked for.

Running under mayapy is still open: `cmds.about(batch=True)` and any batch-only
behaviour cannot be checked from a GUI session, and this box's mayapy fails at
`import maya.standalone`. Nothing here covers Maya 2025 or 2026.
