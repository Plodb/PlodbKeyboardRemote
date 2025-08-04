import asyncio
import logging
import base64
import threading
import webbrowser
import io
import os
import ctypes
import time
import json
import sys
import signal
import qrcode
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk, ImageDraw
import websockets
import keyboard
import random
import string
import socket
import portalocker
import pystray
from pystray import MenuItem as item
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

LOG_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), "plodb.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler(sys.stderr) if sys.stderr else logging.NullHandler(),
    ],
)
# --- Constants ---
ICON_BASE64 = """/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAYEBQYFBAYGBQYHBwYIChAKCgkJChQODwwQFxQYGBcUFhYaHSUfGhsjHBYWICwgIyYnKSopGR8tMC0oMCUoKSj/2wBDAQcHBwoIChMKChMoGhYaKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCj/wAARCAAyADIDASIAAhEBAxEB/8QAHAAAAQQDAQAAAAAAAAAAAAAAAAUGBwgCAwQB/8QALhAAAQMDAwMCBAcBAAAAAAAAAQIDBAAFEQYSIRMxQRRRByJhcRUyUmKBobHR/8QAGwEAAgMBAQEAAAAAAAAAAAAAAgMBBAUGAAf/xAApEQABAwMDAwIHAAAAAAAAAAABAAIDBBEhBRMxBkFhElEjMkKBkbHw/9oADAMBAAIRAxEAPwCvenbcLvfYNvU50kyHUtleM7QfNW3+HGjdLIjrYs1vjuTI6Qh185Lm4jg5UOxHmqv6J0bqXU0oO6cgPOdFYPqMhDaFDnlR4z9KtnpebedJ2BUrXlycmy1rwoxEKdbQnA5Xxwc+U4FZuvmKYCMzWI+kGxJ/uybcjK06ns06URGRbHgjJHCmgFJ8gnJx9D/VQJqLSDMqTMQYbcZ5gqUVIIRlPfPbCuCO2c+9WjkXA3W3tzbTIQ4laOo0oAKS5xwD7Cq/fEEypVvfUp9tu4KVtceI+XyDjaeM8c81kdP1rpJXxtOB73v9whPzDKgZ9KEvLS0ve2DhKsYyKwromQpEMj1DZSlX5Vd0q+x7Gueu+BBGESKKKKleV7NDT7BP0fbHdKttx7cWxtjpUCpo+Uq/dW+RHukhbjanorcZZO4FvqEp/Tg4HPnv3qj9iv8AdbDKRItM5+K4g7hsUdp+47GrN6H+Kb2pLCy+6mOiZHw3LQO+cjCwP0nzxxXzmv6RrXVBkpHNcScX7fm+fP6Saqpjp49yS9h7ZUmQbbGt9tbgwW+hHbGEJQcbec/7UV/ETpbChl5LMd0DslOSvcRkHtgdhx4pZueobmZRmRZCg0gZEfHy8Dnnz/NRRqrUr9xkPR3OnGkYwgJScq2jgg5wPP04qzpXSupafPu1ffPN8+VSp9Tp60fAN7eElSWm7napLSGSpS47ydrIyEuJVuQFEdvf/aiynhdr87bLe9bIeUvPKUXnCrOxJz8qRzjvk85pn12sEbmXutIYACKKKKsKVk2hTriUNpKlqOAAOTTh0bPNlu7ctcpttsgtvNFKlb0ZwQQBj7U32XXGHUOsrUhxBylSTgg1vXOedXukbXj3+Yc5+45oTfsoLWubZynrTuqYV3ivIjrX1EqThCs7zzxnx4xSLquItt/1bIaC8FCVODAbcPAIHge3vUZWC4+jll6PJ9K9zgL5Qfbnx/IpyXjU13/Dm/XQWhHeA6a0kFKgCfbOatvqhJFtycrDj0p1JU71Pb0nkJl3S3ToEhabhHeacKuVLSfmPfOfNcVKSrtMPU2urCFq3KQo7h/dYqxK3rVHSnJGVNJ2gcdsdvFU/URyt0WKT6KUxbI5AP4nEH0O7/lFRuNR7bkmUUUUxAinbYiRYnFgnekgJV5Az4oooXcKW8pR1I2hFpjrShKVqSjKgME8HuaYSlqV+ZRP3NFFAxMfwvKKKKalL//Z"""
HTML_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), "index.html")
LOCK_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), "plodb.lock")

# --- Globals ---
ip = socket.gethostbyname(socket.gethostname())
tray_icon = None
lock_fp = None
toggled_mods = set()
active_mods = set()
ws_loop = None
ws_server = None
http_server = None
root = None
shutting_down = False
connected_clients = set()
# --- PIN ---
PIN_CODE = "".join(random.choices(string.digits, k=4))
authorized_clients = set()
print(f"[PIN] Web control PIN: {PIN_CODE}")


# --- Language ---
def get_current_lang():
    SUPPORTED_LANGS = ["en", "ru"]

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    hwnd = user32.GetForegroundWindow()
    thread_id = user32.GetWindowThreadProcessId(hwnd, 0)
    layout = user32.GetKeyboardLayout(thread_id)
    lid = layout & 0xFFFF

    buf = ctypes.create_unicode_buffer(9)
    if kernel32.GetLocaleInfoW(lid, 0x00000003, buf, len(buf)):
        lang = buf.value.lower()
        if any(lang.startswith(s) for s in SUPPORTED_LANGS):
            return buf.value
        print(f"[UNSUPPORTED LAYOUT: {buf.value}] → FORCING ENU")
        return "ENU"
    return "unknown"


prev_lang = get_current_lang()


def shutdown(*_):
    global tray_icon, ws_server, ws_loop, http_server, lock_fp, root, shutting_down
    if shutting_down:
        return
    shutting_down = True

    if tray_icon:
        try:
            tray_icon.stop()
        except Exception as e:
            logging.warning("Tray icon stop failed: %s", e)

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

    if ws_server and ws_loop and not ws_loop.is_closed():
        ws_server.close()
        fut = asyncio.run_coroutine_threadsafe(ws_server.wait_closed(), ws_loop)
    try:
        fut.result(timeout=3)
    except Exception as e:
        logging.warning("Graceful WS shutdown failed: %s", e)
        ws_loop.call_soon_threadsafe(ws_loop.stop)

    ws_loop.call_soon_threadsafe(ws_loop.stop)

    if http_server:
        http_server.shutdown()
        http_server.server_close()

    if lock_fp:
        try:
            portalocker.unlock(lock_fp)
            lock_fp.close()
        except Exception:
            pass

    if root:
        root.after(0, root.quit)


# --- Ensure single instance ---
def ensure_single_instance():
    global lock_fp
    try:
        lock_fp = open(LOCK_PATH, "w")
        portalocker.lock(lock_fp, portalocker.LOCK_EX | portalocker.LOCK_NB)
    except portalocker.exceptions.LockException:
        logging.warning("Already running.")
        try:
            tmp = tk.Tk()
            tmp.withdraw()
            messagebox.showinfo("PlodbKeyboardRemote", "Already running.")
            tmp.destroy()
        except Exception:
            pass
        sys.exit(0)


# --- Tray logic ---
def create_tray_icon(root):
    def on_open(icon, item):
        root.after(0, root.deiconify)
        icon.stop()

    def on_exit(icon, item):
        shutdown()

    img_data = base64.b64decode(ICON_BASE64)
    image = Image.open(io.BytesIO(img_data)).convert("RGBA")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, image.width, image.height), outline=(0, 0, 0, 0))

    return pystray.Icon(
        "PlodbBoard",
        image,
        "PlodbBoard",
        menu=pystray.Menu(item("Open", on_open), item("Exit", on_exit)),
    )


def show_gui():
    global tray_icon, root
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

    tk.Label(root, text="PlodbKeyboardRemote", font=("Consolas", 13, "bold")).pack(
        pady=5
    )
    tk.Label(root, text=f"Web: http://{ip}:8888", font=("Consolas", 10)).pack()
    tk.Label(root, text=f"WS: ws://{ip}:8765", font=("Consolas", 10)).pack()
    tk.Label(
        root,
        text=f"PIN: {PIN_CODE}",
        font=("Consolas", 10, "bold"),
    ).pack(pady=(2, 8))

    tk.Button(
        root,
        text="Open in Browser",
        command=lambda: webbrowser.open(f"http://{ip}:8888"),
        font=("Consolas", 10),
    ).pack(pady=5)

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

    root.protocol("WM_DELETE_WINDOW", shutdown)
    root.bind(
        "<Unmap>", lambda e: minimize_to_tray() if root.state() == "iconic" else None
    )

    root.mainloop()


# --- WebSocket logic ---


async def handler(websocket):
    global toggled_mods, active_mods, connected_clients, authorized_clients
    connected_clients.add(websocket)
    authed = False

    try:
        async for message in websocket:
            data = json.loads(message)
            msg_type = data.get("type")
            key = data.get("key", "")

            if not authed:
                if msg_type == "pin" and data.get("pin") == PIN_CODE:
                    authorized_clients.add(websocket)
                    authed = True
                    await websocket.send(json.dumps({"type": "pin_accepted"}))
                else:
                    await websocket.send(json.dumps({"type": "pin_required"}))
                continue

            if msg_type == "keydown":
                keyboard.press(key)
                active_mods.add(key)
            elif msg_type == "keyup":
                keyboard.release(key)
                active_mods.discard(key)
            elif msg_type == "get_lang":
                lang = get_current_lang()
                await websocket.send(json.dumps({"type": "lang", "lang": lang}))
                await websocket.send(
                    json.dumps(
                        {
                            "type": "sync",
                            "layout": "ru" if lang.lower().startswith("ru") else "en",
                        }
                    )
                )
    except Exception as e:
        logging.warning("WebSocket error: %s", e)
    finally:
        connected_clients.discard(websocket)
        authorized_clients.discard(websocket)


def run_ws_server():
    global ws_loop, ws_server

    async def start():
        global ws_server
        ws_server = await websockets.serve(
            handler, "", 8765, ping_interval=20, ping_timeout=10
        )
        await ws_server.wait_closed()

    ws_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(ws_loop)
    try:
        ws_loop.run_until_complete(start())
    except KeyboardInterrupt:
        pass
    finally:
        if not ws_loop.is_closed():
            ws_loop.close()


def start_http_server():
    global http_server

    class CustomHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=os.path.dirname(HTML_PATH), **kwargs)

    try:
        http_server = ThreadingHTTPServer(("", 8888), CustomHandler)
        logging.info("[HTTP] Serving index.html at http://%s:8888", ip)
        http_server.serve_forever()
    except Exception as e:
        logging.error("HTTP server failed: %s", e)


# mod key listener
from websockets.protocol import State


def start_key_watcher():
    def loop():
        global prev_lang
        prev_state = {"alt": False, "ctrl": False, "shift": False}

        while not shutting_down:
            current_lang = get_current_lang()
            if current_lang != prev_lang:
                print(f"[LANG DETECTED] {prev_lang} → {current_lang}")
                prev_lang = current_lang
                layout = "ru" if current_lang.lower().startswith("ru") else "en"

                for ws in list(connected_clients):
                    if ws.state != State.OPEN:
                        connected_clients.discard(ws)
                        continue
                    try:
                        print(f"[SEND] sync → {layout} → {ws.remote_address}")
                        asyncio.run_coroutine_threadsafe(
                            ws.send(json.dumps({"type": "sync", "layout": layout})),
                            ws_loop,
                        )
                    except Exception as e:
                        logging.warning("Failed to send layout to client: %s", e)

            for key in prev_state:
                current = keyboard.is_pressed(key)
                if prev_state[key] and not current:
                    msg = json.dumps({"type": "keyup", "key": key})
                    for ws in list(connected_clients):
                        if ws.state != State.OPEN:
                            connected_clients.discard(ws)
                            continue
                        try:
                            asyncio.run_coroutine_threadsafe(ws.send(msg), ws_loop)
                        except Exception as e:
                            logging.warning("Failed to send keyup: %s", e)
                prev_state[key] = current

            time.sleep(0.05)

    threading.Thread(target=loop, daemon=True).start()


# --- Start ---
if __name__ == "__main__":
    ensure_single_instance()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, shutdown)

    ws_thread = threading.Thread(target=run_ws_server)
    http_thread = threading.Thread(target=start_http_server)
    ws_thread.start()
    http_thread.start()
    start_key_watcher()

    try:
        show_gui()
    finally:
        shutdown()
        ws_thread.join()
        http_thread.join()
        if root:
            root.destroy()
