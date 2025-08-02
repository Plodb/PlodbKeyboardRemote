import asyncio
import logging
import base64
import threading
import webbrowser
import io
import os
import sys
import qrcode
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk, ImageDraw
import websockets
import keyboard
import socket
import portalocker
import pystray
from pystray import MenuItem as item
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
# --- Constants ---
ICON_BASE64 = """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"""
HTML_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), "index.html")
LOCK_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)),  "plodb.lock")

# --- Globals ---
ip = socket.gethostbyname(socket.gethostname())
tray_icon = None
lock_fp = None
toggled_mods = set()
active_mods = set()

# --- Ensure single instance ---
def ensure_single_instance():
    global lock_fp
    try:
        lock_fp = open(LOCK_PATH, "w")
        portalocker.lock(lock_fp, portalocker.LOCK_EX | portalocker.LOCK_NB)
    except portalocker.exceptions.LockException:
        print("Already running.")
        sys.exit(0)

# --- Tray logic ---
def create_tray_icon(root):
    def on_open(icon, item):
        root.after(0, root.deiconify)
        icon.stop()

    def on_exit(icon, item):
        icon.stop()
        root.quit()

    img_data = base64.b64decode(ICON_BASE64)
    image = Image.open(io.BytesIO(img_data)).convert("RGBA")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, image.width, image.height), outline=(0, 0, 0, 0))

    return pystray.Icon("PlodbBoard", image, "PlodbBoard", menu=pystray.Menu(
        item("Open", on_open),
        item("Exit", on_exit)
    ))

def show_gui():
    global tray_icon
    root = tk.Tk()
    root.title("Remote Keyboard Server")
    root.geometry("320x400")
    root.resizable(False, False)

    try:
        icon_data = base64.b64decode(ICON_BASE64)
        icon_img = Image.open(io.BytesIO(icon_data))
        icon_tk = ImageTk.PhotoImage(icon_img)
        root.iconphoto(False, icon_tk)
    except Exception as e:
        logging.warning("Icon load failed: %s", e)

    tk.Label(root, text="PlodbKeyboardRemote", font=("Consolas", 13, "bold")).pack(pady=5)
    tk.Label(root, text=f"Web: http://{ip}:8888", font=("Consolas", 10)).pack()
    tk.Label(root, text=f"WS: ws://{ip}:8765", font=("Consolas", 10)).pack()

    tk.Button(root, text="Open in Browser", command=lambda: webbrowser.open(f"http://{ip}:8888"),
              font=("Consolas", 10)).pack(pady=5)

    qr = qrcode.make(f"http://{ip}:8888")
    buffer = io.BytesIO()
    qr.save(buffer, format="PNG")
    buffer.seek(0)
    qr_img = Image.open(buffer).resize((200, 200))
    tk_img = ImageTk.PhotoImage(qr_img)
    qr_label = tk.Label(root, image=tk_img)
    qr_label.image = tk_img
    qr_label.pack(pady=5)

    def minimize_to_tray(event=None):
        root.withdraw()
        global tray_icon
        tray_icon = create_tray_icon(root)
        threading.Thread(target=tray_icon.run, daemon=True).start()

    root.protocol("WM_DELETE_WINDOW", minimize_to_tray)
    root.bind("<Unmap>", lambda e: minimize_to_tray() if root.state() == "iconic" else None)

    root.mainloop()

# --- WebSocket logic ---
async def handler(websocket):
    global toggled_mods, active_mods
    try:
        async for message in websocket:
            try:
                if message.startswith("toggle:"):
                    key = message[7:]
                    if key in toggled_mods:
                        keyboard.release(key)
                        toggled_mods.remove(key)
                    else:
                        keyboard.press(key)
                        toggled_mods.add(key)
                elif message.startswith("press:"):
                    key = message[6:]
                    keyboard.press(key)
                    active_mods.add(key)
                elif message.startswith("release:"):
                    key = message[8:]
                    keyboard.release(key)
                    active_mods.discard(key)
            except Exception as e:
                logging.warning("Keyboard action failed: %s", e)
    finally:
        # Release any keys that might still be pressed when the client disconnects
        for key in toggled_mods.copy():
            try:
                keyboard.release(key)
            except Exception as e:
                logging.warning("Keyboard action cleanup failed: %s", e)
        toggled_mods.clear()

        for key in active_mods.copy():
            try:
                keyboard.release(key)
            except Exception as e:
                logging.warning("Keyboard action cleanup failed: %s", e)
        active_mods.clear()

async def start_ws_server():
    async with websockets.serve(handler, "", 8765):
        await asyncio.Future()

def start_websocket_thread():
    asyncio.run(start_ws_server())
def start_http_server():
    class CustomHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=os.path.dirname(HTML_PATH), **kwargs)

    try:
        server = ThreadingHTTPServer(('', 8888), CustomHandler)
        print(f"[HTTP] Serving index.html at http://{ip}:8888")
        server.serve_forever()
    except Exception as e:
        logging.error("HTTP server failed: %s", e)
# --- Start ---
if __name__ == "__main__":
    ensure_single_instance()
    threading.Thread(target=start_websocket_thread, daemon=True).start()
    threading.Thread(target=start_http_server, daemon=True).start()
    show_gui()
