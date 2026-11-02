# Setting up the Annakut kiosk (about 45 minutes)

What it does: a camera looks at a table. When someone holds a phone up to it, your video plays on the TV. When the video ends, the camera comes back on. Runs fully offline after setup.

## You need
- Raspberry Pi 3, its power supply, microSD card (16 GB or more)
- Pi camera (ribbon cable) or a USB webcam
- TV or monitor with an HDMI cable, plus a USB keyboard and mouse for setup
- Wi-Fi or a network cable **for setup only**
- A computer with an SD card slot (to prepare the card)
- The phone video file (put it on a USB stick)

## Step 1: Prepare the SD card (on a computer)
1. Install **Raspberry Pi Imager** from raspberrypi.com/software.
2. Device: **Raspberry Pi 3**.
3. Operating system: choose **Raspberry Pi OS (64-bit)**. If you only see 32-bit, open "Raspberry Pi OS (other)" and pick the **64-bit** one with desktop. 32-bit will not work.
4. Storage: the SD card. When it asks about settings, set a username and password and enter your Wi-Fi.
5. Write, then put the card in the Pi.

## Step 2: First start
1. If you use the Pi camera, connect the ribbon cable **before** powering on (blue side facing the black USB/Ethernet ports on a Pi 3).
2. Connect TV, keyboard, mouse, then power. Wait for the desktop.
3. Open **Terminal** (black icon at the top).

## Step 3: Install (type these in Terminal, one line at a time)
```
git clone https://github.com/hardikghori/phone-detect.git
cd phone-detect/pi
bash setup_pi.sh
```
This takes 10 to 15 minutes. It ends with "Setup done".

## Step 4: Speed check
```
.venv/bin/python bench.py
```
It prints two lines ending in PASS or TOO SLOW. **Take a photo of the screen and send it to Hardik.**

## Step 5: Add your video
Plug in the USB stick. It shows up under `/media/` (your username, then the stick's name). Then:
```
bash add_video.sh /media/YOURNAME/STICKNAME/your-video.mp4 phone
```
Tip: type `bash add_video.sh /media/` then press Tab to fill in the path.

## Step 6: Try it
```
./run.sh
```
The camera picture fills the screen. Hold a phone up close, about 30 to 60 cm from the camera, for one second. The video should play, then the camera comes back.
- Press `q` in the camera screen to stop. While a video plays, `q` skips it.
- After a video, the same phone won't replay for 60 seconds. That's on purpose.

## Step 7: Make it start by itself
Reboot (Pi menu, Shutdown, Reboot). The kiosk opens on its own. You can unplug the keyboard and the Wi-Fi now. It works offline.

## If something goes wrong
- **"This needs the 64-bit Raspberry Pi OS"**: redo Step 1 and choose 64-bit.
- **"no camera found"**: check the cable, then reboot. Make sure the USB webcam is plugged in before starting.
- **No sound**: right-click the speaker icon at the top and choose HDMI (or AV jack for speakers).
- **Video doesn't play when a phone is shown**: hold it closer and still. The text at the bottom of the camera screen shows what it sees (for example "cell phone 80%").
- Anything else: send Hardik a photo of the screen, plus the last lines of `kiosk.log` (`tail kiosk.log`).
