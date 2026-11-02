# Annakut kiosk (Raspberry Pi, fully offline)

A camera watches a small table. When someone holds a phone up to it, the phone advice video plays full screen. When the video ends, the camera comes back on and waits for the next object. No internet, nothing recorded.

**Setting it up for the first time? Follow [SETUP_GUIDE.md](SETUP_GUIDE.md).**

## What you need
- Raspberry Pi 3 (Pi 4 or 5 is faster), heatsink, 2.5 A power supply
- microSD card, 16 GB or more, with **Raspberry Pi OS 64-bit (Bookworm, with desktop)**. Flash it with Raspberry Pi Imager.
- Pi Camera Module or any USB webcam
- TV or monitor over HDMI, with sound (HDMI audio or speakers on the 3.5 mm jack)

## Setup (once)
1. Copy this `pi` folder to the Pi, for example to `/home/pi/kiosk`.
2. On the Pi: `cd ~/kiosk && bash setup_pi.sh`
3. Add your video (converted to 720p on the Pi): `bash add_video.sh /path/to/video.mp4 phone`
4. Speed check: `.venv/bin/python bench.py`. You need 2 fps or more at 320px.
5. Reboot. The kiosk starts by itself.

## Using it
- Point the camera at a table with a sign: "Show your phone here".
- The phone must be fairly close (3% of the picture or more) and held still for about 1 second. Phones far away in the crowd are ignored on purpose.
- After a video, the same object will not replay for 60 seconds.
- Keys (plug in a keyboard): `p` plays the phone video now, `q` quits. While a video plays, `q` skips it.
- Every play is logged in `plays.csv`.

## Add another object
1. Put its video in `videos/`, e.g. `videos/book.mp4`.
2. Add a block in `config.yaml` (a book block is already there and turns on once `videos/book.mp4` exists). Any of the 80 COCO objects works: cup, bottle, laptop, clock, and so on (full list in `detector.py`).
3. Objects not in that list (a mala, prasad) need a small custom model trained on about 150 photos each.

## Settings
All in `config.yaml`: model size (320 or 416), how close an object must be (`min_area`), how long it must be held (`steady_seconds`), cooldown, and the on-screen prompt in English and Gujarati.

## Testing without a camera
`python kiosk.py --source tests/phone_black.jpg --run-for 15` plays the video once, then the cooldown holds.
`python check_photos.py tests/*.jpg` prints what the model sees.

## Notes
- Model: YOLO11n (Ultralytics, COCO), exported to NCNN. Runs with the bare `ncnn` package, no PyTorch, to fit in the Pi 3's 1 GB.
- YOLO11n often calls a black phone a "remote", so the phone object accepts both.
- Test photos in `tests/` are from Wikimedia Commons (see `tests/CREDITS.md`).
