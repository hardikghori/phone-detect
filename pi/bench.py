"""Day-1 check on the Raspberry Pi: is it fast enough? Pass = 2 fps or more, RAM under 700 MB.

Usage: python bench.py
"""
import sys
import time
from pathlib import Path

import cv2

from detector import Detector

HERE = Path(__file__).resolve().parent
img = cv2.imread(str(HERE / "tests" / "phone.jpg"))


def temp_c() -> str:
    try:
        return f"{int(Path('/sys/class/thermal/thermal_zone0/temp').read_text()) / 1000:.0f}C"
    except OSError:
        return "n/a"


def rss_mb() -> float:
    try:
        import resource  # Linux only
    except ImportError:
        return float("nan")
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


for size in (320, 416):
    det = Detector(HERE / "models" / f"yolo11n_{size}", size)
    det.detect(img)  # warm up
    runs = 20
    t0 = time.perf_counter()
    for _ in range(runs):
        dets = det.detect(img)
    ms = (time.perf_counter() - t0) * 1000 / runs
    top = ", ".join(f"{d['name']} {d['score']:.2f}" for d in dets[:2])
    verdict = "PASS" if 1000 / ms >= 2 else "TOO SLOW"
    print(f"yolo11n {size}px: {ms:.0f} ms/frame = {1000 / ms:.1f} fps | peak RAM {rss_mb():.0f} MB | "
          f"temp {temp_c()} | sees {top} | {verdict}")
