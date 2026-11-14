// Run the kiosk block of index.html with a fake clock, camera size, detections and <video>.
import fs from "fs";
const html = fs.readFileSync(new URL("../../index.html", import.meta.url), "utf8");
const objBlock = html.slice(html.indexOf("const OBJECTS = {"), html.indexOf("const MIN_SCORE"));
const kBlock = html.slice(html.indexOf("const KIOSK = {"), html.indexOf("async function keepAwake"));
const DUR = { "phone.mp4": 6, "book.mp4": 6, "toy.mp4": 6 };
const scenarios = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const out = {};
for (const sc of scenarios) {
  let T = 0; const timers = [], plays = [], shows = [];
  const mkEl = () => ({ classList: { add() {}, remove() {}, contains() { return false; } }, play() { return Promise.resolve(); }, pause() {} });
  const screenEl = mkEl(), thanksEl = mkEl();
  let src = "";
  Object.defineProperty(screenEl, "src", { get: () => src, set: v => {
    src = v; const name = v.split("/").pop(); shows.push([+(T / 1000).toFixed(2), name]);
    timers.splice(0, timers.length, ...timers.filter(t => t.kind !== "end"));
    if (!screenEl.loop) { if (name !== "baby.mp4") plays.push([name.replace(".mp4", ""), +(T / 1000).toFixed(2)]);
      timers.push({ kind: "end", at: T + DUR[name] * 1000, fn: () => screenEl.onended() }); } } });
  const document = { getElementById: id => id === "screen" ? screenEl : thanksEl };
  const Date = { now: () => T };
  const setTimeout = (fn, ms) => timers.push({ kind: "timeout", at: T + ms, fn: () => { shows.push([+(T/1000).toFixed(2), "thanks-done"]); fn(); } });
  const video = { videoWidth: 1000, videoHeight: 1000 };
  const body = `${objBlock}\nlet soundOn = true;\n${kBlock.replace("const screenEl = document", "const screenEl = document")}
    return { showBaby, kioskStep, get state() { return kstate; } };`;
  const k = new Function("document", "Date", "setTimeout", "video", body)(document, Date, setTimeout, video);
  k.showBaby();
  const dt = (sc.frame_dt || 0.1) * 1000; let f = 0;
  for (const [t, key] of sc.keys || []) timers.push({ kind: "key", at: t * 1000, fn: () => { if (key === "skip" && k.state === "video") screenEl.onended(); } });
  while (T < 45000) {
    T += dt; f++;
    for (const t of timers.filter(t => t.at <= T).sort((a, b) => a.at - b.at)) { timers.splice(timers.indexOf(t), 1); t.fn(); }
    const dets = (sc.miss_every && f % sc.miss_every === 0) ? [] : sc.objs
      .filter(([n, t0, t1, s]) => t0 * 1000 <= T && T < t1 * 1000 && s >= 0.25)
      .map(([n, t0, t1, s, a]) => { const OBJ = new Function(`${objBlock}; const T = {}; for (const [key,o] of Object.entries(OBJECTS)) for (const c of o.classes) T[c]=key; return T;`)();
        return { name: n, score: s, target: OBJ[n], box: { width: Math.sqrt(a) * 1000, height: Math.sqrt(a) * 1000 } }; });
    k.kioskStep(dets);
  }
  out[sc.id] = { plays: plays.map(([n, t]) => [n === "phone" || n === "book" || n === "toy" ? n : n, t]), shows };
}
console.log(JSON.stringify(out));
