# KeyMouseOverlay

KeyMouseOverlay is a lightweight Windows overlay application that visualizes  
mouse button presses and keyboard input in real time.

It is designed for hands-on sessions, live demonstrations, and screen recording,
especially for tools such as Tableau or other GUI-based applications.

---

## Features

- Visual mouse overlay (left and right buttons)
- Real-time keyboard input display
- Supports multiple simultaneous key presses
- Correct handling of modifier keys (Ctrl, Shift, Alt, Win)
- Short key hold after release for better readability
- Borderless, always-on-top overlay window
- Transparent background on Windows
- Minimal and unobtrusive UI

---

## Typical Use Cases

- Tableau hands-on workshops
- Live demonstrations and presentations
- Tutorial video recording
- Screen sharing and streaming (e.g. OBS)

---

## Download

KeyMouseOverlay.exe  
(Windows only)

No installation is required. Download and run the executable.

---

## How to Use

- Left mouse button + drag  
  Move the overlay window

- Right mouse button  
  Open menu and quit the application

The overlay automatically shows:
- Mouse button states
- Currently pressed keys (for example: Ctrl + Shift + C)

---

## Platform Support

- Windows 11: supported
- macOS / Linux: not supported  
  (The transparent overlay relies on Windows-specific behavior)

---

## Implementation Details

- Implemented in Python
- UI built with Tkinter
- Input captured using pynput
- Background transparency achieved via color-key technique
- Key labels use a background plate for readability on any background

---

## License

MIT License

