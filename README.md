# Emotion_Detection

Real-time facial **emotion recognition on ROS 2**, built on top of a USB camera.
The pipeline reuses the [ROS4HRI](https://wiki.ros.org/hri) framework: a custom
OpenCV camera node publishes frames, `hri_face_detect` finds faces, and
`hri_emotion_recognizer` classifies the emotion of each face with an ONNX FER+ model.

> **Goal of this repo:** keep the project reproducible across machines.
> Every environment-specific value (device path, camera VID/PID, topic names)
> lives in [`SETUP.md`](SETUP.md) as a fill-in field, so the same
> code runs anywhere once those fields are set.

---

## Environment (reference machine)

| Item      | Value                                            |
|-----------|--------------------------------------------------|
| OS        | Ubuntu 22.04.5 LTS (Jammy)                        |
| ROS 2     | Humble                                            |
| Install   | Native (migrated from WSL2)                       |
| Camera    | _fill in per machine — see `SETUP.md`_       |
| Python    | System `/usr/bin/python3` (3.10) — **not** conda  |

See [`SETUP.md`](SETUP.md) for the full, reproducible setup.

---

## Pipeline architecture

```
[camera node]  (this project — OpenCV V4L2 capture)
   /image_raw            sensor_msgs/Image
        |
        v
[hri_face_detect]        Mediapipe / YuNet face detection
   /humans/faces/tracked           face IDs currently tracked
   /humans/faces/<id>/roi          bounding box of each face
        |
        v
[hri_emotion_recognizer]  crop face -> FER+ ONNX -> emotion
   /humans/faces/<id>/expression   emotion + confidence
        |
        v
[emotion_reactor]   confidence threshold + temporal smoothing per face,
                     react() on a stable change (currently logs only —
                     the robot-behaviour mapping is still TODO)
[emotion_viewer]     live camera feed with box + expression % overlay
                      (visual sanity check, no reaction logic)
```

The three upstream nodes are independent processes connected only by topics —
that is what lets any camera front-end (including this project's) feed the same
face-detection + emotion stack.

---

## Quickstart

Full, first-time setup is in [`SETUP.md`](SETUP.md). Once set up, this is how
you turn the whole pipeline on: **one process per terminal**, left running,
in order. Each stage feeds the next one over ROS topics, so terminal 2 won't
produce anything until terminal 1 is up, and so on.

In **every** terminal below, before running its command, source ROS 2 and
the workspace:

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
```

**Terminal 1 — camera.** Opens the USB camera and starts publishing raw
video frames. Nothing downstream works until this is running.
```bash
ros2 launch usb_cam_cv camera.launch.py
```

**Terminal 2 — face detection.** Subscribes to the camera feed, finds faces
in each frame, and publishes a bounding box per face.
```bash
ros2 launch hri_face_detect face_detect.launch.py
```

**Terminal 3 — emotion recognition.** Crops each detected face and runs it
through the FER+ model, publishing an emotion label + confidence per face.
```bash
ros2 launch hri_emotion_recognizer emotion_recognizer.launch.py
```

**Terminal 4 — application node.** Reads those emotion results, applies a
confidence threshold and smooths out frame-to-frame flicker, and reacts
whenever a face settles on a new, stable emotion. Right now "react" just
means logging it to this terminal — see `ARCHITECTURE.md` for what's
implemented vs. still open.
```bash
ros2 run emotion_reactor emotion_reactor_node
```

**Terminal 5 — live viewer (optional).** Pops up a window showing your
camera feed with a green box drawn around each detected face and a label
above it like `HAPPY 92%`. This is the one to run if you just want to
*watch* the system work. Press `q` in the window (or Ctrl+C here) to quit.
```bash
ros2 run emotion_reactor emotion_viewer_node
```

**Terminal 6 — raw topic inspection (optional).** Skip the app node/viewer
and read the underlying data directly as text.
```bash
ros2 topic echo /humans/faces/tracked
ros2 topic echo /humans/faces/<face_id>/expression
```

---

## Repository map

| Path                        | What it holds                                             |
|-----------------------------|----------------------------------------------------------|
| `README.md`                 | This overview                                             |
| `SETUP.md`             | Reproducible, per-machine setup (fill-in fields)          |
| `PROGRESS.md`          | Running log of what is done / in progress / blocked       |
| `ARCHITECTURE.md`      | How the pipeline and the FER+ model work                  |
| `TROUBLESHOOTING.md`   | Hard-won fixes (camera, conda, MJPEG, topic wiring)       |
| `usb_cam_cv/`           | Camera node package (OpenCV V4L2 capture)                 |
| `emotion_reactor/`      | Application node (`emotion_reactor_node`) + live viewer (`emotion_viewer_node`) |

See `PROGRESS.md` for current state — the application node's `react()` is
still a logging stub; the emotion-to-behaviour mapping is the next real work.

---

## Emotion labels (FER+)

The default `emotion-ferplus-8.onnx` model outputs 8 classes, in this fixed order:

`neutral, happiness, surprise, sadness, anger, disgust, fear, contempt`

---

## Credits / upstream

- [ros4hri/hri_emotion_recognizer](https://github.com/ros4hri/hri_emotion_recognizer)
- [ros4hri/hri_face_detect](https://github.com/ros4hri/hri_face_detect)
- [ONNX Model Zoo — Emotion FER+](https://github.com/onnx/models/tree/main/validated/vision/body_analysis/emotion_ferplus)
