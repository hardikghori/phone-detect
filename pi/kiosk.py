"""Annakut kiosk: camera watches, a shown object plays its video full screen, then back to the camera.

Keys in the camera window: p = play the first object's video now, q = quit.
While a video plays, mpv's own q skips it.

Testing without a camera: python kiosk.py --source tests/phone.jpg --run-for 20
"""
import argparse
import csv
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import yaml

from detector import Detector

HERE = Path(__file__).resolve().parent
WINDOW = "Annakut"


def load_config() -> dict:
    cfg = yaml.safe_load((HERE / "config.yaml").read_text(encoding="utf-8"))
    objects = {}
    for name, obj in cfg["objects"].items():
        video = HERE / obj["video"]
        if video.exists():
            objects[name] = {**obj, "video": video}
        else:
            print(f"[kiosk] skipping '{name}': {video} not found")
    if not objects:
        sys.exit("[kiosk] no object has a video file; add one to videos/")
    cfg["objects"] = objects
    return cfg


class Camera:
    """Picamera2 for a Pi camera module, OpenCV for a USB webcam."""

    def __init__(self, kind: str, index: int, source: str | None = None):
        self.picam = None
        self.still = None
        if source:  # a photo stands in for the camera
            self.still = cv2.imread(source)
            if self.still is None:
                sys.exit(f"[kiosk] cannot read {source}")
            print(f"[kiosk] using test photo {source}")
            return
        if kind in ("auto", "picamera"):
            try:
                from picamera2 import Picamera2
                self.picam = Picamera2()
                self.picam.configure(self.picam.create_preview_configuration(
                    main={"size": (640, 480), "format": "RGB888"}))  # RGB888 arrays come out in BGR order
                self.picam.start()
                print("[kiosk] using Pi camera")
                return
            except Exception as e:
                self.picam = None
                if kind == "picamera":
                    raise
                print(f"[kiosk] no Pi camera ({e}); trying USB webcam")
        self.cap = cv2.VideoCapture(index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        if not self.cap.isOpened():
            sys.exit("[kiosk] no camera found")
        print("[kiosk] using USB webcam")

    def read(self) -> np.ndarray | None:
        if self.still is not None:
            time.sleep(0.3)  # about Pi 3 speed
            return self.still.copy()
        if self.picam is not None:
            return self.picam.capture_array()
        ok, frame = self.cap.read()
        return frame if ok else None

    def flush(self) -> None:
        """Drop frames buffered while a video played, so detection sees the present."""
        if self.picam is None and self.still is None:
            for _ in range(5):
                self.cap.grab()


def play(video: Path) -> None:
    """Play full screen and block until the video ends."""
    if shutil.which("mpv"):
        subprocess.run(["mpv", "--fs", "--really-quiet", "--no-osc", "--hwdec=auto", str(video)])
    elif shutil.which("ffplay"):
        subprocess.run(["ffplay", "-fs", "-autoexit", "-loglevel", "quiet", str(video)])
    else:  # last resort: picture only, no sound
        cap = cv2.VideoCapture(str(video))
        delay = int(1000 / (cap.get(cv2.CAP_PROP_FPS) or 25))
        while True:
            ok, frame = cap.read()
            if not ok or cv2.waitKey(delay) & 0xFF == ord("q"):
                break
            cv2.imshow(WINDOW, frame)
        cap.release()


def gujarati_font():
    """A font that can draw Gujarati (OpenCV's own fonts cannot), or None."""
    try:
        from PIL import ImageFont
    except ImportError:
        return None
    for path in ["/usr/share/fonts/truetype/noto/NotoSansGujarati-Regular.ttf",
                 "/usr/share/fonts/truetype/noto/NotoSansGujarati-Bold.ttf",
                 "C:/Windows/Fonts/Nirmala.ttc", "C:/Windows/Fonts/Nirmala.ttf"]:
        if Path(path).exists():
            return ImageFont.truetype(path, 30)
    return None


def draw(frame: np.ndarray, dets: list[dict], cfg: dict, font, status: str) -> np.ndarray:
    watched = {c for o in cfg["objects"].values() for c in o["classes"]}
    for d in dets:
        if d["name"] in watched:
            cv2.rectangle(frame, (int(d["x1"]), int(d["y1"])), (int(d["x2"]), int(d["y2"])), (0, 200, 0), 3)
    h, w = frame.shape[:2]
    cv2.rectangle(frame, (0, 0), (w, 90 if font else 50), (0, 0, 0), -1)
    cv2.putText(frame, cfg["prompt_en"], (12, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
    if font:
        from PIL import Image, ImageDraw
        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        ImageDraw.Draw(img).text((12, 46), cfg["prompt_gu"], font=font, fill=(255, 255, 255))
        frame = cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)
    cv2.putText(frame, status, (12, h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    return frame


def log_play(name: str, score: float) -> None:
    path = HERE / "plays.csv"
    new = not path.exists()
    with path.open("a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["time", "object", "score"])
        w.writerow([datetime.now().isoformat(timespec="seconds"), name, f"{score:.2f}"])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", help="photo to use instead of the camera (testing)")
    ap.add_argument("--run-for", type=float, help="quit after this many seconds (testing)")
    args = ap.parse_args()

    cfg = load_config()
    det = Detector(HERE / "models" / cfg["model"], cfg["size"])
    cam = Camera(cfg["camera"], cfg["camera_index"], args.source)
    font = gujarati_font()
    started = time.monotonic()
    cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
    if cfg["fullscreen"] and not args.source:
        cv2.setWindowProperty(WINDOW, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    first_seen: dict[str, float] = {}   # when each object started being in view
    last_seen: dict[str, float] = {}
    last_played: dict[str, float] = {}
    lockout_until = 0.0

    while True:
        frame = cam.read()
        if frame is None:
            time.sleep(0.1)
            continue
        t0 = time.monotonic()
        dets = det.detect(frame, cfg["min_score"])
        now = time.monotonic()

        due = None
        for name, obj in cfg["objects"].items():   # config order is priority order
            hits = [d for d in dets if d["name"] in obj["classes"] and d["area"] >= obj["min_area"]]
            if hits:
                if now - last_seen.get(name, 0) > 0.6:   # allow one missed frame at Pi 3 speed
                    first_seen[name] = now
                last_seen[name] = now
                steady = now - first_seen[name] >= cfg["steady_seconds"]
                cooled = now - last_played.get(name, -1e9) >= obj["cooldown_s"]
                if due is None and steady and cooled and now >= lockout_until:
                    due = (name, max(d["score"] for d in hits))

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q") or (args.run_for and now - started > args.run_for):
            break
        if key == ord("p"):
            due = (next(iter(cfg["objects"])), 1.0)

        if due:
            name, score = due
            print(f"[kiosk] {name} detected ({score:.2f}), playing video")
            log_play(name, score)
            play(cfg["objects"][name]["video"])
            last_played[name] = time.monotonic()
            lockout_until = time.monotonic() + cfg["lockout_after_video_s"]
            first_seen.clear()
            last_seen.clear()
            cam.flush()
            continue

        seen = ", ".join(f"{d['name']} {d['score']:.0%}" for d in dets[:3]) or "nothing"
        status = f"{(now - t0) * 1000:.0f} ms | sees: {seen}"
        cv2.imshow(WINDOW, draw(frame, dets, cfg, font, status))

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
