"""YOLO11 object detector on bare ncnn (no torch), small enough for a Raspberry Pi 3.

Same decode and NMS as the browser version (../index.html: detect, nms, iou).
"""
from pathlib import Path

import cv2
import ncnn
import numpy as np

COCO = ["person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat",
        "traffic light", "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat", "dog",
        "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella",
        "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball", "kite",
        "baseball bat", "baseball glove", "skateboard", "surfboard", "tennis racket", "bottle",
        "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple", "sandwich",
        "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair", "couch",
        "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse", "remote",
        "keyboard", "cell phone", "microwave", "oven", "toaster", "sink", "refrigerator", "book",
        "clock", "vase", "scissors", "teddy bear", "hair drier", "toothbrush"]


class Detector:
    def __init__(self, model_dir: str | Path, size: int, threads: int = 4):
        model_dir = Path(model_dir)
        self.size = size
        self.net = ncnn.Net()
        self.net.opt.use_vulkan_compute = False
        self.net.opt.num_threads = threads
        self.net.load_param(str(model_dir / "model.ncnn.param"))
        self.net.load_model(str(model_dir / "model.ncnn.bin"))

    def detect(self, frame_bgr: np.ndarray, min_score: float = 0.25) -> list[dict]:
        """Boxes in frame pixels: [{name, score, x1, y1, x2, y2, area}] where area is a frame fraction."""
        h, w = frame_bgr.shape[:2]
        r = self.size / max(w, h)
        nw, nh = round(w * r), round(h * r)
        canvas = np.full((self.size, self.size, 3), 114, np.uint8)
        canvas[:nh, :nw] = cv2.resize(frame_bgr, (nw, nh), interpolation=cv2.INTER_LINEAR)
        rgb = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)
        blob = np.ascontiguousarray(rgb.transpose(2, 0, 1), dtype=np.float32) / 255.0

        ex = self.net.create_extractor()
        ex.input("in0", ncnn.Mat(blob))
        _, out = ex.extract("out0")
        out = np.array(out)  # (84, A): cx cy w h, then 80 class scores

        scores = out[4:]
        cls = scores.argmax(0)
        best = scores[cls, np.arange(scores.shape[1])]
        keep = best >= min_score
        if not keep.any():
            return []
        cx, cy, bw, bh = out[:4, keep]
        boxes = np.stack([cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2], 1) / r
        dets = [{"name": COCO[c], "score": float(s), "x1": float(b[0]), "y1": float(b[1]),
                 "x2": float(b[2]), "y2": float(b[3]),
                 "area": float((b[2] - b[0]) * (b[3] - b[1]) / (w * h))}
                for c, s, b in zip(cls[keep], best[keep], boxes)]
        return nms(dets)[:20]


def iou(a: dict, b: dict) -> float:
    iw = min(a["x2"], b["x2"]) - max(a["x1"], b["x1"])
    ih = min(a["y2"], b["y2"]) - max(a["y1"], b["y1"])
    if iw <= 0 or ih <= 0:
        return 0.0
    inter = iw * ih
    area = lambda d: (d["x2"] - d["x1"]) * (d["y2"] - d["y1"])
    return inter / (area(a) + area(b) - inter)


def nms(dets: list[dict], thr: float = 0.45) -> list[dict]:
    """Per-class non-max suppression."""
    keep: list[dict] = []
    for d in sorted(dets, key=lambda d: -d["score"]):
        if not any(k["name"] == d["name"] and iou(k, d) > thr for k in keep):
            keep.append(d)
    return keep
