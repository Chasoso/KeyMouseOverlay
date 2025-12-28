import sys
import os
import queue
import threading
import tkinter as tk
import tkinter.font as tkfont
from pynput import mouse, keyboard
import pystray
from PIL import Image, ImageDraw


def load_tray_icon_from_ico(filename: str):
    """
    Load .ico for pystray.
    Works both for:
      - normal python script
      - PyInstaller onefile exe
    """
    if hasattr(sys, "_MEIPASS"):
        # PyInstaller onefile
        base_path = sys._MEIPASS
    else:
        # normal script
        base_path = os.path.abspath(os.path.dirname(__file__))

    ico_path = os.path.join(base_path, filename)

    # Pillow can open .ico directly
    img = Image.open(ico_path)

    # pystray prefers RGBA
    return img.convert("RGBA")


# --- Key helpers -------------------------------------------------------------

def key_id(k):
    """Stable ID for pressed keys (avoids collisions across Key/KeyCode)."""
    if isinstance(k, keyboard.Key):
        return ("K", k)

    if isinstance(k, keyboard.KeyCode):
        if k.vk is not None:
            return ("C", k.vk)
        if k.char is not None:
            return ("CH", k.char)
        return ("CID", id(k))

    return ("U", str(k))


def format_key(k) -> str:
    """Convert pynput key object into a display label."""
    if isinstance(k, keyboard.KeyCode):
        # Ctrl+A..Z may arrive as control chars (\x01..\x1a): restore to A..Z
        if k.char:
            try:
                code = ord(k.char)
                if 1 <= code <= 26:
                    return chr(code + 64)
            except TypeError:
                pass
            return k.char.upper() if len(k.char) == 1 else str(k.char)

        # Some environments provide only vk
        if k.vk is not None:
            if 65 <= k.vk <= 90:
                return chr(k.vk)
            if 97 <= k.vk <= 122:
                return chr(k.vk).upper()

        return ""

    if isinstance(k, keyboard.Key):
        name = k.name or str(k)
        mapping = {
            "ctrl_l": "Ctrl", "ctrl_r": "Ctrl",
            "alt_l": "Alt", "alt_r": "Alt",
            "shift_l": "Shift", "shift_r": "Shift",
            "cmd": "Win", "cmd_l": "Win", "cmd_r": "Win",
            "enter": "Enter", "return": "Enter",
            "space": "Space",
            "backspace": "Backspace",
            "tab": "Tab",
            "esc": "Esc",
            "caps_lock": "Caps",
            "page_up": "PgUp",
            "page_down": "PgDn",
            "delete": "Del",
            "insert": "Ins",
            "home": "Home",
            "end": "End",
            "up": "Up",
            "down": "Down",
            "left": "Left",
            "right": "Right",
        }
        return mapping.get(name, name.title())

    return str(k)


def sort_key_label(label: str) -> int:
    """Sort order: modifiers first."""
    order = {"Ctrl": 0, "Shift": 1, "Alt": 2, "Win": 3}
    return order.get(label, 10)


def round_rect(canvas: tk.Canvas, x0, y0, x1, y1, r, **kwargs):
    """Draw a rounded rectangle as a smooth polygon."""
    r = max(0, min(r, (x1 - x0) / 2, (y1 - y0) / 2))
    points = [
        x0 + r, y0,
        x1 - r, y0,
        x1, y0,
        x1, y0 + r,
        x1, y1 - r,
        x1, y1,
        x1 - r, y1,
        x0 + r, y1,
        x0, y1,
        x0, y1 - r,
        x0, y0 + r,
        x0, y0,
    ]
    return canvas.create_polygon(points, smooth=True, splinesteps=64, **kwargs)


# --- Tray icon helpers (pystray) ---------------------------------------------

def make_tray_image(size=64):
    """Simple tray icon image (no external file)."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # mouse-ish shape
    pad = size * 0.18
    x0, y0 = pad, pad * 0.9
    x1, y1 = size - pad, size - pad * 0.7
    r = int(size * 0.22)
    d.rounded_rectangle([x0, y0, x1, y1], radius=r, outline=(230, 230, 230, 255), width=3, fill=(20, 20, 20, 255))
    # split line
    cx = (x0 + x1) / 2
    d.line([cx, y0 + (y1 - y0) * 0.18, cx, y0 + (y1 - y0) * 0.55], fill=(200, 200, 200, 255), width=3)
    # highlight dot
    d.ellipse([size * 0.60, size * 0.18, size * 0.78, size * 0.36], fill=(255, 213, 74, 255))

    return img


# --- App ---------------------------------------------------------------------

class FollowInputOverlay:
    BG = "#000000"          # used as transparent color (Windows)
    KEY_TEXT = "#010101"    # "almost black" (true black would be transparent)
    KEY_BG = "#FFFFFF"

    def __init__(self):
        self.root = tk.Tk()
        self._configure_root()

        # behavior / layout
        self.follow_interval_ms = 16
        self.offset_x = 18
        self.offset_y = 18

        self.gap_between_mouse_and_keys = 10

        self.mouse_scale = 0.82
        self.body_shrink_px = 22

        self.hold_ms = 600
        self.inactivity_ms = 2000
        self.inactivity_ms_options = [
            ("Off", None),
            ("1s", 1000),
            ("2s", 2000),
            ("3s", 3000),
            ("5s", 5000),
        ]

        self._clear_after_id = None
        self._last_labels_text = ""
        self._inactivity_after_id = None

        self.events = queue.Queue()

        self.mouse_state = {"left": False, "right": False}
        self.pressed_key_ids = set()
        self.id_to_key = {}

        self._build_ui()
        self._start_listeners()

        self._visible = True
        self._user_visible = True
        self._auto_hidden = False
        self.tray_icon = None
        self._start_tray_icon()

        self._running = True
        self.root.after(self.follow_interval_ms, self._follow_mouse)
        self.root.after(16, self._process_queue)
        self._reset_inactivity_timer()

    def _configure_root(self):
        self.root.title("Follow Input Overlay")
        self.root.configure(bg=self.BG)
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.88)
        self.root.wm_attributes("-transparentcolor", self.BG)

    # --- UI ------------------------------------------------------------------

    def _build_ui(self):
        frm = tk.Frame(self.root, bg=self.BG)
        frm.pack(padx=6, pady=6)

        row = tk.Frame(frm, bg=self.BG)
        row.pack()

        self.canvas = tk.Canvas(row, bg=self.BG, highlightthickness=0)
        self.canvas.pack(side="left")

        self.text_canvas = tk.Canvas(row, height=46, bg=self.BG, highlightthickness=0)
        self.text_canvas.pack(side="left", padx=(self.gap_between_mouse_and_keys, 0))

        self.text_font = ("Segoe UI", 16, "bold")
        self.text_center = (0, 23)

        self.key_bg = round_rect(self.text_canvas, 0, 0, 0, 0, 10, fill=self.KEY_BG, outline="", width=0)
        self.key_text = self.text_canvas.create_text(
            0, 23,
            text="",
            font=self.text_font,
            fill=self.KEY_TEXT,
            anchor="center"
        )
        self.text_canvas.tag_lower(self.key_bg, self.key_text)

        self._tk_font = tkfont.Font(family="Segoe UI", size=16, weight="bold")

        self._draw_mouse_icon()

        self._apply_key_plate_width("")
        self._fit_window_to_content()

    def _draw_mouse_icon(self):
        self.canvas.delete("all")

        # Base geometry (before scaling)
        x0, y0, x1, y1 = 35, 10, 145, 150
        cx = (x0 + x1) / 2
        btn_bottom = y0 + 65
        r = 28
        inset = 6

        # Apply overall scale
        scale = self.mouse_scale
        mx = (x0 + x1) / 2
        my = (y0 + y1) / 2

        def sx(x): return mx + (x - mx) * scale
        def sy(y): return my + (y - my) * scale

        x0s, y0s, x1s, y1s = sx(x0), sy(y0), sx(x1), sy(y1)
        cxs = sx(cx)
        btn_bottom_s = sy(btn_bottom)

        # Shrink body mainly: move bottom up
        new_y1 = y1s - self.body_shrink_px
        y1s = max(new_y1, btn_bottom_s + 14)

        # Canvas size
        pad = 4
        w = int((x1s - x0s) + pad * 2)
        h = int((y1s - y0s) + pad * 2)
        self.canvas.config(width=w, height=h)

        dx = pad - x0s
        dy = pad - y0s

        def tx(x): return x + dx
        def ty(y): return y + dy

        self.mouse_outline = round_rect(
            self.canvas,
            tx(x0s), ty(y0s), tx(x1s), ty(y1s),
            r * scale,
            fill="#141414", outline="#E6E6E6", width=3
        )

        bx0, by0, bx1, by1 = x0s + inset * scale, y0s + inset * scale, x1s - inset * scale, btn_bottom_s
        if (by1 - by0) < 22:
            by1 = by0 + 22

        self.left_btn = self.canvas.create_rectangle(tx(bx0), ty(by0), tx(cxs - 2), ty(by1), outline="", fill="#1F1F1F")
        self.right_btn = self.canvas.create_rectangle(tx(cxs + 2), ty(by0), tx(bx1), ty(by1), outline="", fill="#1F1F1F")
        self.canvas.create_line(tx(cxs), ty(by0), tx(cxs), ty(by1), fill="#CFCFCF", width=2)

    def _fit_window_to_content(self):
        self.root.update_idletasks()
        w = self.root.winfo_reqwidth()
        h = self.root.winfo_reqheight()
        self.root.geometry(f"{w}x{h}+40+40")

    def _cancel_after(self, after_id):
        if after_id is None:
            return None
        try:
            self.root.after_cancel(after_id)
        except Exception:
            pass
        return None

    # --- pynput listeners -----------------------------------------------------

    def _start_listeners(self):
        def on_click(_x, _y, button, pressed):
            if button == mouse.Button.left:
                name = "left"
            elif button == mouse.Button.right:
                name = "right"
            else:
                return
            self.events.put(("mouse", name, pressed))

        def on_press(k):
            self.events.put(("key", k, True))

        def on_release(k):
            self.events.put(("key", k, False))

        self.mouse_listener = mouse.Listener(on_click=on_click)
        self.kb_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        self.mouse_listener.start()
        self.kb_listener.start()

    # --- Follow window --------------------------------------------------------

    def _follow_mouse(self):
        if not self._running:
            return

        if self._visible:
            try:
                x, y = mouse.Controller().position
                self.root.geometry(f"+{int(x + self.offset_x)}+{int(y + self.offset_y)}")
            except Exception:
                pass

        self.root.after(self.follow_interval_ms, self._follow_mouse)

    # --- Event processing -----------------------------------------------------

    def _process_queue(self):
        try:
            while True:
                kind, *rest = self.events.get_nowait()

                if kind == "mouse":
                    name, pressed = rest
                    self.mouse_state[name] = pressed
                    self._render_mouse()
                    self._handle_activity()

                elif kind == "key":
                    k, pressed = rest
                    kid = key_id(k)
                    if pressed:
                        self.pressed_key_ids.add(kid)
                        self.id_to_key[kid] = k
                    else:
                        self.pressed_key_ids.discard(kid)
                    self._render_keys()
                    self._handle_activity()

        except queue.Empty:
            pass
        except Exception as e:
            print("Process queue error:", repr(e))

        if self._running:
            self.root.after(16, self._process_queue)

    def _render_mouse(self):
        def fill(on: bool):
            return "#FFD54A" if on else "#1F1F1F"

        self.canvas.itemconfig(self.left_btn, fill=fill(self.mouse_state["left"]))
        self.canvas.itemconfig(self.right_btn, fill=fill(self.mouse_state["right"]))

    def _render_keys(self):
        labels = []
        for kid in self.pressed_key_ids:
            k = self.id_to_key.get(kid)
            if not k:
                continue
            label = format_key(k)
            if label:
                labels.append(label)

        labels = sorted(set(labels), key=lambda s: (sort_key_label(s), s))

        if labels:
            text = " + ".join(labels)
            self._set_key_text(text)
            self._last_labels_text = text
            self._clear_after_id = self._cancel_after(self._clear_after_id)
            return

        if not self._last_labels_text:
            self._set_key_text("")
            return

        self._set_key_text(self._last_labels_text)
        self._schedule_clear_keys()

    # --- Key plate ------------------------------------------------------------

    def _apply_key_plate_width(self, text: str):
        if not text:
            self.text_canvas.config(width=10)
            self.text_center = (5, 23)
            self.text_canvas.coords(self.key_text, self.text_center[0], self.text_center[1])
            return

        pad_x = 10
        w = self._tk_font.measure(text) + pad_x * 2 + 10
        w = max(120, min(520, w))
        self.text_canvas.config(width=w)
        self.text_center = (w // 2, 23)
        self.text_canvas.coords(self.key_text, self.text_center[0], self.text_center[1])

    def _set_key_text(self, text: str):
        self.text_canvas.itemconfig(self.key_text, text=text)

        self._apply_key_plate_width(text)

        if not text:
            self.text_canvas.coords(self.key_bg, 0, 0, 0, 0, 0, 0)
            self._fit_window_to_content()
            return

        pad_x, pad_y, r = 10, 6, 10
        w = self._tk_font.measure(text)
        h = self._tk_font.metrics("linespace")

        cx, cy = self.text_center
        x0 = cx - w / 2 - pad_x
        y0 = cy - h / 2 - pad_y
        x1 = cx + w / 2 + pad_x
        y1 = cy + h / 2 + pad_y

        r = max(0, min(r, (x1 - x0) / 2, (y1 - y0) / 2))
        points = [
            x0 + r, y0,
            x1 - r, y0,
            x1, y0,
            x1, y0 + r,
            x1, y1 - r,
            x1, y1,
            x1 - r, y1,
            x0 + r, y1,
            x0, y1,
            x0, y1 - r,
            x0, y0 + r,
            x0, y0,
        ]
        self.text_canvas.coords(self.key_bg, *points)
        self.text_canvas.tag_lower(self.key_bg, self.key_text)

        self._fit_window_to_content()

    def _schedule_clear_keys(self):
        self._clear_after_id = self._cancel_after(self._clear_after_id)
        self._clear_after_id = self.root.after(self.hold_ms, self._clear_key_display)

    def _clear_key_display(self):
        self._set_key_text("")
        self._last_labels_text = ""
        self._clear_after_id = None

    # --- Visibility + inactivity -------------------------------------------

    def _update_visibility(self):
        should_show = self._user_visible and not self._auto_hidden
        if should_show and not self._visible:
            self.root.deiconify()
        elif not should_show and self._visible:
            self.root.withdraw()
        self._visible = should_show

    def _handle_activity(self):
        if not self._running:
            return
        self._auto_hidden = False
        self._update_visibility()
        self._reset_inactivity_timer()

    def _reset_inactivity_timer(self):
        self._inactivity_after_id = self._cancel_after(self._inactivity_after_id)

        if self.inactivity_ms is None:
            return

        self._inactivity_after_id = self.root.after(self.inactivity_ms, self._handle_inactivity_timeout)

    def _handle_inactivity_timeout(self):
        if not self._running:
            return
        self._inactivity_after_id = None
        self._auto_hidden = True
        self._update_visibility()

    def _set_inactivity_ms(self, ms):
        self.inactivity_ms = ms
        # Returning from tray should reflect immediately
        self._auto_hidden = False
        self._update_visibility()
        self._reset_inactivity_timer()
        try:
            if self.tray_icon is not None:
                self.tray_icon.update_menu()
        except Exception:
            pass

    # --- Tray (pystray) ------------------------------------------------------

    def _start_tray_icon(self):
        def on_quit(icon, item):
            # pystray thread -> Tk thread
            try:
                self.root.after(0, self.quit)
            except Exception:
                pass
    
        def on_toggle(icon, item):
            try:
                self.root.after(0, self.toggle_visible)
            except Exception:
                pass

        def make_inactivity_item(label, ms):
            def on_set(icon, item):
                try:
                    self.root.after(0, lambda: self._set_inactivity_ms(ms))
                except Exception:
                    pass

            def is_checked(item):
                return self.inactivity_ms == ms

            return pystray.MenuItem(label, on_set, checked=is_checked)

        image = load_tray_icon_from_ico("key_mouse_overlay.ico")

        menu = pystray.Menu(
            pystray.MenuItem("Show/Hide", on_toggle),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "Auto-hide",
                pystray.Menu(*(make_inactivity_item(label, ms) for label, ms in self.inactivity_ms_options))
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", on_quit),
        )

        self.tray_icon = pystray.Icon(
            "KeyMouseOverlay",
            image,
            "KeyMouseOverlay",
            menu
        )

        t = threading.Thread(target=self.tray_icon.run, daemon=True)
        t.start()

    def toggle_visible(self):
        self._user_visible = not self._user_visible
        if self._user_visible:
            self._auto_hidden = False
            self._reset_inactivity_timer()
        self._update_visibility()

    # --- Quit ----------------------------------------------------------------

    def quit(self):
        self._running = False
        self._inactivity_after_id = self._cancel_after(self._inactivity_after_id)
        try:
            self.mouse_listener.stop()
        except Exception:
            pass
        try:
            self.kb_listener.stop()
        except Exception:
            pass

        # stop tray
        try:
            if self.tray_icon is not None:
                self.tray_icon.stop()
        except Exception:
            pass

        try:
            self.root.destroy()
        except Exception:
            pass

    def run(self):
        self._fit_window_to_content()
        self.root.mainloop()


if __name__ == "__main__":
    FollowInputOverlay().run()
