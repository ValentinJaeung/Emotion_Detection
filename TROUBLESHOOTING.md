# Troubleshooting

Hard-won fixes from getting the camera + pipeline working. Most of these cost
real time to diagnose once — they should never cost time twice.

---

## conda PATH pollution

**Symptoms**
- `rqt_image_view`: `ModuleNotFoundError: No module named 'rclpy._rclpy_pybind11'`
- `colcon build`: `ModuleNotFoundError: No module named 'catkin_pkg'`

**Cause**
miniconda's Python shadows the system Python 3.10 that ROS 2 Humble was built
against. `conda deactivate` only removes the `(base)` prompt — it does **not**
remove miniconda from `$PATH`, so the problem returns in every new terminal.

**Fix**
Comment out the entire `# >>> conda initialize >>>` block in `~/.bashrc`, and
add an opt-in alias **below** the block (inside it, `conda init` overwrites it):

```bash
alias conda-on='source ~/miniconda3/bin/activate'
```

**Verify**
```bash
which python3                     # -> /usr/bin/python3
echo $PATH | grep -c miniconda    # -> 0
```

---

## pip vs apt package shadowing

**The single most expensive class of bug on this project.** Same root shape as
the conda problem below: something is ahead of the apt packages on `sys.path`.

`pip3 install --user <x>` installs to `~/.local/lib/python3.10/site-packages`,
which Python searches **before** `/usr/lib/python3/dist-packages`. ROS 2's
`cv_bridge`, `transforms3d` and friends are apt packages compiled against the
**apt** `numpy` (1.21.5) and **apt** `opencv` (4.5.4). Shadow either one and
things break in ways that point nowhere near the real cause.

Installing `mediapipe` with plain `pip3 install -U mediapipe` pulled in
`numpy 2.2.6` **and** `opencv-contrib-python 5.0.0`, and broke three things:

| Symptom | Actually caused by |
|---------|--------------------|
| `mediapipe` import: `AttributeError: _ARRAY_API not found`, `numpy.core.multiarray failed to import` | pip `numpy 2.x` vs apt `matplotlib` built for numpy 1.x |
| `camera_node`: `cv_bridge ... cv2_to_imgmsg ... KeyError: 16` | pip `opencv 5.0.0` shadowing apt `opencv 4.5.4`; `cv_bridge`'s type table no longer matched its own C extension |
| `hri_face_detect`: `AttributeError: module 'numpy' has no attribute 'float'` in `transforms3d/quaternions.py` | pip `numpy 1.26` (where `np.float` was removed) vs apt `transforms3d` written for numpy < 1.24 |

**Fix — give the apt packages back their precedence:**

```bash
pip3 uninstall -y numpy opencv-contrib-python opencv-python opencv-python-headless
```

**Verify** — all must live under `/usr/lib/python3/dist-packages`:

```bash
python3 -c "import numpy; print(numpy.__version__, numpy.__file__)"   # 1.21.5, apt
python3 -c "import cv2;   print(cv2.__version__, cv2.__file__)"       # 4.5.4,  apt
python3 -c "import mediapipe; print(mediapipe.__version__)"           # 0.10.9
python3 -c "from tf_transformations import quaternion_from_euler; print('ok')"
```

mediapipe 0.10.9 runs fine against the older apt numpy/opencv — its
`requirements.txt` pins are not hard requirements.

**Prevention:** install pip packages with `--no-deps` on this machine, so a
transitive dependency can never silently replace an apt one:

```bash
pip3 install --user --no-deps mediapipe==0.10.9
```

> Debugging tip: `python3 -c "import sys; print('\n'.join(sys.path))"` shows the
> precedence order, and `<module>.__file__` shows which copy actually won.

---

## Remap arguments silently ignored on PAL launch files

**Symptom:** `ros2 launch hri_face_detect face_detect.launch.py image:=/image_raw`
runs with no error, the node reaches `State: Active.`, and
`/humans/faces/tracked` never publishes anything. The launch log even prints
`Remappings: - image -> image`, which reads like confirmation but is not.

**Cause:** `hri_face_detect` and `hri_emotion_recognizer` build their config with
PAL's `get_pal_configuration()`. It creates `DeclareLaunchArgument` entries for
**`parameters` only**. `remappings` are read exclusively from
`config/00-defaults.yml` (or `~/.pal/config` overrides) and **cannot be set from
the command line**. ROS 2 launch discards unrecognised `key:=value` args
silently, so `image:=...` evaporates and the node keeps its default `/image`.

Consequence: the camera published `/image_raw` while face detection listened on
`/image` — nothing connected, and nothing said so.

**Diagnose in 10 seconds** — publisher/subscriber counts are unambiguous:

```bash
ros2 topic info /image      # Publisher count: 0, Subscription count: 1
ros2 topic info /image_raw  # Publisher count: 1, Subscription count: 0
```

**Fix:** remap on the side you control — the camera launch file:

```python
remappings=[('image_raw', 'image')],
```

**Note which knobs *are* CLI-overridable:** anything the launch log lists under
`Parameters ... [overridable]` — e.g. `debug:=true`, `confidence_threshold:=0.5`,
`processing_rate:=15`. Those work exactly as expected.

---

## Lifecycle node stalls at Unconfigured

**Symptom:** `hri_face_detect` (or `hri_emotion_recognizer`) prints
`State: Unconfigured.` and stops there. No error, no crash. It never reaches
`Inactive` / `Active`, so it publishes nothing.

**Cause:** the launch file fires a one-shot `EmitEvent(ChangeState(CONFIGURE))`
at startup. If it is emitted before the node's `change_state` service is up, the
event is dropped and never retried. It is a race, so it is intermittent — the
same command often works on the next run.

**Fix — nudge it manually from another terminal:**

```bash
ros2 lifecycle get /hri_face_detect          # -> unconfigured [1]
ros2 lifecycle set /hri_face_detect configure
```

Configure is enough; the launch file's `OnStateTransition` handler catches the
`inactive` state and fires `ACTIVATE` automatically. Confirm:

```bash
ros2 lifecycle get /hri_face_detect          # -> active [3]
```

---

## Two unlinked copies of a package

**Symptom:** you edit a file, `colcon build` succeeds, and the running node
behaves exactly as before — as if the edit never happened.

**Cause:** on the reference machine the git repo and the build workspace are
**two separate directories**, not a clone and not a symlink:

```
/home/val/Emotion_Detection/usb_cam_cv     <- the git repo (edits land here)
/home/val/ros2_ws/src/usb_cam_cv           <- what colcon builds (not a git repo)
```

This contradicts §3 of [`SETUP.md`](SETUP.md), which describes cloning the repo
*into* the workspace. Editing the repo copy changes nothing about the build.

**Diagnose:**

```bash
diff -r /home/val/Emotion_Detection/usb_cam_cv /home/val/ros2_ws/src/usb_cam_cv
```

**Fix:** apply changes to both copies, or better, replace the workspace copy with
a symlink so they can never diverge again. Always confirm a build actually took
by grepping the *installed* artifact:

```bash
grep -n remappings ~/ros2_ws/install/usb_cam_cv/share/usb_cam_cv/launch/camera.launch.py
```

---

## ROS 2 MJPEG drivers fail on the reference camera

Both `usb_cam` and `v4l2_camera` failed to decode MJPEG on the reference
hardware. The camera, OpenCV, and libavcodec were all fine — the drivers were
the problem.

| Driver / mode           | Result                                    |
|-------------------------|-------------------------------------------|
| `usb_cam` `mjpeg2rgb`   | Segmentation fault (all resolutions)      |
| `usb_cam` `raw_mjpeg`   | No crash, but grey frame + noise band     |
| `usb_cam` `yuyv2rgb`    | Works, but capped at 640x480 @ 25fps      |
| `v4l2_camera` MJPG      | Abort — decoder not implemented           |
| `v4l2_camera` YUYV      | Works at ~5.5fps                          |

**Why 1080p forces MJPEG:** USB 2.0 bandwidth (~35–40 MB/s) cannot carry 1080p
YUYV (~124 MB/s). Only MJPG reaches 1080p, so MJPEG decode had to be solved.

**Resolution:** bypass the ROS 2 drivers — open the camera directly with
OpenCV's V4L2 backend (`cv2.VideoCapture(dev, cv2.CAP_V4L2)`, `FOURCC='MJPG'`,
`BUFFERSIZE=1`) in a small custom node, and publish `sensor_msgs/Image`.

### How the root cause was isolated (repeat this order)
1. Inspect JPEG structure -> valid (`ffd8` start, correct EOI, no trailing).
2. OpenCV decode test -> encode/decode both `True`.
3. Decoded frame -> uniform grey (data was empty, not corrupt JPEG).
4. **Capture outside ROS with ffmpeg** -> real image -> camera is fine.

> Verifying the camera *outside ROS* was the decisive turning point:
> `ffmpeg -f v4l2 -i /dev/videoX -frames:v 1 out.png`

---

## Device numbers are unstable

`/dev/videoN` numbering changes across reboots/replugs, and one camera exposes
two nodes (capture + metadata). Pin a stable name with a udev rule keyed on
VID:PID **and** `ATTR{index}=="0"` (that index selects the capture node). Full
rule and commands are in [`SETUP.md`](SETUP.md#2-identify-the-camera-device).

---

## False fps bottleneck from republish

`/image_raw/compressed` once measured 4.6fps and looked like a camera fault. The
real cause was `image_transport republish` CPU-decoding 1080p MJPEG and stalling
the pipeline. After killing republish: 29.7fps, std dev 0.004s.

> When measuring, kill every unrelated node first. A topic can also report full
> rate while showing a grey frame — always check rate **and** on-screen content.

---

## General debugging order for a new camera / pipeline stage

1. Check the shell (`which python3` — conda pollution).
2. Check devices (`v4l2-ctl --list-devices`).
3. Check hardware capability (`v4l2-ctl -d <dev> --list-formats-ext`) — never
   assume a resolution/fps combo that isn't listed.
4. Check what format names the driver wants vs. what the camera reports
   (`MJPG` != `mjpeg2rgb`).
5. Start low (640x480), then raise resolution.
6. Verify outside ROS first when something breaks.
7. Measure rate, then verify the actual image.
8. Change one thing at a time.
