import queue
import tkinter as tk
import tkinter.font as tkfont

from pynput import mouse, keyboard


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


# --- App ---------------------------------------------------------------------

class InputOverlayApp:
    BG = "#000000"          # used as transparent color
    KEY_TEXT = "#010101"    # "almost black" (true black would be transparent)
    KEY_BG = "#FFFFFF"

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Input Overlay")
        self.root.configure(bg=self.BG)

        self.hold_ms = 600
        self._clear_after_id = None
        self._last_labels_text = ""

        # borderless + topmost + transparency (Windows)
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.88)
        self.root.wm_attributes("-transparentcolor", self.BG)

        # drag to move
        self._drag_x = 0
        self._drag_y = 0
        self.root.bind("<ButtonPress-1>", self._start_drag)
        self.root.bind("<B1-Motion>", self._on_drag)

        # right-click menu
        self.menu = tk.Menu(self.root, tearoff=0)
        self.menu.add_command(label="Quit", command=self.quit)
        self.root.bind("<Button-3>", self._show_menu)

        # cross-thread event queue (pynput -> Tk)
        self.q = queue.Queue()

        # input state
        self.mouse_state = {"left": False, "right": False}
        self.pressed_key_ids = set()
        self.id_to_key = {}

        self._build_ui()
        self._start_listeners()

        self._running = True
        self.root.after(16, self._process_queue)

    def _build_ui(self):
        frm = tk.Frame(self.root, bg=self.BG)
        frm.pack(padx=10, pady=10)

        self.canvas = tk.Canvas(frm, width=180, height=160, bg=self.BG, highlightthickness=0)
        self.canvas.pack()

        # mouse shape
        x0, y0, x1, y1 = 35, 10, 145, 150
        cx = (x0 + x1) / 2
        btn_bottom = y0 + 65
        r = 28

        self.mouse_outline = round_rect(
            self.canvas, x0, y0, x1, y1, r,
            fill="#141414", outline="#E6E6E6", width=3
        )

        inset = 6
        bx0, by0, bx1, by1 = x0 + inset, y0 + inset, x1 - inset, btn_bottom

        self.left_btn = self.canvas.create_rectangle(bx0, by0, cx - 2, by1, outline="", fill="#1F1F1F")
        self.right_btn = self.canvas.create_rectangle(cx + 2, by0, bx1, by1, outline="", fill="#1F1F1F")
        self.canvas.create_line(cx, by0, cx, by1, fill="#CFCFCF", width=2)

        # key display (background plate + text)
        self.text_canvas = tk.Canvas(frm, width=180, height=46, bg=self.BG, highlightthickness=0)
        self.text_canvas.pack(pady=(6, 0))

        self.text_font = ("Segoe UI", 16, "bold")
        self.text_center = (90, 23)

        self.key_bg = round_rect(self.text_canvas, 0, 0, 0, 0, 10, fill=self.KEY_BG, outline="", width=0)
        self.key_text = self.text_canvas.create_text(
            self.text_center[0], self.text_center[1],
            text="",
            font=self.text_font,
            fill=self.KEY_TEXT,
            anchor="center"
        )
        self.text_canvas.tag_lower(self.key_bg, self.key_text)

        self._tk_font = tkfont.Font(family="Segoe UI", size=16, weight="bold")

    def _start_listeners(self):
        def on_click(_x, _y, button, pressed):
            if button == mouse.Button.left:
                name = "left"
            elif button == mouse.Button.right:
                name = "right"
            else:
                return
            self.q.put(("mouse", name, pressed))

        def on_press(k):
            self.q.put(("key", k, True))

        def on_release(k):
            self.q.put(("key", k, False))

        self.mouse_listener = mouse.Listener(on_click=on_click)
        self.kb_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        self.mouse_listener.start()
        self.kb_listener.start()

    def _process_queue(self):
        try:
            while True:
                kind, *rest = self.q.get_nowait()

                if kind == "mouse":
                    name, pressed = rest
                    self.mouse_state[name] = pressed
                    self._render_mouse()

                elif kind == "key":
                    k, pressed = rest
                    kid = key_id(k)
                    if pressed:
                        self.pressed_key_ids.add(kid)
                        self.id_to_key[kid] = k
                    else:
                        self.pressed_key_ids.discard(kid)
                    self._render_keys()

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

            if self._clear_after_id is not None:
                try:
                    self.root.after_cancel(self._clear_after_id)
                except Exception:
                    pass
                self._clear_after_id = None
            return

        if self._last_labels_text:
            self._set_key_text(self._last_labels_text)

            if self._clear_after_id is not None:
                try:
                    self.root.after_cancel(self._clear_after_id)
                except Exception:
                    pass

            def clear():
                self._set_key_text("")
                self._last_labels_text = ""
                self._clear_after_id = None

            self._clear_after_id = self.root.after(self.hold_ms, clear)
        else:
            self._set_key_text("")

    def _set_key_text(self, text: str):
        self.text_canvas.itemconfig(self.key_text, text=text)

        if not text:
            self.text_canvas.coords(self.key_bg, 0, 0, 0, 0, 0, 0)
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

    def _start_drag(self, e):
        self._drag_x = e.x
        self._drag_y = e.y

    def _on_drag(self, e):
        x = self.root.winfo_x() + (e.x - self._drag_x)
        y = self.root.winfo_y() + (e.y - self._drag_y)
        self.root.geometry(f"+{x}+{y}")

    def _show_menu(self, e):
        self.menu.tk_popup(e.x_root, e.y_root)

    def quit(self):
        self._running = False
        try:
            self.mouse_listener.stop()
        except Exception:
            pass
        try:
            self.kb_listener.stop()
        except Exception:
            pass
        self.root.destroy()

    def run(self):
        self.root.update_idletasks()
        w = self.root.winfo_reqwidth()
        h = self.root.winfo_reqheight()
        self.root.geometry(f"{w}x{h}+40+40")
        self.root.mainloop()


if __name__ == "__main__":
    InputOverlayApp().run()
