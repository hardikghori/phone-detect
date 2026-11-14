"""Drive pi/kiosk.py main() with a fake clock, camera, detector and mpv player."""
import json, sys, types
from pathlib import Path
PI = Path(r"C:\Projects\phone-detect\pi"); sys.path.insert(0, str(PI))
import kiosk

DUR = {"phone.mp4": 6, "book.mp4": 6, "toy.mp4": 6}

def run(sc):
    T = [0.0]
    dt = sc.get("frame_dt", 0.1); miss = sc.get("miss_every"); frame_no = [0]
    shows, plays = [], []
    clock = types.SimpleNamespace(monotonic=lambda: T[0], sleep=lambda s: T.__setitem__(0, T[0] + s))
    kiosk.time = clock
    class Cam:
        def __init__(self, *a, **k): pass
        def read(self):
            T[0] += dt; frame_no[0] += 1; return frame_no[0]
    class Det:
        def __init__(self, *a, **k): pass
        def detect(self, f, min_score):
            if miss and f % miss == 0: return []
            return [{"name": n, "score": s, "area": a} for n, t0, t1, s, a in sc["objs"]
                    if t0 <= T[0] < t1 and s >= min_score]
    class Events:
        def __init__(self): self.q = []
        def empty(self): return not any(t <= T[0] for t, _ in self.q)
        def get(self):
            i = min((i for i, (t, _) in enumerate(self.q) if t <= T[0]), key=lambda i: self.q[i][0])
            return self.q.pop(i)[1]
    class Player:
        def __init__(self, *a):
            self.events = Events(); self.pending = None
            for t, k in sc.get("keys", []):
                self.events.q.append((t, {"event": "client-message", "args": [k]}))
        def show(self, path, loop=False, image_s=3):
            shows.append((round(T[0], 2), Path(path).name))
            if self.pending in self.events.q: self.events.q.remove(self.pending)
            self.pending = None
            if not loop:
                d = image_s if Path(path).suffix == ".png" else DUR[Path(path).name]
                self.pending = (T[0] + d, {"event": "end-file", "reason": "eof"})
                self.events.q.append(self.pending)
        def close(self): pass
    kiosk.Camera, kiosk.Detector, kiosk.Player = Cam, Det, Player
    kiosk.log_play = lambda n, s: plays.append([n, round(T[0], 2)])
    kiosk.keys_file = lambda cfg: None
    sys.argv = ["kiosk", "--run-for", "45"]
    import io, contextlib
    with contextlib.redirect_stdout(io.StringIO()): kiosk.main()
    return plays, shows

if __name__ == "__main__":
    out = {sc["id"]: dict(zip(["plays", "shows"], run(sc))) for sc in json.load(open(sys.argv[1]))}
    json.dump(out, sys.stdout)
