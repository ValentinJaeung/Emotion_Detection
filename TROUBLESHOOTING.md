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
