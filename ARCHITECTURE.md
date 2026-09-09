# Architecture

How the pipeline is put together and how emotion recognition actually works.

---

## Why three separate nodes

The FER+ model can only classify an **already-cropped face**. It cannot find
where faces are in an image. So the work is split:

- **camera node** — produces frames.
- **`hri_face_detect`** — finds faces, publishes each face's bounding box (ROI).
- **`hri_emotion_recognizer`** — crops each ROI and classifies its emotion.

Splitting along these lines follows ROS's node-per-responsibility design and
lets you swap any stage (e.g. a better face detector) without touching the
others. All coupling is through topics.

---

## Data flow and topics

```
camera node
  -> /image_raw                       sensor_msgs/Image

hri_face_detect  (subscribes to the image)
  -> /humans/faces/tracked            list of active face IDs
  -> /humans/faces/<id>/roi           bounding box per face

hri_emotion_recognizer  (subscribes to ROIs + image)
  -> /humans/faces/<id>/expression    emotion + confidence per face
```

Topics follow the **ROS4HRI convention (REP-155)**. That is why face data lives
under `/humans/faces/<id>/...` rather than a project-specific name.

---

## How the FER+ emotion model works

The default model is `emotion-ferplus-8.onnx` from the ONNX Model Zoo — a
convolutional network trained on the FER+ annotations of the FER dataset.

Per face, the node does:

1. **Crop** the face region using the ROI from `hri_face_detect`.
2. **Preprocess** to the model's input spec:
   - convert to **grayscale** (1 channel),
   - resize to **64x64**,
   - reshape to a `[1, 1, 64, 64]` tensor.
3. **Infer** — forward pass through the ONNX model, producing a `[1, 8]` score
   array (one score per emotion class).
4. **Postprocess** — apply **softmax** to turn scores into probabilities. The
   highest-probability class is the emotion; its probability is the confidence.
5. **Publish** the result on `/humans/faces/<id>/expression`.

### Label order (fixed)

```
0 neutral   1 happiness   2 surprise   3 sadness
4 anger     5 disgust     6 fear       7 contempt
```

### Practical implications

- Input is only 64x64 grayscale, so **camera resolution does not improve emotion
  accuracy** — it only affects how well faces are detected upstream. Run face
  detection at a modest resolution (e.g. 720p) to save CPU.
- FER+ is lightweight and CPU-friendly (no GPU required), but its accuracy on
  ambiguous expressions is limited — expect frame-to-frame flicker. Downstream
  application logic should debounce and threshold on confidence.
- Poor lighting hurts both detection and classification. Fixing camera
  brightness is part of accuracy work, not cosmetic.

---

## Where your application fits

Consume `/humans/faces/<id>/expression` in a new node. The ROS4HRI Python API
(`HRIListener`) iterates tracked faces and exposes `face.expression`, handling
face tracking/ID bookkeeping for you. Map emotions to robot behaviour there
(e.g. stop on `surprise`), with a confidence threshold and temporal smoothing.
