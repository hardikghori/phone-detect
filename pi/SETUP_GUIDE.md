# Setting up the Annakut "crying baby" kiosk (about 45 minutes)

What it does: the screen shows a crying baby. A camera looks down into a small doll-house room. A visitor picks one object (phone, book or toy) and puts it in the room. That object's video plays, then a thank-you screen, then the crying baby again for the next person. Runs fully offline after setup.

## You need
- **Jetson Orin** (Orin Nano or Orin NX) with JetPack 6 already on it, and its power supply. Use the Orin, not the old Jetson Nano: the Nano's software is too old for this.
- A camera: USB webcam, or a ribbon camera for the Jetson (IMX219 type)
- The digital screen with an HDMI or DisplayPort cable, and speakers if the screen has none
- USB keyboard and mouse for setup
- Internet **for setup only** (about 10 minutes). Wi-Fi without antennas is too slow: use a network cable, or plug in a phone with a USB cable and turn on USB tethering
- The 4 videos from the content team on a USB stick: `baby.mp4`, `phone.mp4`, `book.mp4`, `toy.mp4`

## Step 1: Build the room
1. Mount the camera on the room's ceiling, looking straight down at the floor.
2. Light the room evenly (a small LED strip inside works). Avoid shadows and reflections.
3. Plain floor color that is different from the objects (for example light beige). Not black, not patterned.
4. Leave space for only one object.

## Step 2: First start
1. Ribbon camera: connect it **before** powering on. USB camera: plug it in.
2. Connect the screen, keyboard, mouse, then power. Log in to the desktop.
3. Open **Terminal** (Ctrl+Alt+T).

## Step 3: Install (type these in Terminal, one line at a time)
```
git clone https://github.com/hardikghori/phone-detect.git
cd phone-detect/pi
bash setup_jetson.sh
```
This takes about 10 minutes. It ends with "Setup done".

## Step 4: Speed check
```
.venv/bin/python bench.py
```
It prints two lines ending in PASS or TOO SLOW. **Take a photo of the screen and send it to Hardik.**

## Step 5: Aim the camera
```
.venv/bin/python kiosk.py --aim
```
The camera picture opens with green boxes around what it sees. Put each real object in the room, one at a time, in a few positions. The bottom line says "counts as: phone" (or book, toy) when it works. Press `q` to close.
**Take a photo of the screen for each object and send it to Hardik.** If an object does not show up, tell him which one: he can tune it or train the model on your exact objects.

## Step 6: Add the 4 videos
The kit already has 4 labeled stand-in videos (colored screens that say "CRYING BABY (placeholder)", "PHONE VIDEO (placeholder)" and so on), so Step 7 works before the real videos arrive. Replace them when you have the real ones.

Plug in the USB stick. It shows up under `/media/` (your username, then the stick's name). Run one line per video:
```
bash add_video.sh /media/YOURNAME/STICKNAME/baby.mp4 baby
bash add_video.sh /media/YOURNAME/STICKNAME/phone.mp4 phone
bash add_video.sh /media/YOURNAME/STICKNAME/book.mp4 book
bash add_video.sh /media/YOURNAME/STICKNAME/toy.mp4 toy
```
Tip: type `bash add_video.sh /media/` then press Tab to fill in the path.
The thank-you screen is already included (`videos/thanks.png`). To use your own, replace that file, or put a `thanks.mp4` there and change `thanks:` in `config.yaml`.

## Step 7: Try it
```
./run.sh
```
The crying baby plays full screen. Put a phone in the room: after about 1 second the phone video plays, then thank you, then the baby again.
- Take the object out before the next person. A new object only counts after the room has been empty for 2 seconds, so a left-behind object never replays.
- Cooldown: after the baby comes back, the camera is ignored for 3 seconds so the baby always cries for a moment. Change `cooldown_seconds` in `config.yaml`.
- Keys: `1` phone video, `2` book video, `3` toy video, `0` skip, `q` quit.

## Step 8: Make it start by itself
Reboot. The kiosk opens on its own. You can unplug the keyboard and the network now.

## If something goes wrong
- **"no camera found"**: check the cable, then reboot.
- **No sound**: click the speaker icon at the top right and choose the screen (HDMI/DisplayPort) or your speakers.
- **Object not detected**: run Step 5 again and look at the "counts as" line. Better light usually fixes it.
- Anything else: send Hardik a photo of the screen, plus the last lines of `kiosk.log` (`tail kiosk.log`).
