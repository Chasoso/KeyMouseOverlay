# KeyMouseOverlay

KeyMouseOverlay is a lightweight Windows overlay that follows your cursor and visualizes mouse and keyboard input in real time. It is handy for hands-on sessions, live demos, and screen recording (e.g., Tableau, GUI trainings, OBS streaming).

---

## Features

- Mouse overlay with left/right button highlights
- Real-time keyboard display with multiple simultaneous keys and modifier labeling
- Short key hold after release for readability
- Auto-hide after inactivity (configurable in tray; Off/1s/2s/3s/5s)
- Tray menu for Show/Hide toggle, auto-hide interval, and Quit
- Borderless, always-on-top window that follows the cursor with a small offset
- Transparent background on Windows for unobtrusive capture

---

## Typical Use Cases

- Live demonstrations and presentations
- Tutorial or training video recording
- Screen sharing and streaming (OBS, etc.)

---

## Download

KeyMouseOverlay.exe (Windows only)  
No installation required—download and run the executable.

---

## How to Use

- Launch the app: the overlay appears near your cursor and tracks it automatically.
- Tray icon (notification area):  
  - **Show/Hide**: toggle overlay visibility manually.  
  - **Auto-hide**: choose inactivity timeout (Off/1s/2s/3s/5s). If enabled, the overlay hides after the selected idle time and reappears on the next mouse click or key press.  
  - **Quit**: exit the app.
- Displayed content: current mouse button states and pressed keys (e.g., `Ctrl + Shift + C`).

---

## Platform Support

- Windows 11: supported  
- macOS / Linux: not supported (transparency relies on Windows-specific behavior)

---

## Implementation Details

- Python + Tkinter for UI
 - pynput for global input capture
- Pystray for the system tray icon and menu
- Color-key transparency for the background
- Key labels use a background plate for readability on any backdrop

---

## License

MIT License

