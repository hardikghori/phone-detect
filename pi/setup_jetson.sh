#!/usr/bin/env bash
# One-time setup on a Jetson Orin (JetPack 6, Ubuntu 22.04 desktop). Run: bash setup_jetson.sh
set -e
cd "$(dirname "$0")"

if [ ! -f /etc/nv_tegra_release ]; then
  echo "This script is for a Jetson. On a Raspberry Pi use setup_pi.sh."
  exit 1
fi
if ! python3 -c 'import sys; sys.exit(sys.version_info < (3, 10))'; then
  echo "Needs Python 3.10 or newer (JetPack 6). The original Jetson Nano (JetPack 4) is too old; use the Orin."
  exit 1
fi

sudo apt update
sudo apt install -y mpv ffmpeg git python3-venv python3-numpy python3-yaml python3-pil fonts-noto-core
# JetPack ships OpenCV with camera (GStreamer) support. Only install it if it is missing.
python3 -c 'import cv2' 2>/dev/null || sudo apt install -y python3-opencv

python3 -m venv --system-site-packages .venv
.venv/bin/pip install ncnn==1.0.20261020

# Start the kiosk when the desktop logs in, and keep the screen awake.
chmod +x run.sh
mkdir -p ~/.config/autostart
sed "s#__DIR__#$PWD#" kiosk.desktop > ~/.config/autostart/annakut-kiosk.desktop
gsettings set org.gnome.desktop.session idle-delay 0 || true
gsettings set org.gnome.desktop.screensaver lock-enabled false || true

echo
echo "Setup done. Next:"
echo "  1. Speed check:   .venv/bin/python bench.py"
echo "  2. Aim camera:    .venv/bin/python kiosk.py --aim      (q quits)"
echo "  3. Videos:        bash add_video.sh /path/to/baby.mp4 baby   (and phone, book, toy)"
echo "  4. Try it:        ./run.sh"
echo "  5. Reboot: the kiosk starts by itself."
