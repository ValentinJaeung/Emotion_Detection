# Progress Log

The single place to answer "where is this project right now?" when picking it up
on another machine or after a break. Update the **Status board** whenever a phase
changes, and add a dated entry under **Log** for anything non-obvious.

Legend: ✅ done · 🔄 in progress · ⛔ blocked · ⬜ not started

---

## Status board

| Phase | Task                                              | Status | Notes                                  |
|-------|---------------------------------------------------|--------|----------------------------------------|
| 1     | Environment check (conda / device / camera)       | ✅     | see SETUP.md §0 machine profile        |
| 2     | Install hri_face_detect + emotion_recognizer      | ✅     | both built from source; ONNX model + pyhri resolved |
| 3     | Wire camera into pipeline (topic / QoS / cam_info) | ✅     | only topic name needed a fix — remapped in usb_cam_cv's own launch file; QoS and camera_info were non-issues, see SETUP.md §5 |
| 4     | Verify full pipeline (rate + on-screen content)   | ✅     | `expression: happy, confidence: 0.9986` confirmed live |
| 5     | Application node (react to `expression`)          | 🔄     | `emotion_reactor` package scaffolded, builds and runs; `react()` is a logging stub — behavior mapping still TODO |
| 6     | Tuning + cleanup (brightness / resolution / model) | ⬜     |                                        |

---

## Current focus

_One or two sentences: what you are doing right now and the very next action._

- Now: `emotion_reactor` ROS 2 package scaffolded — `HRIListener`-based node
  with confidence thresholding, a majority-vote smoothing window per face id,
  and `on_face_lost` cleanup so state never leaks across ephemeral ids. Builds
  and runs cleanly against the real workspace; `react()` only logs so far.
- Next: decide what `react()` should actually do (the robot-behavior mapping,
  e.g. stop on `surprise`), implement it, then run it live against the full
  pipeline to tune `confidence_threshold` / `smoothing_window`.

---

## Open blockers

_Anything stopping progress. Move to the Log with a resolution when cleared._

_None currently._

---

## Decisions made

_Choices that would otherwise get re-litigated on another machine._

- Camera front-end: custom OpenCV V4L2 node (ROS 2 drivers `usb_cam` /
  `v4l2_camera` failed MJPEG decode on the reference camera — see
  `TROUBLESHOOTING.md`).
- Face detection: `hri_face_detect` (ROS4HRI), not a bespoke detector — keeps
  the emotion node reusable.
- Topic wiring fix lives on the **camera** side (`usb_cam_cv/launch/camera.launch.py`
  remaps `image_raw` -> `image`), not on `hri_face_detect`, because PAL's launch
  config makes `hri_face_detect`'s remappings uneditable from the CLI. See
  `SETUP.md` §5a / `TROUBLESHOOTING.md`.
- Never `pip install` `numpy` or `opencv*` on this machine — apt owns them.
  See `TROUBLESHOOTING.md#pip-vs-apt-package-shadowing`.

---

## Log

Newest entries on top. Format: `YYYY-MM-DD — short title`, then what happened,
why it matters, and the exact commands/paths involved.

### 2026-09-09 — Fixed laggy `emotion_viewer_node`
- Symptom: video played in visible slow motion once the box/label overlay
  was on screen. Cause: default reliable/depth-10 subscription queued
  frames faster than `imshow` at full 1080p could draw+display them, so
  playback fell behind and replayed the backlog.
- Fix: best-effort, depth-1 QoS on the image subscription (always renders
  the latest frame, drops stale ones) + downscale to `display_scale` (0.5
  default) before drawing/display. Confirmed smooth by the user.

### 2026-09-09 — Added `emotion_viewer_node` (visual sanity check)
- New node in `emotion_reactor`: shows the full `/image` feed with each
  tracked face's bounding box (`face.roi`, normalized xywh -> pixel coords)
  and `EXPRESSION percentage%` label drawn above it via OpenCV `imshow`.
- Debug/visualization only — no reaction logic, separate from
  `emotion_reactor_node`. Press `q` in the window or Ctrl+C to quit.
- Run: `ros2 run emotion_reactor emotion_viewer_node`.
- Verified: builds and the module imports cleanly; not yet eyeballed live
  against a real face (no GUI available in this session).

### 2026-09-09 — Scaffolded the `emotion_reactor` application node
- New `ament_python` package `emotion_reactor` (repo: `emotion_reactor/`,
  workspace: `~/ros2_ws/src/emotion_reactor` — remember these are two
  unlinked copies, see `TROUBLESHOOTING.md#two-unlinked-copies-of-a-package`).
- `emotion_reactor_node.py` uses `HRIListener` (pyhri) directly rather than
  subscribing to the raw `Expression` topic — `face.expression` /
  `face.expression_confidence` give the same data with tracking handled.
- Per-face state: a `deque(maxlen=smoothing_window)` of expressions that
  passed `confidence_threshold`, majority-voted each tick; only reacts on a
  *change* in the smoothed result (debounced), and state is dropped in
  `HRIListener.on_face_lost` so nothing leaks across ephemeral face ids.
- `react()` is currently just a log line — the actual robot-behavior mapping
  (which emotion does what) is still undecided; that's the next real work.
- Verified: builds clean with `colcon build --packages-select emotion_reactor`
  and runs without error via `ros2 run emotion_reactor emotion_reactor_node`
  (no faces tracked in that smoke test, so `react()` was not exercised live).

### 2026-09-09 — Full pipeline working end to end
- Built `hri_face_detect` and `hri_emotion_recognizer` from source; installed
  the undocumented runtime dep `ros-humble-pyhri` (upstream marks it
  `test_depend` only, but `hri_emotion_recognizer` imports it at runtime).
- Confirmed the ONNX model blocker in the old log entry below was already
  resolved — model was present at `~/ros2_ws/src/hri_emotion_models/models/`.
- Hit and fixed three cascading pip-vs-apt shadowing bugs
  (`cv_bridge KeyError: 16`, `transforms3d np.float`, mediapipe numpy ABI) —
  root cause and fix in `TROUBLESHOOTING.md#pip-vs-apt-package-shadowing`.
- Found `image:=/image_raw` on the `hri_face_detect` launch command was a
  no-op the whole time (PAL launch config quirk) — real fix is a remap in
  `usb_cam_cv`'s own launch file. See `TROUBLESHOOTING.md`.
- Hit a lifecycle-node race (`State: Unconfigured.` hang) — worked around with
  a manual `ros2 lifecycle set ... configure`.
- Discovered the git repo and `~/ros2_ws/src/usb_cam_cv` are two unlinked
  copies — a repo edit doesn't reach the build until applied to both. See
  `TROUBLESHOOTING.md#two-unlinked-copies-of-a-package`.
- End result: live `/humans/faces/<id>/expression` reading
  `expression: happy, confidence: 0.9986213445663452`.

### 2026-09-08 — Camera pipeline stabilized (from handover doc)
- Custom OpenCV camera node publishes `/image_raw` at 1920x1080 ~28–30fps.
- Root cause of prior grey/segfault frames: ROS 2 MJPEG drivers, not the
  hardware. Details in `TROUBLESHOOTING.md`.

<!--
### YYYY-MM-DD — title
- what changed
- why it matters
- commands / paths
-->
