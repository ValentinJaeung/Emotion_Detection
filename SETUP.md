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
ONNX model path:     ~/ros2_ws/src/hri_emotion_models/models/emotion-ferplus-8.onnx
```

> ⚠️ **On the reference machine, `~/ros2_ws/src/usb_cam_cv` is a separate copy of
> this repo's package, not a clone of it.** Editing this repo and running
> `colcon build` then silently builds the *old* code. Verify which copy feeds the
> build before editing (`diff -r`), or symlink the workspace copy at the repo.
> See [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md#two-unlinked-copies-of-a-package).

---

## 1. Verify the Python environment (do this first, every new terminal)

The #1 recurring failure on this project is **something shadowing the system
Python packages** that ROS 2 Humble was built against. Confirm before anything else:

```bash
which python3            # MUST be /usr/bin/python3
echo $PATH | grep -c miniconda   # MUST be 0

# these MUST resolve to /usr/lib/python3/dist-packages, NOT ~/.local
python3 -c "import numpy; print(numpy.__version__, numpy.__file__)"   # 1.21.5, apt
python3 -c "import cv2;   print(cv2.__version__, cv2.__file__)"       # 4.5.4,  apt
```

If conda is on `$PATH`, comment out the `# >>> conda initialize >>>` block in
`~/.bashrc`, open a new terminal, and re-check. See
[`TROUBLESHOOTING.md`](TROUBLESHOOTING.md#conda-path-pollution) for the full fix.

> ### 🚫 Golden rule: let **apt** own `numpy` and `opencv`
>
> `pip install` drops packages into `~/.local/lib/python3.10/site-packages`,
> which sits **before** `/usr/lib/python3/dist-packages` on `sys.path` and so
> shadows the apt builds that `cv_bridge`, `transforms3d` and the rest of ROS 2
> were compiled against. On this project that single mistake broke three
> different things in a row. Never `pip install` `numpy`, `opencv-python`, or
> `opencv-contrib-python` on this machine — not even as a transitive dependency.
> Full symptoms and fixes:
> [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md#pip-vs-apt-package-shadowing).

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

### 4a. Shared dependencies (apt)

```bash
sudo apt install \
  ros-humble-hri-msgs \
  ros-humble-launch-pal \
  ros-humble-diagnostic-aggregator \
  ros-humble-pyhri
```

> `ros-humble-pyhri` is **required at runtime** by `hri_emotion_recognizer`
> (it does `from hri import HRIListener`), but upstream lists it only as a
> `test_depend`, so `rosdep` will not pull it in. Without it the node dies with
> `ModuleNotFoundError: No module named 'hri'`.

### 4b. Face detection — build from source

**There is no `ros-humble-hri-face-detect` apt package.** It does not exist in
the ROS 2 apt repos for Humble under any name (`apt-cache search hri-face` only
returns `hri-face-body-matcher`). Build it from source:

```bash
cd <ros_workspace>/src
git clone https://github.com/ros4hri/hri_face_detect.git
cd <ros_workspace>
colcon build --packages-select hri_face_detect
```

Its Python dependency is **mediapipe**. Installing it with pip will drag in a
newer `numpy`/`opencv` and break ROS 2 — read the golden rule in §1 first, then:

```bash
pip3 install --user --no-deps mediapipe==0.10.9
```

`--no-deps` is what keeps pip from replacing the apt `numpy`/`opencv`.
Afterwards, re-run the §1 verification block and confirm `numpy` and `cv2` still
resolve to `/usr/lib/python3/dist-packages`.

A `pal_module_cmake` CMake warning during the build is **harmless** — that
package is PAL-internal and guarded by `condition="$PAL_DISTRO != ''"`.

### 4c. Emotion recognizer

```bash
cd <ros_workspace>/src
git clone https://github.com/ros4hri/hri_emotion_recognizer.git
cd <ros_workspace>
colcon build --packages-select hri_emotion_recognizer
```

### 4d. ONNX emotion model  ✅ resolved

The node needs `emotion-ferplus-8.onnx`, supplied by the `hri_emotion_models`
package. On the reference machine this resolved without needing the ONNX Model
Zoo fallback. Confirmed working path:

```
~/ros2_ws/src/hri_emotion_models/models/emotion-ferplus-8.onnx
  -> installed to ~/ros2_ws/install/hri_emotion_models/share/hri_emotion_models/models/
```

The model is loaded with **`cv2.dnn.readNetFromONNX`**, not `onnxruntime` —
do **not** install `onnxruntime`, it is not a dependency.

Verify the node found it; on startup it logs:
`Loaded emotion model: /.../emotion-ferplus-8.onnx`

---

## 5. Wire the camera into the pipeline

Of the three interfaces originally flagged here, **only the topic name actually
needed work.** The other two were non-issues; they are documented below so they
do not get "fixed" again on the next machine.

### 5a. Topic name — the one that matters ⚠️

**`image:=/image_raw` on the `hri_face_detect` launch command does nothing.**
It fails silently — no error, no warning, and the launch log even prints a
reassuring `Remappings: - image -> image`.

`hri_face_detect` uses PAL's `get_pal_configuration()`, which turns **only
`parameters`** into CLI-overridable launch arguments. **`remappings` can never
be set from the command line** — they come solely from the package's
`config/00-defaults.yml` (or a user override under `~/.pal/config`). Any
unrecognised `key:=value` is discarded without complaint.

So `hri_face_detect` always subscribes to **`/image`**, its built-in default.

**The fix used here** — remap on the *camera* side, in
[`usb_cam_cv/launch/camera.launch.py`](usb_cam_cv/launch/camera.launch.py):

```python
Node(
    package='usb_cam_cv',
    executable='camera_node',
    ...
    remappings=[('image_raw', 'image')],
)
```

The camera node's code still publishes `image_raw`; the launch file remaps it to
`/image` so it lands on the topic `hri_face_detect` is already listening to. No
arguments are needed on the face-detect side at all.

> **How to diagnose this class of bug in 10 seconds.** Publisher and subscriber
> counts do not lie:
> ```bash
> ros2 topic info /image      # Publisher count: 0, Subscription count: 1  <- nobody is feeding it
> ros2 topic info /image_raw  # Publisher count: 1, Subscription count: 0  <- talking to nobody
> ```
> Two ships passing in the night. Check this *before* suspecting QoS or the model.

### 5b. QoS — no change needed ✅

The earlier concern that the publisher must be **Best Effort** was unfounded.
DDS compatibility requires the *offered* QoS to be at least as strong as the
*requested* one, and `RELIABLE` is stronger than `BEST_EFFORT`. So a `RELIABLE`
camera publisher and `hri_face_detect`'s `BEST_EFFORT` subscription
(`qos_profile_sensor_data`) connect **fine**. The camera node ships `RELIABLE`
and works as-is.

### 5c. camera_info — optional ✅

`hri_face_detect` subscribes to `camera_info`, but only to obtain the intrinsics
matrix for **6D head pose and gaze TF frames**, and that use is guarded:

```python
if hasattr(self, 'k'):
    face.compute_6d_pose(...)
```

With no `camera_info` publisher, face detection, tracking, ROIs and **emotion
recognition all work normally** — you simply get no head-pose/gaze transforms.
Only add a `CameraInfo` publisher if you need 3D pose downstream.

---

## 6. Verify end to end

Source **both** setup files in every terminal:

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
```

```bash
# terminal 1 — camera  (publishes /image, see §5a)
ros2 launch usb_cam_cv camera.launch.py

# terminal 2 — face detection.  NO image:= argument; debug:=true opens a live
# window with boxes drawn on detected faces (debug IS a parameter, so it IS
# overridable — unlike remappings).
ros2 launch hri_face_detect face_detect.launch.py debug:=true

# terminal 3 — emotion
ros2 launch hri_emotion_recognizer emotion_recognizer.launch.py

# terminal 4 — read the result. Face IDs are random and change whenever
# tracking is lost, so discover the current one rather than hardcoding it:
ID=$(ros2 topic list | grep expression | head -1 | sed 's|/humans/faces/||; s|/expression||')
ros2 topic echo /humans/faces/$ID/expression
```

Expected healthy output:

```
expression: happy
confidence: 0.9986213445663452
```

### Things that look broken but are not

- **All three nodes must reach `State: Active.`** `hri_face_detect` and
  `hri_emotion_recognizer` are **lifecycle** nodes. If one stalls at
  `State: Unconfigured.`, nudge it (see
  [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md#lifecycle-node-stalls-at-unconfigured)):
  ```bash
  ros2 lifecycle set /hri_face_detect configure   # auto-activates afterwards
  ```
- **`ros2 topic echo` is not a GUI.** It prints text to the same terminal and
  prints *nothing at all* when no face is visible. For a visual check use
  `debug:=true` above.
- **`/humans/faces/tracked` only publishes when a frame arrives.** Total silence
  there means no image is reaching face detection — go check §5a's
  `ros2 topic info` trick, not the model.
- **FER+ is strongly biased toward `neutral`.** Subtle expressions will not move
  it; grin broadly to confirm the classifier responds.

Check **both** rate and content: a topic can flow at full rate while the frame
is grey/empty. Add the RViz Humans plugin to confirm labels are correct on-screen.

---

## Environment differences log

When a machine needs something the reference machine didn't, record it here so
the next person hits it in the docs, not in the terminal.

| Date | Machine | Difference / extra step needed |
|------|---------|--------------------------------|
|      |         |                                |
