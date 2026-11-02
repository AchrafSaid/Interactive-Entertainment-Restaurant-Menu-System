# Restaurant Menu Gesture Control

The desktop UI follows the supplied OLIVE / TABLE Figma design: welcome screen,
category rail, three dish cards, item-detail sheet, and local order summary.
Original photos, icons, and fonts are bundled in `assets/` for offline use.
The window can be resized; scroll vertically in shorter windows. Tab and Enter
activate controls, Left/Right browse categories, and Escape closes a dish sheet
or returns to the welcome screen.

Click a dish or hold one finger to view its details. Quantity controls and Add
update the local order; Remove and Undo work in the order summary. No restaurant
order or payment is submitted by this prototype. Account, loyalty, staff, and
phone-game services are outside this UI implementation.

The camera and touch-mode switches are connected to the camera controller. It
checks these settings once a second; turning the camera off releases the camera
capture, and turning it back on opens it again.

Use Python 3.12 with Tkinter support. The project uses MediaPipe's legacy
`mp.solutions` API, so its compatible library versions are pinned in
`requirements.txt`.

## Setup

From this folder, using [uv](https://docs.astral.sh/uv/):

```sh
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
```

Or, if Python 3.12 is already installed:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Check the libraries:

```sh
.venv/bin/python test_libraries.py
```

Tkinter comes with the Python installation rather than a pip package. If it is
missing, use a Python 3.12 installation that includes Tkinter.

## Run

In one terminal, start the menu server:

```sh
.venv/bin/python menu_server_gui.py
```

Keep that running. In a second terminal, from this same folder, start the camera
and gesture controller:

```sh
.venv/bin/python integrated_menu.py
```

Allow camera access when macOS asks. Press **Q** in the camera window to quit.

To use the shorter `python` command, run `source .venv/bin/activate` in each
terminal first. This selects the project's libraries even if a Conda environment
such as `(ds)` is active.

## Gestures

- Hold an open palm still for about half a second to open or return to the menu.
- Move your open hand horizontally to change categories: right for next, left
  for previous. A movement of roughly one tenth of the camera width is enough;
  the progress bar shows when a swipe is building. Pause briefly between swipes.
  One continuous sweep changes one category.
- Hold one index finger up in the left, center or right third of the mirrored
  camera view to select the corresponding product card. The camera window shows
  numbered zones and which item will be selected. Keep the hand still until the
  hold bar fills (about half a second). Small hand tremors and brief uncertain
  frames are tolerated.
- Hold a closed fist until the bar fills to hide the menu contents. Small palm
  movements while closing the fist do not cancel this gesture.

After changing the code, stop and restart both the menu server and the camera
controller so they use the same gesture commands. The camera checks the menu's
state on connection and waits for each action to be applied before displaying
its confirmed state. A second menu server on the same port is refused before
opening another window.

## Check menu interactions

```sh
.venv/bin/python -m unittest discover -s tests -v
```

The checks cover noisy tracking, rotated hand poses, swipes, item selection,
mouse buttons, and confirmed gesture delivery through the socket and Tkinter
queue. The menu checks require macOS window access; they do not open the camera.

## MediaPipe `solutions` error

`AttributeError: module 'mediapipe' has no attribute 'solutions'` means the
interpreter is using an incompatible MediaPipe installation. Use the `.venv`
commands above. MediaPipe 0.10.31 removed this API; this project uses 0.10.21.
See the [MediaPipe maintainer's explanation](https://github.com/google-ai-edge/mediapipe/issues/6204).
