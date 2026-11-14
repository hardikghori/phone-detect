# Live Object Detector

Open the link on any phone or tablet browser, tap a Start button, allow the camera.

- **Start kiosk (crying baby)**: the crying baby video loops full screen with the camera in the corner. Show a phone, book or toy for 1 second and its video plays, then a thank-you screen, then the baby again. Same rules as the offline kiosk in `pi/`. Videos come from `pi/videos/` (placeholders until the real ones are added).
- **Detector only**: live boxes and a spoken alert for phones, books and toys.

Detects phones, books and toys (teddy bears and most plush toys, balls) in real time with YOLO11s (COCO, fp16 ONNX, 480px) on onnxruntime-web, WebGPU with WASM fallback, fully on device.
Add ?fast to the link for YOLO11n (5 MB, faster, less accurate).

Add objects: edit OBJECTS in index.html with any of the 80 COCO class names.

## Offline kiosk (Jetson Orin or Raspberry Pi)

The `pi` folder runs the detector offline on a Jetson Orin or Raspberry Pi and plays a video when an object is shown.
Start here: [pi/SETUP_GUIDE.md](pi/SETUP_GUIDE.md). Jetson setup: `cd pi && bash setup_jetson.sh`.
