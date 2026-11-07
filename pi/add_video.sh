#!/usr/bin/env bash
# Put a video into the kiosk, converted to 720p so it plays smoothly.
# Usage: bash add_video.sh /path/to/your-video.mp4 phone
#   (the second word is the file name: baby, phone, book, toy)
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
echo "Converting $src to videos/$name.mp4 (720p)."
ffmpeg -loglevel error -stats -y -i "$src" -vf "scale=-2:720" -c:v libx264 -preset veryfast -crf 23 \
  -pix_fmt yuv420p -c:a aac -b:a 128k "videos/$name.mp4"
echo "Done: videos/$name.mp4"
