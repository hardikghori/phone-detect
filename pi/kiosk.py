"""Annakut "crying baby" kiosk.

The screen loops the crying baby video. A camera looks down into a small doll-house room.
When someone puts one object in the room (phone, book, toy), that object's video plays,
then a thank-you screen, then the crying baby again. The next object only counts after
the room has been empty for a moment, so a left-behind object never replays.

Keys (mpv window): 1, 2, 3 play an object's video, 0 skips the current video, q quits.

Aim the camera:   python kiosk.py --aim
Test, no camera:  python kiosk.py --source tests/sequence.mp4 --run-for 60
"""
import argparse
import csv
import json
import os
import queue
import shutil
import socket
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import yaml

from detector import Detector

HERE = Path(__file__).resolve().parent
WINDOW = "Annakut"
VIDEO_EXT = {".mp4", ".mov", ".mkv", ".avi", ".webm"}


def load_config(video_dir: Path | None) -> dict:
    cfg = yaml.safe_load((HERE / "config.yaml").read_text(encoding="utf-8"))
    base = video_dir or HERE

    def where(p: str) -> Path:
        return base / Path(p).name if video_dir else HERE / p

    cfg["idle_video"] = where(cfg["idle_video"])
    if not cfg["idle_video"].exists():
        sys.exit(f"[kiosk] missing the crying baby video: {cfg['idle_video']}")
    thanks = where(cfg["thanks"]) if cfg.get("thanks") else None
    cfg["thanks"] = thanks if thanks and thanks.exists() else None
    objects = {}
    for name, obj in cfg["objects"].items():
        video = where(obj["video"])
        if video.exists():
            objects[name] = {**obj, "video": video}
        else:
            print(f"[kiosk] skipping '{name}': {video} not found")
    if not objects:
        sys.exit("[kiosk] no object has a video file; add one to videos/")
    cfg["objects"] = objects
    return cfg


class Camera:
    """Pi camera (Picamera2), Jetson CSI camera (GStreamer), USB webcam, or a test photo/video."""

    def __init__(self, kind: str, index: int, source: str | None = None):
        self.picam = self.still = self.cap = None
        self.paced = False
        if source:
            if Path(source).suffix.lower() in VIDEO_EXT:  # a recorded clip, looped in real time
                self.cap = cv2.VideoCapture(source)
                self.paced = True
                self.frame_s = 1 / (self.cap.get(cv2.CAP_PROP_FPS) or 10)
                self.next_t = time.monotonic()
            else:
                self.still = cv2.imread(source)
                if self.still is None:
                    sys.exit(f"[kiosk] cannot read {source}")
            print(f"[kiosk] using test source {source}")
            return
        if kind in ("auto", "picamera") and self._try_picamera(kind):
            return
        if kind in ("auto", "csi") and Path("/etc/nv_tegra_release").exists() and self._try_csi(kind):
            return
        self.cap = cv2.VideoCapture(index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        if not self.cap.isOpened():
            sys.exit("[kiosk] no camera found")
        print("[kiosk] using USB webcam")

    def _try_picamera(self, kind: str) -> bool:
        try:
            from picamera2 import Picamera2
            self.picam = Picamera2()
            self.picam.configure(self.picam.create_preview_configuration(
                main={"size": (640, 480), "format": "RGB888"}))  # RGB888 arrays come out in BGR order
            self.picam.start()
            print("[kiosk] using Pi camera")
            return True
        except Exception as e:
            self.picam = None
            if kind == "picamera":
                raise
            print(f"[kiosk] no Pi camera ({e})")
            return False

    def _try_csi(self, kind: str) -> bool:
        pipeline = ("nvarguscamerasrc ! video/x-raw(memory:NVMM),width=1280,height=720,framerate=30/1 ! "
                    "nvvidconv ! video/x-raw,width=640,height=360,format=BGRx ! videoconvert ! "
                    "video/x-raw,format=BGR ! appsink drop=true max-buffers=1")
        cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
        if cap.isOpened() and cap.read()[0]:
            self.cap = cap
            print("[kiosk] using Jetson CSI camera")
            return True
        if kind == "csi":
            sys.exit("[kiosk] CSI camera did not open (check the ribbon cable, then reboot)")
        print("[kiosk] no CSI camera, trying USB webcam")
        return False

    def read(self) -> np.ndarray | None:
        if self.still is not None:
            time.sleep(0.1)
            return self.still.copy()
        if self.picam is not None:
            return self.picam.capture_array()
        if self.paced:
            self.next_t += self.frame_s
            time.sleep(max(0.0, self.next_t - time.monotonic()))
            ok, frame = self.cap.read()
            if not ok:  # loop the clip
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ok, frame = self.cap.read()
            return frame if ok else None
        ok, frame = self.cap.read()
        return frame if ok else None


class Player:
    """One full-screen mpv window driven over its JSON IPC, so switching videos never shows the desktop.

    Two connections: one only reads events (on a thread), the other sends commands and reads each reply.
    Windows named pipes cannot read and write on one handle from two threads, so this works on both.
    """

    def __init__(self, keys_conf: Path):
        mpv = shutil.which("mpv")
        if not mpv:
            sys.exit("[kiosk] mpv is not installed (sudo apt install mpv)")
        self.addr = r"\\.\pipe\annakut-mpv" if os.name == "nt" else "/tmp/annakut-mpv.sock"
        self.proc = subprocess.Popen([
            mpv, "--fs", "--idle=yes", "--force-window=yes", "--keep-open=no", "--no-osc",
            "--osd-level=0", "--really-quiet", "--hwdec=auto", "--no-input-default-bindings",
            "--cursor-autohide=always", "--background-color=#000000",
            f"--input-conf={keys_conf}", f"--input-ipc-server={self.addr}"])
        self.events: queue.Queue = queue.Queue()
        self.cmd = self._connect()
        threading.Thread(target=self._read_events, args=(self._connect(),), daemon=True).start()
        self.send("disable_event", "all")

    def _connect(self):
        for _ in range(100):
            try:
                if os.name == "nt":
                    return open(self.addr, "r+b", buffering=0)
                s = socket.socket(socket.AF_UNIX)
                s.connect(self.addr)
                return s.makefile("rwb", buffering=0)
            except OSError:
                time.sleep(0.1)
        sys.exit("[kiosk] could not connect to mpv")

    def _read_events(self, conn) -> None:
        buf = b""
        while True:
            chunk = conn.read(4096) if os.name != "nt" else conn.read(1)
            if not chunk:
                self.events.put({"event": "mpv-closed"})
                return
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                msg = json.loads(line)
                if "event" in msg:
                    self.events.put(msg)

    def send(self, *command) -> None:
        self.cmd.write((json.dumps({"command": list(command)}) + "\n").encode())
        line = b""
        while not line.endswith(b"\n"):  # read the reply so the pipe never fills up
            ch = self.cmd.read(1)
            if not ch:
                return
            line += ch

    def show(self, path: Path, loop: bool = False, image_s: float = 3) -> None:
        self.send("set_property", "loop-file", "inf" if loop else "no")
        self.send("set_property", "image-display-duration", image_s)
        self.send("loadfile", str(path), "replace")

    def close(self) -> None:
        if self.proc.poll() is None:
            self.proc.terminate()


def keys_file(cfg: dict) -> Path:
    lines = ["0 script-message skip", "q quit"]
    lines += [f"{i} script-message play {name}" for i, name in enumerate(cfg["objects"], 1)]
    path = HERE / ".mpv-keys.conf"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def targets(dets: list[dict], cfg: dict) -> dict[str, float]:
    """Best score per configured object in this frame."""
    found: dict[str, float] = {}
    for name, obj in cfg["objects"].items():
        hits = [d["score"] for d in dets if d["name"] in obj["classes"] and d["area"] >= obj["min_area"]]
        if hits:
            found[name] = max(hits)
    return found


def log_play(name: str, score: float) -> None:
    path = HERE / "plays.csv"
    new = not path.exists()
    with path.open("a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["time", "object", "score"])
        w.writerow([datetime.now().isoformat(timespec="seconds"), name, f"{score:.2f}"])


def aim(cam: Camera, det: Detector, cfg: dict) -> None:
    """Camera picture with boxes, to point the camera at the room. q quits."""
    while True:
        frame = cam.read()
        if frame is None:
            continue
        t0 = time.monotonic()
        dets = det.detect(frame, cfg["min_score"])
        ms = (time.monotonic() - t0) * 1000
        for d in dets:
            cv2.rectangle(frame, (int(d["x1"]), int(d["y1"])), (int(d["x2"]), int(d["y2"])), (0, 200, 0), 2)
            cv2.putText(frame, f"{d['name']} {d['score']:.0%} area {d['area']:.0%}",
                        (int(d["x1"]), max(15, int(d["y1"]) - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        found = ", ".join(targets(dets, cfg)) or "no object"
        cv2.putText(frame, f"{ms:.0f} ms | counts as: {found}", (10, frame.shape[0] - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.imshow(WINDOW, frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    cv2.destroyAllWindows()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--aim", action="store_true", help="show the camera with boxes (to set it up)")
    ap.add_argument("--source", help="photo or video clip to use instead of the camera (testing)")
    ap.add_argument("--videos", type=Path, help="folder with the videos, instead of the paths in config.yaml")
    ap.add_argument("--run-for", type=float, help="quit after this many seconds (testing)")
    args = ap.parse_args()

    cfg = load_config(args.videos)
    det = Detector(HERE / "models" / cfg["model"], cfg["size"], cfg.get("threads", 4))
    cam = Camera(cfg["camera"], cfg["camera_index"], args.source)
    if args.aim:
        return aim(cam, det, cfg)

    player = Player(keys_file(cfg))
    player.show(cfg["idle_video"], loop=True)
    print("[kiosk] crying baby on screen, waiting for an object")

    state = "baby"                 # baby | video | thanks
    need_empty = True              # the room must be empty once before the first object counts
    first_seen: dict[str, float] = {}
    last_seen: dict[str, float] = {}
    last_target = time.monotonic()  # last time any object was in the room
    started = time.monotonic()
    baby_since = started           # when the crying baby came back on screen (for the cooldown)
    prev_frame, frame_s = started, 0.1  # average seconds per frame, so slow devices still count "steady"

    def start(name: str, score: float) -> None:
        nonlocal state, need_empty
        print(f"[kiosk] {name} placed ({score:.2f}), playing its video")
        log_play(name, score)
        player.show(cfg["objects"][name]["video"])
        state, need_empty = "video", True
        first_seen.clear()

    def finished() -> None:
        nonlocal state, baby_since
        if state == "video" and cfg["thanks"]:
            player.show(cfg["thanks"], image_s=cfg.get("thanks_seconds", 3))
            state = "thanks"
        else:
            player.show(cfg["idle_video"], loop=True)
            state, baby_since = "baby", time.monotonic()
            print("[kiosk] crying baby on screen, waiting for an object")

    try:
        while True:
            while not player.events.empty():
                ev = player.events.get()
                kind = ev.get("event")
                if kind == "mpv-closed":
                    return
                if kind == "end-file" and ev.get("reason") == "eof" and state != "baby":
                    finished()
                elif kind == "client-message":
                    msg = ev.get("args", [])
                    if msg[:1] == ["skip"] and state != "baby":
                        finished()
                    elif msg[:1] == ["play"] and len(msg) > 1 and msg[1] in cfg["objects"]:
                        start(msg[1], 1.0)

            frame = cam.read()
            if frame is None:
                time.sleep(0.05)
                continue
            found = targets(det.detect(frame, cfg["min_score"]), cfg)
            now = time.monotonic()
            frame_s = 0.8 * frame_s + 0.2 * (now - prev_frame)
            prev_frame = now
            # A missed frame or two must not restart the steady timer. On a slow device (Pi 3, about
            # 0.5 s per frame) a fixed 0.5 s gap reset it on every frame and nothing ever played.
            gap_s = max(0.5, 2.5 * frame_s)
            if found:
                last_target = now
            elif need_empty and now - last_target >= cfg["empty_seconds"]:
                need_empty = False
                print("[kiosk] room is empty, ready for the next person")

            for name in found:
                if now - last_seen.get(name, 0) > gap_s or name not in first_seen:
                    first_seen[name] = now
                last_seen[name] = now

            cooled = now - baby_since >= cfg.get("cooldown_seconds", 0)
            if state == "baby" and not need_empty and cooled:
                for name in cfg["objects"]:  # config order is priority order
                    if name in found and now - first_seen[name] >= cfg["steady_seconds"]:
                        start(name, found[name])
                        break

            if args.run_for and now - started > args.run_for:
                return
    except KeyboardInterrupt:
        pass
    finally:
        player.close()


if __name__ == "__main__":
    main()
