# How it works

A camera feeds a model. The model says what it sees. A small set of rules decides what to show on screen.

## Three layers

| Layer | What it holds | Where it lives |
|---|---|---|
| Data | Camera frames, the model file, the 4 videos, the settings, the play log | `models/`, `videos/`, `config.yaml`, `plays.csv` |
| Logic | Detector: one frame in, a list of boxes out (name, score, size). Filter: is this box one of our objects, sure enough, and big enough. State machine: baby, video, thank-you | `detector.py`, then `targets()` and the loop in `main()` in `kiosk.py` |
| Control | What a person can change or press without touching the logic: settings, keys, start flags, autostart, telling the video player what to play | `config.yaml`, keys `1 2 3 0 q`, `--aim`, `run.sh`, `kiosk.desktop`, `Player` in `kiosk.py` |

## One phone, start to finish
1. The camera gives a frame.
2. `Detector.detect()` runs YOLO11n on it and returns boxes, for example `cell phone, 0.80, 5% of the frame`.
3. `targets()` keeps a box only if its class is listed for an object in `config.yaml`, its score is at least `min_score` (0.35), and it covers at least `min_area` (2%) of the frame.
4. The loop in `main()` waits until the phone has been there for `steady_seconds` (1 s).
5. `Player.show()` tells mpv to play `videos/phone.mp4`. The play is written to `plays.csv`.
6. When the video ends, the thank-you screen shows for 3 seconds, then the baby video loops again.
7. Nothing new can play until the room has been empty for `empty_seconds` (2 s) and the baby has been back for `cooldown_seconds` (3 s).

## Why the detector and the kiosk are separate
`detector.py` only answers "what is in this frame". `kiosk.py` only answers "what should the screen do".
- The model can be swapped (a custom model, or GPU instead of CPU) without touching the rules.
- The rules can be tested with fake detections and a fake clock. `tests/check_sequences.py` does this for 14 situations with several people.
- `kiosk.py --aim` shows the detector's view with boxes, for setting up the camera.

## Why the web page has two buttons
Both buttons use the same camera and the same model (YOLO11s in the browser). They differ only in what is done with the detections.
- **Detector only**: draw boxes, show a banner, speak.
- **Start kiosk**: feed the same detections into the same baby, video, thank-you rules as the Orin kiosk.

One flag picks the path in `index.html`: `if (kiosk) kioskStep(dets); else announce(dets);`

## Tradeoffs
1. **Small model.** YOLO11n is fast on weak hardware and less accurate. It often calls a black phone a "remote", so the phone object accepts both names.
2. **Empty-room rule, not a timer.** A left-behind phone never replays. The cost: a visitor who puts an object in too quickly has to take it out and put it back.
3. **Browser or box.** The web version needs internet to load and runs on the visitor's device. The Orin version needs a one-time setup and then runs offline.
4. **Stock model, not custom.** It knows 80 everyday objects, learned mostly from side views. The kiosk camera looks down, so scores are lower. The fix, if needed, is a small custom model trained on about 100 photos of each real object.
