#!/usr/bin/env bash
# Runs the kiosk and restarts it if it crashes. Pressing q in the camera window stops it for good.
cd "$(dirname "$0")"
export DISPLAY="${DISPLAY:-:0}"
while true; do
  .venv/bin/python kiosk.py >> kiosk.log 2>&1 && break
  echo "$(date) kiosk exited with an error, restarting" >> kiosk.log
  sleep 2
done
