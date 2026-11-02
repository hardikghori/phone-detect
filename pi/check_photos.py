"""Run the detector on photo files and print what it sees. Usage: python check_photos.py img1.jpg img2.jpg"""
import sys
import time

import cv2

from detector import Detector

size = 320
for arg in sys.argv[1:]:
    if arg.startswith("--size="):
        size = int(arg.split("=")[1])
det = Detector(f"models/yolo11n_{size}", size)
for path in [a for a in sys.argv[1:] if not a.startswith("--")]:
    img = cv2.imread(path)
    t0 = time.perf_counter()
    dets = det.detect(img)
    ms = (time.perf_counter() - t0) * 1000
    seen = ", ".join(f"{d['name']} {d['score']:.2f} (area {d['area']:.2f})" for d in dets[:5]) or "nothing"
    print(f"{path}: {ms:.0f} ms | {seen}")
