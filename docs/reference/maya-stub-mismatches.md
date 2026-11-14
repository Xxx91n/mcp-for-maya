# Where `types-maya-strict` disagrees with a shipped Maya call

**What this file is:** the per-spot record behind the type-checking batch in
#229. For each place where the third-party Maya type definitions disagree with
a call the code already ships, it states the stub's claim, what the call
really sends, the evidence for the call form, the handling, and what a live
Maya interpreter still has to confirm. It is the list to read the next time
`types-maya-strict` is upgraded.

**What it is not:** proof of live Maya behaviour. No Maya session was run for
this batch: the mayapy tier is unrunnable on the box that measured it
(`docs/testing.md` Tier 2 records the native access violation when
`maya.standalone` is imported and the `maya.exe -batch` hang), so every live
cell below is still open. The fake Maya test layer (`tests/maya_stub/`)
accepts these same calls, but that proves the calls match the fake, not the
real command; the real-interpreter test
(`tests/test_mayapy_smoke.py::test_callform_stub_disagreement_forms`) is what
turns a cell into a result, and it skips honestly on this box. None of the six
stub forms needs GUI eyes — all six are assertable in batch, which is why
their live column says `mayapy`.

**Measured environment:** `types-maya-strict==2025.0.6`, `mypy==2.3.1`,
`mypy-baseline==0.7.4`, Python from `uv sync --frozen`, base commit `1ece725`
(#227 merged), Windows 11 x64, 2026-11-14.

## The six stub disagreements (17 errors) and the one mixed finding

| Spot | Stub claims | Call sends | If the stub were right | Evidence for the call form | Handling | Live check |
|---|---|---|---|---|---|---|
| `xform` query reads — `analyze_aesthetics`, `scene_review` | flags are `query`/`worldSpace`/`translation`/`rotation` only | `q=`, `ws=`, `t=`, `ro=` | every read would raise a flag error and the lighting scores would lose world positions | Command reference (Maya 2024): `worldSpace(ws)`, `translation(t)`, `rotation(ro)` are the flag's own short names, and the command is queryable | Call unchanged; `cast(Any, cmds.xform)` at the three call sites | `mayapy` |
| `rename` — `create_camera_shot`, `create_orbit_camera` | returns `None` | uses the return value (`... or name`) | the camera keeps the auto-generated name instead of the requested one | Command reference returns "the new name" as a string | Call unchanged; `cast(str, ...)` states the return type | `mayapy` |
| `keyTangent` — `create_orbit_camera` | flags are `inTangentType`/`outTangentType` only | `itt=`, `ott=` | the tangent edit would raise a flag error and the orbit keys stay flat | Command reference lists `inTangentType(itt)` and `outTangentType(ott)`; both are also on its global-flag list | Call unchanged; `# type: ignore[call-overload]` on that line | `mayapy` |
| `playbackOptions` — `create_orbit_camera` | flags are `minTime`/`maxTime` only | `min=`, `max=` | the playback range would raise a flag error and stay at the scene default | Command reference lists `min` -> `minTime` and `max` -> `maxTime` | Call unchanged; `# type: ignore[call-overload]` on that line | `mayapy` |
| `aimConstraint` — `create_camera_shot`, `create_orbit_camera` | `aimVector`/`upVector` are `tuple[float, float, float]` | three-number lists `[0, 0, -1]`, `[0, 1, 0]` | the constraint call would reject the arguments and the camera would fall back to manual rotation | Command reference types both flags as three doubles; a Python list of three numbers is the same flag value | Call unchanged; `# type: ignore[call-overload]` on each call line | `mayapy` |
| `MFnMesh.getPoint` — `get_scene_graph` full detail | parameter is `MSpace`, but `MSpace.kWorld` is declared `ClassVar[int]` in the same stub file | `om2.MSpace.kWorld` | the vertex dump would lose its world-space points (the call is inside a `try`) | The stub contradicts itself: the value it declares `int` is the value its own parameter type expects | Call unchanged; `cast(om2.MSpace, ...)` records the value Maya really passes | `mayapy` |
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

## What the remaining 67 baseline entries are

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

## When the stub is upgraded

The `# type: ignore[...]` comments fail the build if the stub starts accepting
the call (`warn_unused_ignores = true`). The `cast(...)` sites do not — remove
each one by hand once the stub declares the shape above, then delete the row
here. Keep the `getPoint` cast until `MSpace.kWorld` is declared as the enum
the parameter expects.
