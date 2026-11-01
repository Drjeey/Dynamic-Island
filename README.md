# Dynamic-Island

A Windows desktop "Dynamic Island" overlay with Lumi, a small AI pet you can talk to.

## Setup

```bash
pip install -r requirements.txt
```

Then run:

```bash
python island7.py
```

To chat with Lumi, add your Gemini API key in **Settings → Lumi and voice** (it's stored in Windows Credential Manager, not in a file), or set it as an environment variable (which takes priority):

```bash
setx GEMINI_API_KEY "your-key-here"
```

## Using it

- **Glance** at the island: while something is live it shows the focus or break countdown, what's playing, Lumi listening, thinking or speaking, or a short confirmation.
- **Click** the island (or focus it and press Enter) to open the dashboard: memory, battery, network, a quick note and Focus. While music plays, clicking opens the player; while a timer runs, it opens the focus panel.
- **Focus:** pick 15, 25, 45 or 60 minutes (or a 5-minute break). When a session ends Lumi offers a break, and today's total is shown in the panel.
- **Click Lumi** to chat by typing. Ask questions, or ask Lumi to do things: "focus for 45 minutes", "add milk to my note", "pause the music", "open Calculator", "how's my battery?".
- **Press Win+Alt+Space** anywhere to open the command bar: search and open apps, ask Lumi a question, `focus 45`, `break`, `note buy milk`, `chat`, `play`, `next`, `settings`, or search the web.
- **Right-click** the island for Settings, Hide for 1 hour, and Quit.
- **Scroll** on the island to change the volume; the level shows in the island.
- **Hover** over Lumi and click the mic to talk. The first click explains where your voice is sent; click again to start. In Settings you can switch to **Live (preview)** voice, a flowing conversation you can interrupt (headphones recommended).
- **Drag** the island to another display; it snaps to the top centre. Choose "Free" in Settings to leave it where you drop it.
- Panels close when the mouse leaves them, or with **Esc**. Use **Tab** to move between buttons.
- The island hides itself while a full-screen app (video, game, slideshow) is in front.

The microphone uses `sounddevice`, which installs on any Python version. If `PyAudio` is installed, SpeechRecognition's own microphone is used instead.

## Code layout

| Path | What it holds |
|---|---|
| `island7.py` | Starts the app |
| `lumi/window.py` | The windows, transparency, click areas, position, watchers and focus timer |
| `lumi/api.py` | What the island and Settings pages can ask Python to do, including the command bar |
| `lumi/config.py` | Paths, defaults and `config.json` |
| `lumi/system.py` | Memory, battery, network, volume and displays |
| `lumi/media.py` | What's playing, from Windows' media controls |
| `lumi/apps.py` | Installed apps and their icons, for the command bar |
| `lumi/hotkey.py` | The global shortcut |
| `lumi/chat.py` | Lumi's conversation with Gemini (typed and standard voice) |
| `lumi/live.py` | Live voice through Gemini Live |
| `lumi/tools.py` | What Lumi can do on the island when asked |
| `lumi/focus.py` | Focus sessions, breaks and the focus log |
| `lumi/credentials.py` | The Gemini key in Windows Credential Manager |
| `ui/` | The island and Settings pages (HTML, CSS, JavaScript) |

## config.json

Created next to `island7.py`. Everything here can also be changed in Settings. Focus history is kept in `focus_log.json` and your note in `notes.txt`; the Gemini key is not stored in any file.

| Key | Meaning |
|---|---|
| `anchor` | `top_center` (snap to the top centre of `monitor`) or `free` |
| `monitor` | Which display, `0` being the main one |
| `geometry` | Window position, used when `anchor` is `free` |
| `auto_start` | `true` to start with Windows (current user only) |
| `hide_in_fullscreen` | `false` to keep the island visible over full-screen apps |
| `scroll_volume` | `false` to stop scrolling on the island from changing the volume |
| `motion` | `system` (follow Windows), `full` or `reduced` |
| `lumi_visible` | `false` to show just the island |
| `hotkey` | The command bar shortcut, default `Win+Alt+Space` |
| `gemini_model` | Chat model, default `gemini-2.5-flash` |
| `voice_mode` | `standard` (listen, then reply) or `live` (Gemini Live, preview) |
| `live_model` | Gemini Live model used in live mode |
| `voice_notice_seen`, `live_notice_seen` | Set after the first mic click in each voice mode shows the privacy notice |
| `onboarding_done` | Set after the getting-started tour |
