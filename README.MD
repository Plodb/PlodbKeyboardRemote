# PlodbKeyboardRemote

A full virtual keyboard server for remote control over LAN, designed to run on your PC and be accessed from any device with a browser.

## Features

- Full keyboard layout (with toggle/press modifiers, F1–F12, arrows, etc.)
- Realtime keypress
- WebSocket connection
- Pin code auth
- PyInstaller-ready (single `.exe`)

##  Usage

1. Run the script or the `.exe` file.
2. Open the link in your browser (shown in GUI or QR).
3. Enter the pin code (shown in GUI)
4. Tap keys and use combination keys remotely.

## Build

To create standalone EXE:

```bash
pyinstaller --noconfirm --add-data "index.html;." PlodbKeyboardRemote.py 
