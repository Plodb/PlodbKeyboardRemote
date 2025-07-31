# PlodbBoardRemote

A full virtual keyboard server for remote control over LAN, designed to run on your PC and be accessed from any device with a browser.

## Features

- Full keyboard layout (with modifiers, F1–F12, arrows, etc.)
- Realtime keypress
- WebSocket-powered low latency
- PyInstaller-ready (single `.exe`)

##  Usage

1. Run the script or the `.exe` file.
2. Open the link in your browser (shown in GUI or QR).
3. Tap your keys remotely like a goddamn hacker.

## Build

To create standalone EXE:

```bash
pyinstaller PlodbKeyboardRemote.py --onefile --icon=icon.ico 