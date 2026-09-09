# Setup Guide

This guide makes the project reproducible on any machine. **Everything that
changes between machines is a fill-in field marked `<...>`.** Fill the
"Machine profile" table first, then follow the steps top to bottom.

---

## 0. Machine profile (fill this in per machine)

Copy this block and record the real values for the machine you are on. This is
the single source of truth for the fill-in fields used below.

```
Hostname:            val-Vivobook-ASUSLaptop-M7600QC-M7600QC
OS / ROS 2:          Ubuntu 22.04.5 LTS (Jammy) / Humble
Camera model:        Jieli Technology USB PHY 2.0: USB 2.0 Camera
Camera VID:PID:      1224:2a25
Capture device:      /dev/video2
udev symlink:        /dev/usb_cam
Working resolution:  1920x1080 @ 30fps, MJPG
ROS workspace:       ~/ros2_ws
```

---

## 1. Verify the Python environment (do this first, every new terminal)

The #1 recurring failure on this project is **conda shadowing the system Python**
that ROS 2 Humble was built against. Confirm before anything else:

```bash
which python3            # MUST be /usr/bin/python3
echo $PATH | grep -c miniconda   # MUST be 0
```

If conda is on `$PATH`, comment out the `# >>> conda initialize >>>` block in
`~/.bashrc`, open a new terminal, and re-check. See
[`TROUBLESHOOTING.md`](TROUBLESHOOTING.md#conda-path-pollution) for the full fix.

---

## 2. Identify the camera device

Camera device numbers are **not stable** across reboots/replugs. Identify the
real capture node, then (recommended) pin it with a udev rule.

```bash
# list all video devices and which physical camera they belong to
v4l2-ctl --list-devices

# confirm the formats/resolutions the camera actually supports
v4l2-ctl -d <capture_device> --list-formats-ext
```

A single camera often exposes **two** `/dev/videoN` nodes — the first is the
capture node, the second is metadata. Use the capture node.

**Recommended — pin a stable name with udev** (`/etc/udev/rules.d/99-usb-camera.rules`):

```
SUBSYSTEM=="video4linux", ATTRS{idVendor}=="<VID>", ATTRS{idProduct}=="<PID>", ATTR{index}=="0", SYMLINK+="usb_cam"
```

`ATTR{index}=="0"` is what distinguishes the capture node from the metadata node.
Apply:

```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
ls -l /dev/usb_cam    # -> should point at your capture device
```

Record VID:PID, the capture device, and the symlink in your machine profile.

---

## 3. Set up the ROS 2 workspace

```bash
mkdir -p <ros_workspace>/src
cd <ros_workspace>/src
git clone https://github.com/ValentinJaeung/Emotion_Detection.git
```

Source ROS 2 (and later the workspace) in **every** terminal:

```bash
source /opt/ros/humble/setup.bash
source <ros_workspace>/install/setup.bash   # after the first build
```

---

## 4. Install the ROS4HRI packages

### 4a. Face detection

```bash
sudo apt install ros-humble-hri-face-detect
```

### 4b. Emotion recognizer

There may be no apt package for this one (upstream is PAL-internal). If not,
build from source:

```bash
cd <ros_workspace>/src
git clone https://github.com/ros4hri/hri_emotion_recognizer.git
cd <ros_workspace>
colcon build --packages-select hri_emotion_recognizer
```

### 4c. ONNX emotion model  ⚠️ likely blocker

The node needs the model file `emotion-ferplus-8.onnx`. The repo points to a
PAL GitLab `hri_emotion_models` repo that may be inaccessible. If so, download
the model directly from the ONNX Model Zoo and place it where the node's `model`
parameter expects it (typically `hri_emotion_models/models/`).

> Record the exact path you placed the model at, so other machines match it.

---

## 5. Wire the camera into the pipeline

This is the real integration work. Three interfaces must match between the
camera node (`/image_raw`) and `hri_face_detect` (`image` + `camera_info`).

1. **Topic name** — either remap at launch (`image:=/image_raw`) **or** publish
   under a `camera` namespace so it becomes `/camera/image_raw` (preferred —
   scales to multiple cameras and matches the `<camera namespace>` convention).
2. **QoS** — `hri_face_detect` and the RViz Humans plugin expect the image
   topic QoS to be **Best Effort**. Match it on the camera publisher.
3. **camera_info** — if the camera node only publishes `sensor_msgs/Image`,
   add a `CameraInfo` publisher (real calibration or a dummy) when face_detect
   requires it.

> Change **one** of these at a time — mixing changes makes failures unreadable.

---

## 6. Verify end to end

```bash
# terminal 1 — camera
ros2 launch usb_cam_cv camera.launch.py
ros2 topic hz /image_raw          # expect your target fps

# terminal 2 — face detection
ros2 launch hri_face_detect face_detect.launch.py image:=/image_raw
ros2 topic echo /humans/faces/tracked      # expect face IDs when a face is visible

# terminal 3 — emotion
ros2 launch hri_emotion_recognizer emotion_recognizer.launch.py
ros2 topic echo /humans/faces/<face_id>/expression   # expect emotion + confidence
```

Check **both** rate and content: a topic can flow at full rate while the frame
is grey/empty. Add the RViz Humans plugin to confirm labels are correct on-screen.

---

## Environment differences log

When a machine needs something the reference machine didn't, record it here so
the next person hits it in the docs, not in the terminal.

| Date | Machine | Difference / extra step needed |
|------|---------|--------------------------------|
|      |         |                                |
