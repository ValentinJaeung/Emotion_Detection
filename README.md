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

Full, first-time setup is in [`SETUP.md`](SETUP.md). Once set up, run each
step below in its own terminal, sourcing both of these first:

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
```

```bash
# 1. camera
ros2 launch usb_cam_cv camera.launch.py

# 2. face detection
ros2 launch hri_face_detect face_detect.launch.py

# 3. emotion recognition
ros2 launch hri_emotion_recognizer emotion_recognizer.launch.py

# 4. application node — reacts to a stable, confident expression change
#    per face (currently just logs it; see ARCHITECTURE.md)
ros2 run emotion_reactor emotion_reactor_node

# 5. optional — live visual check: camera feed with a box + "EXPRESSION NN%"
#    label over each tracked face
ros2 run emotion_reactor emotion_viewer_node

# 6. inspect the raw topics directly instead of/alongside the above
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
