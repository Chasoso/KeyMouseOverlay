# KeyMouseOverlay

## 日本語

KeyMouseOverlayは、マウスカーソルを追従し、マウス・キーボード入力をリアルタイム表示する軽量Windows用オーバーレイです。ハンズオン、ライブデモ、録画（OBSなど）での操作可視化に向いています。

### 特長
- 左右クリックのハイライトとリアルタイムのキー表示（複数キー・修飾キー対応）
- キーを離した後もしばらく表示して読みやすさを確保
- 一定時間操作が無いと自動的に非表示（トレイでOff/1s/2s/3s/5sを選択）
- トレイメニューから表示切替、非表示までの時間設定、終了が可能
- カーソル近くに追従するボーダーレス・最前面ウィンドウ
- Windowsでの透過背景に対応

### 主な利用シーン
- ライブデモ・プレゼン
- トレーニング／チュートリアル動画の録画
- 画面共有・配信（OBS等）

### ダウンロード
KeyMouseOverlay.exe（Windows専用）  
インストール不要で、実行するだけで使えます。

### 使い方
- 起動するとカーソル付近に表示され、自動で追従します。
- タスクトレイアイコン（通知領域）から:  
  - **Show/Hide**: 表示のON/OFF  
  - **Auto-hide**: 一定時間操作が無いと自動的に非表示（Off/1s/2s/3s/5s）。入力があれば再表示します。  
  - **Quit**: アプリを終了
- 表示内容: 現在のマウスボタン状態と押下中のキー（例: `Ctrl + Shift + C`）

### 対応環境
- Windows 11: 対応  
- macOS / Linux: 非対応（Windows固有の透過処理を使用）

### 実装
- Python + Tkinter（UI）
- pynput（グローバル入力取得）
- Pystray（トレイアイコン・メニュー）
- 透過はカラキー方式、キー表示は背景プレートで視認性を確保

### ライセンス
- MIT License

---

## English

KeyMouseOverlay is a lightweight Windows overlay that follows your cursor and visualizes mouse and keyboard input in real time. It’s useful for hands-on sessions, live demos, and screen recording/streaming (e.g., OBS).

### Features
- Left/right click highlights and real-time key display (multiple keys and modifiers)
- Short key hold after release for readability
- Auto-hide after inactivity (tray selectable: Off/1s/2s/3s/5s)
- Tray menu for Show/Hide, auto-hide interval, and Quit
- Borderless, always-on-top window that follows the cursor with a small offset
- Transparent background on Windows

### Typical Use Cases
- Live demonstrations and presentations
- Training/tutorial video recording
- Screen sharing and streaming (OBS, etc.)

### Download
KeyMouseOverlay.exe (Windows only)  
No installation required—download and run.

### How to Use
- Launch: the overlay appears near your cursor and tracks it automatically.
- Tray icon (notification area):  
  - **Show/Hide** toggles visibility.  
  - **Auto-hide** chooses inactivity timeout (Off/1s/2s/3s/5s); hides on idle, reappears on next input.  
  - **Quit** exits the app.  
- Displayed: mouse button states and pressed keys (e.g., `Ctrl + Shift + C`).

### Platform Support
- Windows 11: supported  
- macOS / Linux: not supported (relies on Windows-specific transparency)

### Implementation Details
- Python + Tkinter for UI
- pynput for global input capture
- Pystray for tray icon and menu
- Color-key transparency; key labels use a background plate for readability

### License
MIT License

