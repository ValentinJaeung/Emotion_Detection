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
| 2     | Install hri_face_detect + emotion_recognizer      | ⬜     | ONNX model file is the likely blocker  |
| 3     | Wire camera into pipeline (topic / QoS / cam_info) | 🔄     | usb_cam_cv publishes /image_raw; QoS/camera_info not yet checked |
| 4     | Verify full pipeline (rate + on-screen content)   | ⬜     |                                        |
| 5     | Application node (react to `expression`)          | ⬜     | the actual project goal                |
| 6     | Tuning + cleanup (brightness / resolution / model) | ⬜     |                                        |

---

## Current focus

_One or two sentences: what you are doing right now and the very next action._

- Now: Camera stage done (usb_cam_cv, /image_raw @ ~28-30fps, 1920x1080).
- Next: Install hri_face_detect + hri_emotion_recognizer, then wire topic/QoS/camera_info (Phase 3).

---

## Open blockers

_Anything stopping progress. Move to the Log with a resolution when cleared._

- [ ] ONNX `emotion-ferplus-8.onnx` — confirm the model source is reachable and
      record the exact install path (see `SETUP.md` §4c).

---

## Decisions made

_Choices that would otherwise get re-litigated on another machine._

- Camera front-end: custom OpenCV V4L2 node (ROS 2 drivers `usb_cam` /
  `v4l2_camera` failed MJPEG decode on the reference camera — see
  `TROUBLESHOOTING.md`).
- Face detection: `hri_face_detect` (ROS4HRI), not a bespoke detector — keeps
  the emotion node reusable.

---

## Log

Newest entries on top. Format: `YYYY-MM-DD — short title`, then what happened,
why it matters, and the exact commands/paths involved.

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
