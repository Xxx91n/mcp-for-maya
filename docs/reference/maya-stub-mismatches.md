# Where `types-maya-strict` disagrees with a working Maya call

**What this file is:** the per-spot record behind the type-checking batch in
#229. For each place where the third-party Maya type definitions disagree with
a call the code already makes, it states the stub's claim, what the call
really sends, the evidence for keeping the call, how the type checker was
quieted, and what a live session still has to confirm. It is the list to read
the next time `types-maya-strict` is upgraded.

**What it is not:** proof of live Maya behaviour. No Maya session was run for
this batch (`mayapy` is unreachable on the machine that measured it), so the
live column stays `human_verify`. The fake Maya test layer
(`tests/maya_stub/`) passing these same calls proves the calls match the fake,
not the real command.

**Measured environment:** `types-maya-strict==2025.0.6`, `mypy==2.3.1`,
`mypy-baseline==0.7.4`, Python from `uv sync --frozen`, baseline commit
`1ece725` (#227 merged), Windows 11 x64, 2026-11-14.

## The six stub disagreements (17 errors) and the one mixed finding

| Spot | Stub claim | Call sends | Evidence for the call | Handling | Live check |
|---|---|---|---|---|---|
| `xform` query reads — `analyze_aesthetics`, `scene_review` | flags are `query`/`worldSpace`/`translation`/`rotation` only (`maya-stubs/cmds/__init__.pyi` `xform`) | `q=`, `ws=`, `t=`, `ro=` | The Maya command reference lists `worldSpace(ws)`, `translation(t)`, `rotation(ro)` as the flag's own short names, and marks the command queryable (the query flag is `q`) | Call unchanged; `cast(Any, cmds.xform)` at the three call sites | `human_verify` |
| `rename` — `create_camera_shot`, `create_orbit_camera` | `-> None` (`maya-stubs/cmds/__init__.pyi` `rename`) | uses the return value (`... or name`) | The command reference returns "the new name" as a string | Call unchanged; `cast(str, ...)` states the return type | `human_verify` |
| `keyTangent` — `create_orbit_camera` | flags are `inTangentType`/`outTangentType` only | `itt=`, `ott=` | The command reference lists `inTangentType(itt)` and `outTangentType(ott)`; both are also on its global-flag list | Call unchanged; `# type: ignore[call-overload]` on that line | `human_verify` |
| `playbackOptions` — `create_orbit_camera` | flags are `minTime`/`maxTime` only | `min=`, `max=` | The command reference lists `min` -> `minTime` and `max` -> `maxTime` | Call unchanged; `# type: ignore[call-overload]` on that line | `human_verify` |
| `aimConstraint` — `create_camera_shot`, `create_orbit_camera` | `aimVector`/`upVector` are `tuple[float, float, float]` | three-number lists `[0, 0, -1]`, `[0, 1, 0]` | The reference types the flag as three doubles; a Python list of three numbers is the same flag value | Call unchanged; `# type: ignore[call-overload]` on each call line | `human_verify` |
| `MFnMesh.getPoint` — `get_scene_graph` full detail | parameter is `MSpace`, but `MSpace.kWorld` is declared `ClassVar[int]` in the same stub file | `om2.MSpace.kWorld` | The stub contradicts itself: the enum value it declares `int` is the value its own parameter type expects | Call unchanged; `cast("om2.MSpace", ...)` records the value Maya really passes | `human_verify` |
| `cmds.camera` — `create_camera_shot` (the mixed one) | overloads are narrow but usable | `focalLength=shot["focal_length"]` was inferred `object` | The `object` came from the local `SHOT_TYPES` literal, not from the stub | Local fix: `SHOT_TYPES: dict[str, dict[str, Any]]`; the call is unchanged | none needed |

The live check for six of these is
`tests/test_human_verify.py::test_stub_mismatch_call_forms_real_maya` — a
`human_verify` entry that prints the steps and always skips. It is the mayapy
tier booked as a manual checklist because no healthy interpreter is reachable
on this machine; running it is what turns any `human_verify` cell above into a
recorded result.

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
total: 18 entries removed, 0 added, so no new finding hid behind an old
message. `uv run mypy-baseline sync < mypy-report.txt` regenerated
`mypy-baseline.txt` (100 lines -> 67); `mypy-baseline filter` then reported
`new 0`, `fixed 0`, exit 0.

## What the remaining 67 baseline entries are

- 54 missing annotations: `no-untyped-def` 31, `no-untyped-call` 23.
- 13 container/inference findings with local causes, not stub causes:
  `operator` 7, `str-format` 3, `attr-defined` 1, `var-annotated` 1,
  `assignment` 1. Most come from `_MAYA_STANDARDS`, an untyped dict whose
  values are inferred `object`; #213 already named that root and singled out
  `scene_review`'s `sub_scores["decay"]` (a float stored into a dict first
  inferred `int`) as its own thing to look at.
- Keeping the baseline is still reasonable: the remaining errors are local
  typing gaps with no evidence of runtime faults, and the stub disputes are
  now either cast or ignored at single points, each with a reason above.

## When the stub is upgraded

The `# type: ignore[...]` comments fail the build if the stub starts accepting
the call (`warn_unused_ignores = true`). The `cast(...)` sites do not — remove
each one by hand once the stub declares the shape above, then delete the row
here. Keep the `getPoint` cast until `MSpace.kWorld` is declared as the enum
the parameter expects.
