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
[your application node]   react to emotions (TODO)
```

The three upstream nodes are independent processes connected only by topics —
that is what lets any camera front-end (including this project's) feed the same
face-detection + emotion stack.

---

## Quickstart

Full, first-time setup is in [`SETUP.md`](SETUP.md). Once set up, run
each in its own terminal (source ROS 2 + the workspace in every terminal first):

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
# 1. camera
ros2 launch usb_cam_cv camera.launch.py

# 2. face detection
ros2 launch hri_face_detect face_detect.launch.py image:=/image_raw

# 3. emotion recognition
ros2 launch hri_emotion_recognizer emotion_recognizer.launch.py

# 4. inspect
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

Code (camera package, application node, integrated launch) will be added as the
project progresses — see `PROGRESS.md` for current state.

---

## Emotion labels (FER+)

The default `emotion-ferplus-8.onnx` model outputs 8 classes, in this fixed order:

`neutral, happiness, surprise, sadness, anger, disgust, fear, contempt`

---

## Credits / upstream

- [ros4hri/hri_emotion_recognizer](https://github.com/ros4hri/hri_emotion_recognizer)
- [ros4hri/hri_face_detect](https://github.com/ros4hri/hri_face_detect)
- [ONNX Model Zoo — Emotion FER+](https://github.com/onnx/models/tree/main/validated/vision/body_analysis/emotion_ferplus)
