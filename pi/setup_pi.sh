#!/usr/bin/env bash
# One-time setup on Raspberry Pi OS 64-bit (Bookworm, with desktop). Run: bash setup_pi.sh
set -e
cd "$(dirname "$0")"

if [ "$(uname -m)" != "aarch64" ]; then
  echo "This needs the 64-bit Raspberry Pi OS (aarch64). Reflash the SD card with the 64-bit image."
  exit 1
fi

sudo apt update
sudo apt install -y mpv ffmpeg git python3-opencv python3-numpy python3-yaml python3-pil \
  python3-picamera2 python3-venv fonts-noto-core

# ncnn is the only pip package; everything else comes from apt (lighter on a 1 GB Pi 3).
python3 -m venv --system-site-packages .venv
.venv/bin/pip install ncnn==1.0.20261020

# Start the kiosk when the desktop logs in, and keep the screen from blanking.
chmod +x run.sh
mkdir -p ~/.config/autostart
sed "s#__DIR__#$PWD#" kiosk.desktop > ~/.config/autostart/annakut-kiosk.desktop
sudo raspi-config nonint do_blanking 1 || true

echo
echo "Setup done. Next:"
echo "  1. Speed check:  .venv/bin/python bench.py                  (needs 2 fps or more)"
echo "  2. Your video:   bash add_video.sh /path/to/video.mp4 phone"
echo "  3. Try it:       ./run.sh                                     (q in the camera window quits)"
echo "  4. Reboot: the kiosk starts by itself."
