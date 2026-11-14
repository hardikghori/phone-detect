# Annakut "crying baby" kiosk (Jetson Orin or Raspberry Pi, fully offline)

The screen loops a crying baby video. A camera looks down into a small doll-house room. A visitor puts one object in the room (phone, book or toy) and that object's 15 to 20 second video plays, then a thank-you screen, then the crying baby again. No internet, nothing recorded.

**Setting it up for the first time? Follow [SETUP_GUIDE.md](SETUP_GUIDE.md).**

## How it decides
- The object must sit in the room for 1 second (`steady_seconds`) with enough model confidence (`min_score`).
- After a video, the room must be empty for 2 seconds (`empty_seconds`) before the next object counts. A left-behind object never replays.
- After the baby comes back, the camera is ignored for 3 seconds (`cooldown_seconds`).
- `videos/` ships with labeled placeholder videos. Swap in the real ones with `add_video.sh`.
- If two objects are in the room, the one listed first in `config.yaml` wins.
- Every play is logged in `plays.csv`.

## Hardware
- **Jetson Orin** (JetPack 6): `bash setup_jetson.sh`. The original Jetson Nano (JetPack 4, Python 3.6) is too old for this code.
- Raspberry Pi (64-bit Bookworm): `bash setup_pi.sh`. Slower but works.
- Camera: USB webcam, Jetson ribbon camera (GStreamer), or Pi camera. `camera: auto` finds it.
- Video plays in one full-screen mpv window, controlled over mpv's IPC, so switching videos never shows the desktop.

## Files
- `kiosk.py`: the kiosk. `--aim` shows the camera with boxes, for setup.
- `config.yaml`: videos, objects, timings.
- `detector.py`: YOLO11n (Ultralytics, COCO) exported to NCNN, run with the bare `ncnn` package. Same code on Jetson, Pi and a laptop.
- `bench.py`: speed check. `check_photos.py`: what the model sees in photos.
- `add_video.sh`: converts a video to 720p into `videos/`.

## Notes
- The camera looks down from the ceiling. COCO models learned mostly from side views, so check every real object with `--aim` before the event. If one is weak, the fix is a small custom model trained on about 100 photos of each real object in the room.
- YOLO11n often calls a black phone a "remote", so the phone object accepts both.

## Testing without a camera
`python kiosk.py --source clip.mp4 --videos some/folder --run-for 45` uses a recorded clip as the camera and the videos in that folder.
