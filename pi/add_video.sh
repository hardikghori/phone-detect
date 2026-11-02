#!/usr/bin/env bash
# Put a video into the kiosk, converted so the Pi 3 plays it smoothly.
# Usage: bash add_video.sh /path/to/your-video.mp4 phone
#   (the second word is the object from config.yaml: phone, book, ...)
set -e
cd "$(dirname "$0")"
src="$1"
name="${2:-phone}"
if [ ! -f "$src" ]; then
  echo "Video not found: $src"
  echo "Usage: bash add_video.sh /path/to/your-video.mp4 phone"
  exit 1
fi
mkdir -p videos
echo "Converting $src to videos/$name.mp4 (720p). On a Pi 3 this takes a few minutes..."
ffmpeg -loglevel error -stats -y -i "$src" -vf "scale=-2:720" -c:v libx264 -preset veryfast -crf 23 \
  -pix_fmt yuv420p -c:a aac -b:a 128k "videos/$name.mp4"
echo "Done: videos/$name.mp4"
