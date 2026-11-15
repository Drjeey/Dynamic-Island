# Lumi Island: improvement phases

The roadmap from the product audit, and a record of each phase as it's done. Refs such as `U12` and `F3` point to problems and features in the [audit report](https://claude.ai/artifact/L4SPRYMVe2Zudfhu2W4thX).

| Phase | Focus | Status |
|---|---|---|
| A | Critical fixes | Done, 30 Oct 2026 |
| B | High-impact improvements | Done, 30 Oct 2026 |
| C | Product enhancements | Done, 30 Oct 2026 (Gemini parts tested with a simulated Gemini; see "Not tested yet") |
| D | Experience refinement | Done, 31 Oct 2026 |
| E | Lumi as a companion (activity-driven expressions) | Done, 31 Oct 2026 (E1–E5) |
| P | Choice of AI provider (Gemini, Claude, OpenAI, or any OpenAI-compatible server) | Done, 31 Oct 2026 |
| F | Fixes from the island design critique (Impeccable, 25/40) | Done, 31 Oct 2026 |
| G | More feelings and play: new emotions, interactions, dancing, and Try a reaction in Settings | Done, 31 Oct 2026 |
| H | Claude Code and Codex on the island: run them, follow your own sessions as node states, and Lumi's coding look | Done, 1 Nov 2026 |
| I | Skins: twelve full characters for Lumi, a picker in Settings, and seasonal dress-up | Done, 6 Nov 2026 |

---

## Phase A: Critical fixes (done, 30 Oct 2026)

All changes are in `island7.py` unless noted.

| ID | Item | Refs | What changed |
|---|---|---|---|
| A1 | Hide in full-screen apps | U22, F13 | A watcher hides the window while a full-screen app is in front, and shows it again when that app closes. It uses Windows' `SHQueryUserNotificationState`, plus a check for a non-maximized window covering the island's monitor (for full-screen browser video). It can be turned off with `hide_in_fullscreen` in `config.json`. |
| A2 | Launcher overflow, Lumi mood leak | U7, U8 | Launcher icons are 48px with 12px gaps, inside a 344px island. One `resolveMood()` sets Lumi's mood for every state, so a mood no longer carries over between panels. |
| A3 | Close panels on leave and Esc | U12 | Panels close about 0.6s after the pointer leaves, or on Esc, and never while hovered, while typing a note or while moving through the panel by keyboard. Python checks the pointer position (`_watch_pointer`) while a panel is open, because Windows doesn't reliably tell the page when the mouse slides onto see-through pixels. Focus ticks (`focus_tick`, `focus_end`) no longer replace an open panel. |
| A4 | Separate focus control; red only for errors | U2, U6 | The dashboard has its own Focus button, and the memory ring no longer starts a timer. Focus mode is amber. Memory shows "high" only after a full minute above 90% (sampled every 10s). Lumi never turns red. |
| A5 | Accessibility | U19, U20, U21 | All 14 controls are `<button>`s with `aria-label`s and a visible focus ring. The island acts as a button when compact (Enter or Space opens the dashboard). Listening and speaking show an icon and a word in the island, not just a colour. `prefers-reduced-motion` turns animations off. |
| A6 | Offline icons, native type | U9, U10, U11 | Font Awesome from the CDN is replaced by a built-in SVG icon set. Text uses Segoe UI Variable, with a minimum size of 11px and secondary text in `#A3A3AD`. The browser button shows a generic globe, not the Chrome logo. |
| A7 | Performance | U24 | Hit areas are measured only while something is animating, not on every frame. The unused `backdrop-filter` blur is removed. The shape-shifting animation is replaced by breathing and blinking, which pause after 2 minutes without the mouse nearby. |
| A8 | Mic notice and microphone library | U26, U27 | The first mic click explains where your voice goes; the second click starts listening (`voice_notice_seen` in `config.json`). If PyAudio isn't installed, the mic uses `sounddevice`, which installs on any Python version; `requirements.txt` now lists `sounddevice` in place of `PyAudio`. |

### Also fixed during Phase A

- **Dashboard tiles:** their text overflowed, so the island is now 548px wide and the tiles size to their content.
- **Panels that never closed:** clicking the island gave it keyboard focus, which stopped it from ever closing.
- **Speech bubble:** it now stays up until Lumi finishes speaking, instead of hiding after 6s.

### How it was tested

- **Browser copy of the interface:** colours, closing rules, focus ticks, all 14 controls keyboard-reachable and labelled, no internet requests, no work on every frame, and the dashboard fitting its worst-case text.
- **Python with stand-ins:**
  - the voice notice;
  - the `sounddevice` recorder fed a simulated microphone: speech, silence (times out after 5s) and non-stop speech (capped at 10s);
  - the memory threshold;
  - the focus messages.
- **The real app, driven with the mouse:** hover shows the mic, the island opens the dashboard, the right-click launcher fits, panels close after the pointer leaves, and the island hides in front of a full-screen window and comes back. The app log has no errors.

### Not tested yet

- A real voice conversation (needs a Gemini API key).
- Tab navigation in the real window (only checked in the browser).
- Windows' "Animation effects" setting driving reduced motion.

---

## Phase B: High-impact improvements (done, 30 Oct 2026)

| ID | Item | Refs | What changed |
|---|---|---|---|
| B1 | Split UI and Python | audit §11 | `island7.py` is now a 5-line launcher (so the auto-start entry keeps working). Python lives in `lumi/`: `window.py`, `api.py`, `config.py`, `system.py`, `media.py`, `apps.py`, `hotkey.py`, `chat.py`. The interface is plain files in `ui/` (`island.html/.css/.js`, `settings.html/.css/.js`), served by pywebview's built-in server. The Gemini SDK now loads on first use, which halved import time. |
| B2 | Settings window | F11, U5 | A second, normal window (right-click → Settings) in the Windows 11 Settings style. It follows the light or dark theme. Sections: General (start with Windows, position, display, hide in full screen, scroll volume, motion, shortcut), Lumi and voice (show Lumi, replay tour, Gemini key and model) and About. Every change applies at once (`apply_setting`). The API key is never sent back to the page. |
| B3 | First-run onboarding | F12, U1 | A four-step card under Lumi: click the island; the mic (shown during the step); the command bar shortcut; right-click for Settings. Skippable, saved as `onboarding_done`, and can be replayed from Settings. |
| B4 | Compact live activities | F3, U4 | The idle pill shows the most important live thing: listening/speaking > confirmation or volume > focus countdown (with a progress line) > now playing (artwork, title, animated bars). The old 52px focus panel is gone. Clicking now-playing opens the player; anything else opens the dashboard. |
| B5 | Real Now Playing | F1, U13 | `lumi/media.py` follows Windows' media session (WinRT `GlobalSystemMediaTransportControlsSessionManager`): title, artist, app, play state and artwork. The controls act on that session, falling back to media keys when there's none. The player has a "Nothing playing" empty state and a play/pause button that reflects the state. |
| B6 | Volume HUD | F2, U15 | Scrolling on the island (not on Lumi; can be turned off) changes the volume 2% per notch through Core Audio (`pycaw`) and shows a level bar in the island. One worker thread keeps the audio device open, so changes take about 2 ms. |
| B7 | System panel | U25 | Live refresh every 2s while the dashboard is open (`watch_stats`), and nothing when it's closed. Ping is replaced by a Network tile (Online/Offline, checked every 10s). Battery says "Charging" or "Plugged in". |
| B8 | Command bar and global shortcut | F4, U3, U14 | Win+Alt+Space (changeable) opens a search box in the island from anywhere. Empty, it shows 4 pins with real app icons (your default browser, File Explorer, Terminal, Calculator). Typing searches all 150+ installed apps, including Store apps, plus commands (`focus 45`, `note …`, `play`, `next`, `previous`, `music`, `settings`, `quit`), with a web search as the last option. Arrow keys and Enter work, Esc closes and gives the keyboard back. The hard-coded launcher is removed (right-click is now the menu). |
| B9 | Snap and fit | U17, U23 | In "Top centre" mode the window snaps to the top centre of the chosen display at start-up, after a drag (the drop picks the display) and when displays change. "Free" keeps the old drag-anywhere behaviour. The window's height follows its content, so long replies and the command bar are never cut off. Lumi's replies are capped at 5 lines. |

### Also fixed during Phase B

- **Dragging crashed:** declaring argument types on the shared `ctypes.windll.user32` changed them for pywebview too, and broke its drag code. `lumi/` now uses private `ctypes.WinDLL` copies.
- **Shortcut conflict:** the planned default, Ctrl+Alt+Space, is captured by the Claude desktop app's keyboard hook, so Windows let Lumi register it but the key press never arrived. The default is now Win+Alt+Space, checked to actually arrive, and your `config.json` was updated.
- **Settings opened behind other windows:** the new window is now brought to the front.
- **Slow start-up:** the window took about 15s to appear; it now takes about 2s.
- **Shortcut capitalisation:** shortcuts typed in Settings are tidied ("ctrl + alt + k" becomes "Ctrl+Alt+K").
- **Web search option:** it's always kept as the last command-bar result.

### How it was tested

- **Browser copy of the new interface** (Python replaced by sample data), with no script errors:
  - live-activity priority, focus progress and long-title truncation;
  - the volume readout appearing and disappearing;
  - the music panel's real data and Play/Pause label;
  - live dashboard refresh, including Charging and Offline;
  - the menu;
  - the command bar: pins, results, arrow keys, Enter runs and confirms, Esc closes;
  - the four-step tour;
  - the Lumi-hidden and reduced-motion preferences;
  - the content-height report;
  - everything fitting inside the island.
- **Python checks:**
  - **Settings:** a bad shortcut, a valid shortcut, unknown keys, a bad motion value, preference pushes, and the API key never being returned.
  - **Command bar:** search for `fo`, `focus 45`, `note buy milk`, `calc` and `n`, plus the pins.
  - **App index and icons:** 152 apps, with all 4 pin icons extracted.
  - **Volume:** a change from a worker thread, followed by a change back.
  - **Media:** the media-session API answered.
  - **Shortcut delivery:** a probe confirmed Win+Alt+Space actually arrives.
- **The real app, driven with the mouse and keyboard:**
  - snapped to the top centre at start-up;
  - Win+Alt+Space opened the command bar, took the keyboard, and the window grew (299 → 413 → 430px);
  - typing "calc" listed Calculator with its real icon, and Esc closed the bar;
  - the right-click menu opened Settings in front, and it closed cleanly;
  - scrolling changed the volume (20 → 22 → 20) and showed the readout;
  - dragging the island away snapped it back to the top centre with no errors.

### Not tested yet

- **Now Playing with real music:** nothing was playing during testing, so artwork reading and the controls on a live session are untested.
- **Multiple displays:** only one display was available.
- **"Free" position mode** in the real app.
- **Each Settings toggle clicked in the real window:** they were tested through the same API the page calls.
- **Start with Windows:** left off.
- **Store-app icons other than the four pins.**

### Side effects during testing

- An early test pressed Ctrl+Alt+Space, which opened the Claude desktop app's quick-entry box and may have typed "calc" into it. The test script now types only when the island has the keyboard.

## Phase C: Product enhancements (done, 30 Oct 2026)

No Gemini API key was available, so everything that talks to Gemini was tested against a simulated Gemini. The no-key path was tested in the real app.

| ID | Item | Refs | What changed |
|---|---|---|---|
| C1 | Typed chat | F7, U16 | Click Lumi (not the mic) to open a chat panel in the island. It holds a scrolling conversation that grows to fit (up to 260px of messages), shows a typing indicator, and gives clear errors. The command bar offers **Ask Lumi "…"**: first for anything that looks like a question, otherwise just above the web search. Choosing it opens the chat and sends the question. Voice and typed chat share one conversation (`ChatController.messages`, last 40 messages), using Gemini's chat sessions so Lumi remembers earlier turns. The panel stays open while you type or wait for a reply. Esc or ✕ closes it. |
| C2 | Lumi can act | F9 | `lumi/tools.py` gives Gemini 9 tools: start/stop focus, add to and read the note, control media, what's playing, open an app, system status, and change volume. They're passed as plain Python functions, so the SDK's automatic function calling runs them and lets Gemini answer afterwards. Each action shows a confirmation in the island and a small "success" hop from Lumi. A new "thinking" state (eyes glance up, "Thinking" in the island) covers the wait. |
| C3 | Better focus sessions | F6 | `lumi/focus.py` replaces the old timer. The dashboard's Focus tile opens a **focus panel** with 15/25/45/60-minute choices (remembering the last one), today's total, a 5-minute break and Start. While running, it shows the time and Stop. Breaks turn the compact timer green with the label "Break". When a session ends, a card offers a break; when a break ends, it offers another round. Sessions, including minutes from ones stopped early, are logged in `focus_log.json`. Command bar: `focus 45`, `break`. **Not done:** turning on Windows Do Not Disturb. Windows has no public API for it, and the known workarounds use undocumented internals, so it's left out. |
| C4 | API key in Windows Credential Manager | U26 | `lumi/credentials.py` stores the key with `keyring` (Windows Credential Manager, entry "LumiIsland"). A key found in `config.json` from earlier versions is moved there on start-up and blanked in the file. Settings can save or remove the key but never read it back. `GEMINI_API_KEY` still takes priority. |
| C5 | Streaming voice (Gemini Live), preview | F8 | `lumi/live.py`, switched on in Settings → Voice → Live (preview). The mic streams 16 kHz audio to the Live API and Lumi's 24 kHz voice plays back as it arrives. Interrupting Lumi stops its voice at once. Lumi's tools work here too, and the transcription appears in the speech bubble and the chat history. While Lumi talks, only clearly louder speech is sent, so Lumi doesn't hear itself through the speakers. The session ends on a second mic click or after 30s of quiet. The live model is a setting (default `gemini-2.5-flash-native-audio-preview-09-2025`), because Live model names change often. Live mode has its own first-use privacy notice. |
| C6 | Research | F5, F10, F14 | See "C6 findings" below. Nothing was built. |

### C6 findings

| Idea | What I checked | Finding | Recommendation |
|---|---|---|---|
| **Notification mirroring** (F5) | Asked Windows for this app's notification-listener access status, without reading any notifications | Status **1 (allowed)**: Windows lets this unpackaged desktop app use `UserNotificationListener`. Change events may still need a packaged app, but polling every few seconds works. | Feasible. Build it as an **opt-in** setting with a per-app allow list (notification text is sensitive), showing the app icon and title in the compact island for 4s. A good fit for Phase D or later. |
| **Next meeting** (F14) | Checked whether Outlook is installed, without opening it | Classic Outlook is registered for automation, and the new Outlook app is also installed. | Feasible **without any sign-in** through classic Outlook's local calendar (`pywin32`), but only while classic Outlook is the one set up. The new Outlook and Google Calendar would need Microsoft Graph or Google sign-in and an app registration. Worth a small spike first. |
| **File / clipboard tray** (F10) | Compared with Windows' built-in features | Windows already has clipboard history (Win+V) and drag-and-drop between windows. A tray would add a second place for files with privacy risks (clipboard contents). | **Don't build** unless users ask for it. |
| **Multiple notes** | No user evidence available | The single quick note and the new `note …` command and Lumi tools cover quick capture. Multiple notes would start turning the island into a notes app. | **Don't build yet.** Revisit if people say one note isn't enough. |

### Also fixed during Phase C

- **Panels closing on their own:** a panel opened from another panel (dashboard → focus) can be narrower, leaving the pointer outside it, so it closed immediately. A new panel now stays open until the pointer has entered it once, or for 4s.
- **Dashboard Focus button:** it now opens the focus panel instead of starting 25 minutes straight away, and while a session runs it shows the remaining time.

### How it was tested

- **Python, with a simulated Gemini and temporary files:**
  - **Focus:** start, early stop (logs 2 minutes), completion (adds to today), and a break that keeps your last length.
  - **Tools:** all 9, each with its confirmation.
  - **Conversation:** memory across turns; a tool call during an answer really edits the note; spoken questions get the "short answer" hint; errors start a fresh session; empty input and no key are handled.
  - **Live voice, with a simulated stream:**
    - an input transcription, then a tool call (started a 30-minute focus and sent the result back);
    - streamed audio and the output transcription;
    - an interruption.
    - While Lumi talks, quiet microphone audio is held back and louder speech gets through.
  - **Real SDK:** it builds a valid description for each tool.
- **Credential Manager:** save, read back, remove, and moving a key out of `config.json`, using a separate test entry that was deleted afterwards.
- **Browser copy of the interface:**
  - **Focus panel:** chips, Start, compact focus and break (green, "Break"), the running view, and the end-of-session card starting a break.
  - **Chat:** opening by clicking Lumi, the typing indicator and thinking mood, replies, errors, growth and scrolling, and closing.
  - **Command bar:** the "Ask Lumi" row sending the question into chat.
  - **Feedback:** the success hop and confirmation, and the thinking status.
  - No script errors.
- **The real app:**
  - clicking Lumi opened chat; typing "hello" and Enter showed the reply "Add a Gemini API key in Settings so I can chat!";
  - dashboard → Focus opened the focus panel, which stayed open and closed after the pointer left;
  - the log was clean.

### Not tested yet

- **Anything against the real Gemini service:** answers, tool calls chosen by the model, and Gemini Live. The default live model name is a best guess and may need changing in Settings.
- **Live voice audio on real hardware:** echo handling with speakers is especially uncertain; headphones are safer.
- **A full 15–60 minute focus session in the real app:** the completion path was tested with a 2-second session in Python.

### Side effects during testing

- One real-app run clicked before the island was ready. Two clicks probably landed on the title and menu bars of your VirtualBox Manager window. A third may have toggled its **Properties** details pane, which only changes what's shown. No dialogs were opened or confirmed. The test script now checks that the island's own window is under the pointer before every click.

## Phase D: Experience refinement (done, 31 Oct 2026)

Option A was chosen: Lumi's expressions are drawn in code (SVG + CSS), not Rive.

| ID | Item | What changed |
|---|---|---|
| D1 | Lumi's expressions | Lumi's face is now an SVG with open eyes, happy arcs, closed lids, a mouth, cheeks, floating z's and sparkles. Moods: idle, listening (wider eyes, pulse), thinking (eyes glance up), speaking (moving mouth, no squint), success (happy eyes, cheeks, hop), **puzzled** after errors (head tilt, flatter eyes; never a red body), music (closed happy eyes, gentle sway), focus (calm half-closed eyes), break, and **sleepy**. |
| D2 | Spring motion | One spring curve (`linear()` easing, about 7% overshoot) for every change of shape. Expanding takes 0.42s and collapsing 0.28s, panel contents fade in after the shape settles, and every island button gives a press response. Reduced motion still turns it all off. |
| D3 | Personalisation | Six Lumi colours (Cloud, Peach, Mint, Sky, Lilac, Butter) in Settings → Lumi and voice, with a live preview, applied at once (`lumi_color`). |
| D4 | Delight | **Sleepy:** after 10 minutes with no keyboard or mouse input anywhere (Windows' last-input time), Lumi falls asleep and gives a little stretch when you're back. **Empty note:** a line drawing of a sheet and pencil. **Milestones:** 5 focus sessions in a day and every 7-day streak get one spin with sparkles, each shown once (`milestones_shown`); can be turned off (`celebrations`). |
| D5 | Weekly summary | Once per week (8s after start-up, only if last week has data) a card recaps last week: focus time, sessions, days, this week so far, current streak. "Stop weekly recaps" turns it off (`weekly_summary`, also in Settings); the command bar's `summary` shows it any time. |

### How it was tested

- **Python, with a temporary log:**
  - a 7-day streak was counted correctly;
  - the 5th session of the day triggered its milestone, and the 7-day streak followed at the next finish;
  - neither repeated afterwards, and nothing showed with celebrations off;
  - this-week and last-week totals were right;
  - the weekly summary was offered once per week, every time when asked for, and never when turned off;
  - the colour reached the page's preferences;
  - Windows' last-input time was read correctly.
- **Browser copy of the interface:** all nine expressions were drawn side by side and checked by eye, and both scripts compile.

- **The real app (31 Oct):**
  - with `lumi_color` set to Mint, Lumi was drawn in mint with the new SVG face; set back to Cloud afterwards, it was drawn in the default colour;
  - the dashboard opened with the spring motion and closed after the pointer left;
  - `summary` in the command bar showed the weekly recap card;
  - the log was clean.

### Also fixed during Phase D

- **Weekly recap with no sessions:** it said "No focus sessions last week." with a **Nice** button. The button now reads **OK** when there's nothing to celebrate, and the card suggests how to start a session.

### Not tested yet

- **Sleepy mode in the real app:** it needs 10 real minutes away; the logic and Windows' last-input time were tested in Python.
- **A milestone celebrating live:** it needs a 5th session in a day or a 7-day streak; the rules were tested in Python and the animation in the browser.
- **Clicking the colour swatches in the Settings window:** the colour path itself was checked through `config.json` in the real app.

## Phase E: Lumi as a companion (done, 31 Oct 2026)

Full proposal: [Lumi Companion Proposal](https://claude.ai/artifact/2fWrNWpmGuKjcVi9G6H7UN).

**Finding:** Lumi has no LangGraph. Its agent is one Gemini chat session with the SDK's automatic tool calling, so Lumi only learns about a tool after it has run. **Recommendation:** don't add LangGraph now. Instead:

- run the tool loop in `chat.py` (automatic tool calling off);
- send versioned activity events (`run`, `seq`, `phase`, `tool`, `kind`, `status`, `label`) through a new `lumi/activity.py`;
- drive Lumi's look from a new `ui/lumi-state.js` with three layers (reaction > activity > ambient), minimum durations and a 45s watchdog.

The event format is ready for LangGraph's `custom` stream mode if approval steps or multi-step workflows are ever added.

| ID | Item | Size |
|---|---|---|
| E1 | Bring Lumi to life: glances, float, boop, daily greeting, animation intensity setting | S |
| E2 | Character state manager (layers, priorities, minimum durations, watchdog) | M |
| E3 | Real activity events: own the tool loop, ActivityBus, tool metadata, activity label, chat receipts, streaming replies | M |
| E4 | Voice sync: listening ring and mouth driven by audio level; live voice through the same events | M |
| E5 | Context and polish: cancel a run, waiting state, contextual reactions | S |

### E1–E2 (done, 31 Oct 2026)

| ID | What changed |
|---|---|
| E2 | New `ui/lumi-state.js`, the **character state controller**. Three layers, highest first: reaction (success, puzzled, greet, celebrate; queued up to 2; since E3 only bad news cuts one short), activity (listening, thinking, speaking), ambient (idle, music, focus, break, sleepy). States have minimum on-screen times (thinking 400ms, and so on), so fast events don't make Lumi flicker. Listening and reactions are urgent and show at once. A 45s watchdog clears a stuck thinking state and says "That took too long. Try again?". Every mood change in `island.js` now goes through it: the old `setMood` / `resolveMood` / `puzzledUntil` code is gone, and voice, typed chat, errors, tool confirmations, focus, presence and milestones all report to it instead. |
| E1 | **Signs of life:** a greeting once a day on first open ("Good morning / afternoon / evening", `last_greeting`) and "Welcome back" after being away; a glance to one side every 20–40s when the pointer isn't nearby; a gentle float while breathing; a "boop" squash when you press Lumi; and the eyes glance up when a panel opens or closes. **Animation setting:** Settings → General → Animation is now Follow Windows / Full / Subtle / Off. Subtle drops floating and glances; Off keeps Lumi's colours and faces with no motion. The old "reduced" value counts as Off. |

**Also fixed:** a focus session that ended with a milestone would have played a success hop and then the milestone spin; now only the spin plays.

**How it was tested:**
- **The controller in Node, with a fake clock (20 checks, all passing):**
  - no flicker when events are 50ms apart;
  - minimum durations are kept;
  - listening interrupts at once;
  - reactions win over activity, and activity over ambient;
  - the queue keeps the newest two;
  - the watchdog fires after 45s, but progress resets it;
  - long speech isn't cut off;
  - reset returns to ambient.
- **Browser copy of the interface:**
  - statuses, errors, tool success, milestones, focus, away and back, and typed chat all reach the right expression through the controller;
  - Full, Subtle, Off and Follow Windows set the right classes;
  - boop and the panel glance work;
  - no script errors.
- **Real app:** "Good morning" appeared on first open and `last_greeting` was saved; the controller loaded with a clean log. The same run also confirmed **Now Playing with real media** (artwork, title, moving bars), which earlier phases hadn't been able to test.

**Not tested yet:** the watchdog in the real app (it takes 45 real seconds of being stuck), and glances, which are random and every 20–40s, in the real app.

### E3 (done, 31 Oct 2026)

Lumi now reacts to what is really happening during a request, step by step, instead of guessing from "thinking" and "done".

| Area | What changed |
|---|---|
| Tool loop | `chat.py` runs the Gemini tool loop itself (automatic tool calling off). Replies are read with `send_message_stream`, so each step is known as it happens. At most 5 tool rounds per question, then Lumi must answer in words. |
| Events | New `lumi/activity.py` (`ActivityBus`). Each typed question, voice question or live session is one **run**. Events carry `v`, `run`, `seq`, `phase`, `source` and, where relevant, `tool`, `kind`, `status`, `reaction`, `receipt`, `label`. Phases: run_started, listening, transcribing, understanding, tool_started, tool_finished, responding, run_finished. Events from an old run are dropped. Every run ends with exactly one `run_finished` (ok, error or cancelled), even if code throws. Events never contain prompts, model text or tool arguments; labels come from fixed tables. A page that reloads mid-run picks up from `activity_snapshot()`. |
| Tools | `tools.py` has a `ToolSpec` per tool: action or lookup, a label ("Checking your note…"), a reaction (hop or nod) and, for lookups, a receipt. `LumiTools.run()` reports start and finish for typed chat, voice and live voice alike. Tools that can't do what was asked now raise `ToolFailed` (no app match, no focus running, unknown media action, volume failure), so Gemini and the user both hear about it. |
| Lumi's face | New looks: attentive (request received), checking (a lookup: eyes scan), working (an action: busy bob), replying (mouth moves while a typed answer streams), nod (a lookup or small action succeeded), reconsider (a tool failed: small head shake). Bad news (reconsider, puzzled) now cuts a playing success hop short instead of waiting behind it. A failed run shows puzzled only once. |
| Island | While the island is compact, it shows what Lumi is doing ("Starting focus…", with a search or spinner icon); an action's confirmation then appears as a short toast, and a failure as a speech bubble. |
| Chat panel | The "•••" line shows the current step ("Checking your note…"); each tool leaves a receipt line (✓ "Focus started for 25 minutes", ✗ "No focus session is running"); the answer streams in word by word. |

**How it was tested:**
- **Python, with a simulated streaming Gemini (5 scenarios, all passing):**
  - a tool that works, a tool that fails, then a streamed reply: exact event order, seq 1..n in one run, the right receipts and reactions, the failure sent back to Gemini, `chat_delta` matching the final reply, and no question text in events;
  - Gemini throwing: the run ends with one `run_finished: error`, and the session is reset;
  - a lookup inside a voice run: `kind=lookup`, the fixed receipt, no chat streaming;
  - a model that keeps asking for tools stops after 5 rounds;
  - the bus: stale events dropped, a new run cancels the old one, errors in the block finish the run as error, snapshot.
- **The controller in Node:** the 20 E2 checks plus 4 new ones on interrupting reactions (one old check updated for the new rule).
- **Browser copy of the interface, fed the same events Python sends:**
  - compact island: attentive, then thinking, working, success (with toast), reconsider, then idle; labels change with each tool; the stale event never shows;
  - chat panel: labelled working line, ✓ and ✗ receipts in order, streamed reply, replying mouth, checking for lookups;
  - a failed question shows puzzled exactly once.
- **Real app (guarded clicks only):** restarted on the new code with a clean log; a typed question with no Gemini key runs as an activity run and ends with one error and a puzzled Lumi; Esc closes the panel.

**Not tested yet:** real Gemini answers with real tool calls, and voice and live voice runs. There is no API key on this PC; the event path for them is covered by the simulated tests above.

### E4 (done, 31 Oct 2026)

Lumi's listening ring and talking mouth now follow real sound instead of looping.

| Area | What changed |
|---|---|
| Levels | New `lumi/levels.py`: a `LevelMeter` turns audio loudness (RMS) into 0–1 on a log scale and sends `level` messages (`{kind: 'mic' or 'voice', value}`) at most 12 times a second, only while audio is flowing, plus one `end` when it stops. The loudest moment between updates is kept, so short syllables still show. No audio or words are sent to the page. |
| Standard voice | While recording, the mic level drives the ring. The room's own noise, measured in the first 0.3 s, doesn't move it. Windows text-to-speech reports when each word starts but not how loud it is, so each word opens the mouth, which then nearly closes until the next word. |
| Live voice | The ring follows your mic while Lumi listens. The mouth follows the audio the speakers are actually playing, so it is closed during pauses. The session now reports through the activity events: `listening`, `responding` once per turn, and `listening` again after the turn or the moment you interrupt. An interruption stops the voice and the mouth at once. |
| Page | Levels set `--mic` and `--voice` on Lumi (registered CSS properties with an 80ms ease), plus `data-mic` / `data-voice` attributes that mood changes don't touch. With levels, the ring grows from 1px to 12px and gets stronger; the mouth opens from nearly closed to fully open. Without levels (an older mic path), or if levels stop arriving for 0.6 s, the old loops play instead. With Animation set to Off, levels are ignored. |

**How it was tested:**
- **Python (22 checks, all passing):**
  - the meter: scale, noise floor, at most 12 updates a second, short peaks kept once, a single `end`, word pulses;
  - standard-voice recording with a fake microphone and clock: still for room noise, large for speech, ends when recording stops;
  - **the real Windows speech engine, run silently: it reported 5 word starts for "one two three four"**;
  - live voice with a fake Gemini Live session and speakers: playback level, the event order (responding, listening on interrupt, responding, listening), the mouth stopping within 150ms of an interruption (measured: 0ms), and "listening" shown at that moment.
- **Browser copy of the interface:** without levels the old loops run; with them the ring goes from 2.1px (quiet) to 10.9px (loud); the mouth scales from 0.5 × 0.25 (silent) to 1 × 1.05 (loud) and follows values in between; word pulses open then settle to 0.15; a lost `end` falls back after 0.6 s; levels survive mood changes; Animation Off ignores them. The browser pane was hidden, so transitions were finished instantly (Web Animations API) to read the final styles.
- **Real app:** restarted on the new code with a clean log. The provider tests (46) still pass.

**Not tested yet:** speaking to Lumi in the real app (it needs your microphone, and live voice needs Gemini, which was timing out), and how the ring looks with your own mic's loudness. If it's too lively or too calm, `QUIET` and `LOUD` in `lumi/levels.py` set the range.

### E5 (done, 31 Oct 2026)

You can stop Lumi mid-request, Lumi has a "waiting for your answer" look ready for future approval prompts, and it reacts quietly to music and breaks.

| Area | What changed |
|---|---|
| Stop | **Esc**, the chat's send button (it becomes **Stop** while Lumi works), or a new **stop button** in the compact island stops the request. The run ends at once as `cancelled`: Lumi goes back to normal with no reaction, the chat frees up immediately and shows "Stopped", and any part of the reply that had already arrived stays, faded. Esc with nothing running closes things as before. |
| Behind the scenes | `ActivityBus.cancel()` ends the open run and flags it (`Run.cancelled`). The work stops at its next safe point (`run.check()`): while the reply streams, before each tool round, before each tool (a tool requested after Stop never runs), and every 0.1 s while recording. Speech stops between words. Turning the mic off ends a live session as `cancelled`. A reply that arrives after Stop is dropped. The stopped request's conversation is set aside, so the next question starts a fresh one at once instead of sharing it. A newer request also cancels an older one. |
| Waiting | The `needs_input` phase shows the waiting look (Lumi looks at you, blinks slowly, sways a little) with the question as the island label, and has no time limit. Nothing uses it yet; it's ready for approval prompts. |
| Small reactions | Music starting gets a nod; a new track makes Lumi glance up at the title; a focus break starting gets a little stretch. They happen only when Lumi isn't busy, and at most once every 20 s. After any request, Lumi goes back to what's true on the PC (music, focus, break, sleepy). |

**How it was tested:**
- **Python (24 checks, all passing):**
  - the bus: cancel with nothing running, exactly one `run_finished` (cancelled), late events dropped, `check()` raising, no run left open, a new run cancelling the old;
  - typed chat cancelled while the reply streams: the result says cancelled, nothing is streamed after Esc, and the conversation is reset;
  - a tool requested after Esc never runs;
  - voice cancelled while recording: stops at the next 0.1 s block, with no error and the ring ended;
  - speech stopping at the next word;
  - live sessions ending by mic-off (`cancelled`) and by idle timeout (`ok`);
  - the window's `cancel_run` (hush, set the conversation aside, stop live voice);
  - Stop then an immediate new question: it gets a fresh conversation, and the stopped question's late reply doesn't disturb it.
- **Earlier suites still pass:** providers (46), E4 (22; I made its fake speaker drain in 20ms steps because one check was timing-dependent), and the state controller in Node.
- **Browser copy of the interface:**
  - chat: Stop during a tool frees the chat at once and shows "Stopped", and the next question works;
  - compact island: the stop button appears only during a request (the island widens to 196px; the button sits inside the island and clears the label) and stops it;
  - Esc: cancels while a request runs and closes the chat when nothing runs; no reaction on cancel;
  - waiting: the look, the label and the stop button;
  - music: one nod, nothing again within 20 s, a glance on track change; a break starting gets one stretch; the break look returns after a request.
- **Real app:** restarted on the new code with a clean log.

**Not tested yet:** stopping a real request in the real app (no provider was answering during testing), and seeing the new stop buttons on screen: the browser pane was hidden, so layout was checked by measurement rather than by eye.

## Phase P: Choice of AI provider (done, 31 Oct 2026)

Lumi is no longer tied to Gemini. Settings → Lumi and voice → **AI model** chooses who answers: **Gemini**, **Claude**, **OpenAI**, or **Other (OpenAI-compatible)**. "Other" covers Ollama, LM Studio, OpenRouter, Groq and similar servers.

| Area | What changed |
|---|---|
| Provider layer | New `lumi/providers/`: one adapter per provider (`gemini.py`, `claude.py`, `openai_compat.py`), each offering the same small interface, `send(message, on_text) -> (text, tool calls)`. `chat.py` keeps one tool loop for all of them, so activity events, reactions, receipts and streaming work the same whichever provider answers. Each SDK is imported only when its provider is chosen. |
| Tools | Tool schemas are built from the same Python methods (names, type hints, docstrings) for every provider. Arguments are checked against the schema before a tool runs; wrong ones are sent back to the model as an error instead of running the tool. |
| Claude | Official `anthropic` SDK; default model `claude-opus-5-5`, with Sonnet 5.5 and Haiku 5.5 suggested in Settings. Effort `low` on current models (short answers come back faster). Server-side refusal fallback (`fallbacks: "default"`) on models that support it. A refusal ends the run with "I can't help with that one." Thinking blocks are passed back unchanged, tool inputs stream and are checked before use, and a cut-off tool call is never run. |
| OpenAI and others | Official `openai` SDK with an optional server address (default `http://localhost:11434/v1`, Ollama). The key is optional for "Other". If a local model can't call tools, Lumi keeps chatting without them. |
| Keys | One Windows Credential Manager entry per provider. Environment variables still win: `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`. The existing Gemini key is kept as it is. |
| Voice | Standard voice works with every provider. Live voice is Gemini Live, so it's offered only with Gemini; with another provider the mic uses standard voice, and Settings says so. The first-use privacy notice and the About page now name the provider your words go to. |
| Timeouts | Every provider now has a 60-second request timeout, so a stalled service ends the request with an error instead of leaving Lumi thinking. |

**Also fixed:** hidden Settings pages were still showing, because a CSS `display` rule overrode the `hidden` attribute. All three pages appeared stacked, and the Remove key button couldn't be hidden.

**How it was tested:**
- **Python, with fake SDK clients for each provider (46 checks, all passing):**
  - tool schemas and argument checks;
  - Claude: the exact request (fallback beta on Opus 5.5 and none on Haiku, effort, tools with input streaming, no sampling parameters), streamed text, tool calls, all tool results in one turn with `is_error` on bad arguments, thinking blocks kept, refusal, a cut-off tool call, unreadable tool JSON retried, and blocks from a declined model left out after a mid-answer fallback;
  - OpenAI-compatible: tool calls rebuilt from streamed pieces, broken JSON, tool messages, and a model without tool support;
  - Gemini: function calls (float minutes made whole) and streamed text;
  - the shared tool loop: events in order, bad arguments never run, the tool-round cap resetting the session, a refusal, and errors naming the provider;
  - choosing a provider: missing keys, a local server with no key, an unknown provider falling back to Gemini, and the privacy-notice wording.
- **Browser copy of Settings:** switching providers swaps the key row, the model and its suggestions, and the server row (Other only); live voice is disabled for non-Gemini providers, with an explanation; keys save per provider.
- **Real app:** restarted on the new code with a clean log.
- **Real Gemini (your saved key, model `gemini-3.8-flash`):**
  - one request reached Gemini, which asked for the `start_focus` tool through the new path;
  - the next requests timed out on Google's side (504 DEADLINE_EXCEEDED, even for "Say OK."), which is what led to adding the timeouts.

**Not tested yet:** a full real answer from any provider (Gemini was timing out on Google's side during testing; there are no Claude or OpenAI keys on this PC), and the chat panel in the real app with a provider other than Gemini.

## Phase F: Fixes from the island design critique (done, 31 Oct 2026)

An Impeccable critique of `ui/island.html` scored the island **25/40 (Acceptable)**, with 3 major and 2 minor issues. The report is saved in `.impeccable/critique/`. You chose to fix all five, to make Lumi peek as a setting, and to keep short labels in a steady pill.

| Issue | What changed |
|---|---|
| **P1: labels didn't fit the pill** (they wrapped and clipped with Stop showing) | Shorter labels (verb + noun: "Reading note…", "Adjusting music…", "Checking PC…"; "Thinking…" instead of "Understanding…"). The label is always one line, ending in "…" if it's too long. The pill is now sized to the measured label plus the Stop button (140–280px), instead of a fixed width. |
| **P1: the pill jumped during a request** (status, then a toast, then status again, with Stop vanishing) | While a request runs, receipts appear inside the same status shape ("✓ Focus started for 25 minutes"), so Stop stays. Lookups add no toast, since what Lumi looked up is in its answer. The last action is confirmed once, when the request ends. |
| **P1: Lumi covered your work all day** | New setting, Settings → Lumi and voice → **When Lumi is quiet**: *Peek from under the island* (the new default) or *Always show in full*. Peeking tucks Lumi behind the pill with only its eyes showing. It comes out for anything it has to say (a mood change, a reaction, a bubble, a card, a request) or when the pointer comes near the island or Lumi, and tucks back 1.5 s after things are quiet. In the real app, 32px of Lumi now shows below the island, against 66px before, and the window's clickable area shrank with it. |
| **P2: errors were dead ends** | Chat errors now carry their way out: **Open Settings** (missing key, can't connect) or **Try again**. Python says which (`action: settings / retry`). Voice and live-voice errors that only Settings can fix, and a shortcut that can't be registered, now show a clickable card with Open Settings instead of a vanishing bubble. When a request gets stuck, the watchdog stops it and offers **Try again** (asks the question again, or listens again). |
| **P2: keyboard, screen reader and contrast** | The island's spoken label now describes what's showing ("Now playing: Blue in Green by Miles Davis. Press Enter for the player"; "Focus, 24:59 left. Press Enter for the timer"). The command bar announces the highlighted result (`aria-activedescendant`, `aria-selected`, a correct `aria-expanded` and `aria-controls`). The focus chips are one Tab stop, and the arrow keys move the choice. The chat and command fields show a focus ring. White text on blue now uses `--blue-strong` `#2E6BE0` (4.9:1; it was 3.2:1). The "✕" and "⚠" text characters, and the "✓"/"✕" marks in receipts, are now drawn icons. |

**How it was tested:**
- **Python:**
  - 6 new checks: label length, "Thinking…", the new setting (default, saving, rejecting bad values, sent to the page), and the Settings action on a missing-key error;
  - every earlier suite still passes: providers 46, E4 22, E5 24, and the state controller in Node.
- **Browser copy of the interface:**
  - all 11 labels fit on one line (17px tall) without touching Stop;
  - for a whole request the pill keeps one shape, and Stop is never hidden;
  - the receipt shows inside the pill, a lookup adds no toast, and there's one confirmation at the end;
  - peek tucks in after 1.5 s (top 27px) and comes out for the pointer, a bubble and a reaction; "Always" keeps Lumi out;
  - the Settings card and its button work, and chat errors show Open Settings or Try again;
  - the spoken label for music, the command-bar announcements and the arrow keys on the chips all work;
  - the Next button is `#2E6BE0`.
- **Design detector** (re-run on `ui/island.html` and `ui/settings.html`): the contrast failure is gone. What's left is the three dashboard-tile warnings (false positives: their contents are centred in a fixed 76px height) and the same kind of warning on Settings' existing position switch, which wasn't touched.
- **Real app** (state read over a local DevTools port, no clicks): Lumi peeks with its eyes at 42–54px, just under the pill's edge at 45px. The log is clean, and the app was restarted without the port afterwards.

**Not tested yet:** how the peek looks and feels on your screen over a day; the Try again and Open Settings buttons with a real provider; and a screen reader actually reading the new labels.

## Fix: "the AI isn't working anymore" (31 Oct 2026)

**Cause:** nothing in Lumi was broken. The saved model `gemini-3.8-flash` was overloaded at Google: "503 UNAVAILABLE … high demand", and earlier 504 timeouts. The key is valid, and the model exists. A check of the model list also showed that Lumi's built-in default, `gemini-2.5-flash`, has been retired (404), so a fresh install would have failed too.

| Change | Details |
|---|---|
| Your model | Switched to **`gemini-3.5-flash`** (your choice), which answered at once. You can change it back in Settings. |
| New defaults | The default model is now `gemini-3.5-flash`. Settings suggests `gemini-3.5-flash`, `gemini-3.8-flash` and `gemini-3.5-flash-lite`. The live-voice default is still available and unchanged. |
| Backup model (your choice) | New setting, **Backup model**, in Settings → AI model (Gemini only); the default is `gemini-3.5-flash-lite`, and leaving it empty turns it off. If the chosen model is busy (rate-limited 429, overloaded 500/503/504, or no answer within 25 s), Lumi asks the backup the same question, carrying the conversation over. The rest of that conversation stays on the backup; the next conversation tries your model first again. Lumi shows "Trying another model…", which also counts as progress, so the 45 s watchdog doesn't give up during the switch. Other errors, such as a bad key, a retired model or a bad request, are shown as before with their buttons, and Stop is never retried. |
| Music buttons | Fixed a crash ("A coroutine object is required"). Windows' media calls return a Windows async operation, not a Python coroutine, so they're now awaited inside one. If an app ignores the request, the keyboard media key is sent instead. |

**How it was tested:**
- **Offline checks (12 new, all passing):**
  - a busy model hands over to the backup with the history, and the conversation stays there;
  - 429, 504 and network timeouts count as busy; 400, 401, 403 and 404 don't;
  - Stop is never retried; with no backup set, the error is shown;
  - play/pause works, and an ignored "next" falls back to the media key.
- **Earlier suites still pass:** providers 46, critique fixes 6, E5 24.
- **Real Gemini, through Lumi's own chat code, with a pretend focus timer:**
  - with your settings, it answered "hello there";
  - with `gemini-3.8-flash` (busy), it switched at 27.5 s with "Trying another model…" and the backup answered at 34.5 s.
- **Real app:** restarted on the new code with a clean log.

**Not tested yet:**
- the music buttons with real music playing;
- typing a question in the real chat panel. Answers came back, but Google was slow: 35 s for a short reply.

## Phase G: More feelings and play (done, 31 Oct 2026)

You chose eight new emotions, five new ways to play with Lumi, and a way to try out reactions that normally happen only now and then: buttons in Settings that play on the real Lumi.

**New emotions and what triggers them**

| Emotion | Looks like | Happens when |
|---|---|---|
| Surprised | Wide eyes, a little "o", a jump | You summon the command bar (at most every 20 s, and only when Lumi isn't busy) |
| Shy | Blushes, looks away, small head tilt | Your pointer rests on Lumi for 2.5 s, or you say something nice in chat ("thank you", "you're the best"…) |
| Sad | Droopy eyes, a sigh, slightly muted colour (2.2 s) | You stop a focus session early, or two requests fail in a row (instead of a second "puzzled") |
| Giggle | Happy eyes, quick mouth, a bouncy wiggle | You double-click Lumi |
| Happy | Happy eyes, rosy cheeks, a contented wiggle | You pet Lumi (rub the pointer back and forth over it) |
| Dizzy | Spinning eyes and a wobble | You shake the island (drag it quickly back and forth) |
| Yawn | Closed eyes, a big yawn and a stretch | Before dozing off when you're away, and now and then before Lumi goes still after a quiet spell (Full animation only, at most every 20 minutes) |
| Notice | Perks up, looks at the island, a small drawn "!" | Lumi has something new for you: a weekly summary, "break's over", or a voice notice. Windows notifications from other apps aren't read: notification mirroring is still an optional extra, not built. |
| Thinking in chat | Thought dots drift up beside Lumi | While Lumi thinks or looks something up (typed chat and voice) |

**New interactions**
- **Dance:** while music is playing, Lumi bobs to a steady beat. It dances in the background look, so it also dances while peeking. It's calmer with Subtle animation and off with Animation Off. The beat is fixed, not taken from the song.
- **Pet:** rub the pointer back and forth over Lumi; it gets happy.
- **Double-click:** Lumi giggles. A single click still opens chat, now after a 0.26 s wait to tell the two apart.
- **Press and hold:** Lumi squishes, and hops when you let go. A hold never opens chat.
- **Shake the island:** a quick back-and-forth drag makes Lumi dizzy. Python spots it from the window's drag positions: 4 turns within 1.2 s, at least 8px each way, once every 3 s.

**Try a reaction** (Settings → Lumi and voice): buttons in three groups.
- **Reactions (14):** Greet, Happy, Giggle, Surprised, Shy, Sad, Dizzy, Yawn, Notice, Done, Nod, Rethink, Puzzled, Celebrate.
- **While working (7):** Listening and Speaking (with made-up sound levels so the ring and mouth move), Thinking, Checking, Working, Replying, Waiting.
- **Moods (5):** Dancing, Music, Focus, Break, Sleepy.

Each one plays on the real Lumi for about 2.5–3.5 s, with its name shown in the island. Lumi comes out of peeking for it, and a try-out never plays over a real request.

**How it was tested:**
- **Python (9 checks):**
  - shake detection: a normal drag, a quick back-and-forth, the 3 s pause, tiny jitters, a slow back-and-forth;
  - the Settings try-out API (sends the reaction; refuses unknown names; 26 entries);
  - stopping focus early sends `stopped` and `kind`.
- **Node:** all 8 new reactions have timings, and the earlier state-controller checks still pass.
- **Browser copy of the interface:**
  - all 26 try-outs apply the right look without peeking; the "!" and thought dots show (opacity 1); Listening and Speaking get moving levels;
  - double-click giggles without opening chat, and a single click opens chat;
  - holding squishes, then hops on release without opening chat; petting gives happy; resting the pointer gives shy;
  - the shake message gives dizzy;
  - dancing starts with music, stops on pause, and stays off with Animation Off;
  - focus stopped early gives sad, going away gives a yawn, and two failures in a row give puzzled then sad;
  - a compliment gives shy, the weekly summary gives notice, and the command bar gives surprised (when Lumi isn't busy).
- **Real app** (over a local DevTools port, no clicks, no screenshots): the giggle try-out played (`mood-giggle`, "Giggle" in the island, Lumi out of peeking, back to normal after), and the log was clean. Restarted without the port afterwards.

**Not tested yet:** how each emotion looks on your screen (that's what Try a reaction is for), petting and shaking with a real mouse, and dancing over a long listening session.

## Phase H: Claude Code and Codex on the island (done, 1 Nov 2026)

You asked for Lumi to run Claude Code and Codex from the island, to show what a session is doing as node states, and for a new expression: Lumi in glasses, thinking, while they run.

**Where the tools are:** neither is on PATH. Lumi finds the ones the desktop apps install: the newest `claude.exe` under `%LOCALAPPDATA%\Claude-Data\…\claude-code\<version>\`, and `codex.exe` under `%LOCALAPPDATA%\OpenAI\Codex\bin\`. PATH and npm installs are checked first.

| Part | What it does |
|---|---|
| **Run from the island** | New **Agents** panel (dashboard tile, the compact island while an agent works, or the command bar). Pick Claude Code or Codex, a folder, and **Can edit files** or **Read only**, then type the task. Claude Code runs as `claude -p … --output-format stream-json` (edit: `--permission-mode acceptEdits`; read only: only Read, Grep, Glob and web tools). Codex runs as `codex exec --json` with the `workspace-write` or `read-only` sandbox. Neither can ask for approval when run like this, so a step it isn't allowed to take shows as a failed node. **Stop** ends the agent and everything it started. |
| **Command bar** | `claude <task>` and `codex <task>` start straight away in the last folder (or open the panel with the task filled in if no folder has been chosen yet); `agents` opens the panel. |
| **Your own sessions** | Sessions you run yourself (terminal, Claude desktop, Codex desktop) show up too. Lumi reads the logs both tools keep on this PC: `~/.claude/projects/*/*.jsonl` and `~/.codex/sessions/<date>/rollout-*.jsonl`, only files written in the last 20 s, every 1.5 s. Codex's built-in reviewer logs are skipped. Nothing is sent anywhere. Off switch: Settings → General → **Show Claude Code and Codex sessions**. |
| **Node states** | Each session is a chain: your task → each step (Thinking, Reading *file*, Editing *file*, a command, Searching files, Searching the web, a tool, Starting a helper, Updating the plan) → Done / Stopped / problem. Nodes are blue and pulsing while running, grey when done, red if failed; repeats merge ("Editing island.js ×9"). The compact island shows the current step and the last 7 nodes as dots; the panel shows the full chain, with tabs when several sessions are going. |
| **Lumi's coding look** | While any agent works, Lumi wears round reading glasses, reads along a line, looks up to think (thought dots), and bobs gently. A new session gets a "notice"; finishing gets a hop, a problem gets "puzzled". **Coding** is in Settings → Try a reaction → Moods. |
| **Fixable failures** | Known errors become a next step, e.g. "Claude Code's own login has no credit. In a terminal, run claude and type /login." |

**Something to know:** on this PC the standalone `claude.exe` answers **"Credit balance is too low"**. The Claude desktop app signs in its own way; the command-line tool outside it uses a login with no credit. Until you run `claude` in a terminal and `/login` with your subscription, runs from the island will stop with that hint. Following your own Claude Code sessions isn't affected, and Codex works.

**How it was tested:**
- **Parsers on real logs:** this Claude Code session's own log (prompt, edits merged into one node, a running command), a real Codex desktop session (commands, an image, answers, Done), and the Codex and Claude probe outputs.
- **Real runs through the manager:**
  - Codex, read-only, "list the files here": prompt → Running a command (`Get-ChildItem -Name`) → answer → Done in 15 s;
  - Claude Code: ends as a problem with the login hint;
  - Stop during a Codex command: ended as Stopped 0.5 s later;
  - bad input (no task, missing folder, unknown agent) gives a message;
  - the watcher found this live session, with its title and folder;
  - the command bar offers `Ask Claude Code: "fix the bug"`.
- **Browser copy of the interface** (with a pretend Python side):
  - panel opens with the right defaults; folder picking, mode and agent switches work; the run is sent with folder, task and mode;
  - nodes appear live with icons and states;
  - the pill shows `Codex · Reading settings.css` with dots, then "is done" (green) or "hit a problem" (red), and clears after 6 s;
  - Lumi wears the glasses while it runs (screenshot), and in the try-out;
  - tabs switch between sessions; Stop only shows for sessions started from Lumi;
  - the dashboard fits the new tile (button tiles 64 → 58 px, no overflow).
  - Fixed during testing: the panel shifted 23 px sideways when the task field took focus while the island was still growing.
- **Real app:** started on the new code with a clean log (only the existing comtypes warning).

**Follow-up, same day: testing a Claude Code run after you logged in.**
- Runs still stop at once with "Credit balance is too low", in both read-only and edit mode.
- `claude auth status` shows why: the CLI is signed in with `authMethod: api_key` ("/login managed key"). That's an Anthropic Console organization billed per use, and it has no credit. It isn't your Claude subscription.
- **To fix:** in a terminal, run `claude`, type `/logout`, then `/login`, and choose the **Claude account with subscription** option (not Anthropic Console).
- Also fixed: when Lumi is started from inside a Claude desktop session (as it was during testing), the agent no longer inherits that session's private endpoint and sign-in settings (`ANTHROPIC_BASE_URL`, `USE_LOCAL_OAUTH`, `CLAUDE_AGENT_SDK_*`). It wasn't the cause here, but it would have sent runs to the wrong place.

**Not tested yet:**
- how it looks on your screen over a real working session;
- an island-started Claude Code run that succeeds (needs the subscription login above);
- a Codex run in "Can edit files" mode that changes files;
- several agents at once over a long time.

## Fix: critical and high bugs from the functional test (6 Nov 2026)

A functional test of the whole app found 1 critical and 7 high bugs. All eight are fixed. The medium and small ones from that test are not.

| # | Bug | Cause | Fix |
|---|---|---|---|
| 1 | **Settings couldn't load:** empty dropdowns, every switch off, no messages | pywebview runs each reply beside a global `var keys`; `settings.js` also declared `keys`, so the browser rejected every reply, and pywebview still reported success | Renamed it `keyInfo` (`ui/settings.js`) |
| 2 | With no saved folder, the command bar started an agent in Lumi's own folder, able to edit files | `Path('')` means the current folder, so the check always passed | `lumi/api.py` opens the panel; `AgentManager.run` refuses an empty folder |
| 3 | API errors in sessions you run yourself (rate limit, no credit, server trouble) stayed "running" for 10 minutes | Only `end_turn` ended a turn. Claude Code writes errors as its own `stop_sequence` lines | A line flagged as an API error ends the session as failed, with its hint. A plain `stop_sequence` line ("No response requested.") ends it as finished |
| 4 | Prompts starting with pasted text were ignored in sessions you run yourself | Anything starting with `<` counted as bookkeeping | New `_asked()` in `lumi/agents.py` keeps your words, or the paste if that's all there is |
| 5 | The Agents panel never closed by itself | `focusKeepsOpen()` excluded the chat box but not the agent box | Excluded it too; the box keeps the panel open only while it has text |
| 6 | Replies still streaming were cut off at 45 s | Streamed text didn't count as progress for the watchdog | Each piece of text restarts it. A reply that really stalls still gets the card after 45 s |
| 7 | Dragging across text moved the window | `easy_drag=True` drags from anywhere, and the drag class covered the whole island | `easy_drag=False`. Notes, chat, agents and the command bar now drag by their headers (the command bar has none). The compact island, Lumi, and the dashboard, music, focus and menu panels drag as before |
| 8 | Two agents could start at once, leaving one that Stop couldn't reach; a finished run could block the next with "still working" | The check and the start were separate steps, and a process still exiting counted as working | `_starting` holds the place until the process exists; a session that has reported its end no longer blocks; the form ignores a second Enter |

**A mistake caught while fixing #3:** the test report called these sessions stuck, and the first fix marked `stop_sequence` as finished. That made a Claude Code "no credit" failure show as Done. A check of real logs then showed that every `stop_sequence` line is written by the tool itself, and most are errors, so #3 was changed to the fix above.

**How it was tested** (on scratch copies of the fixed code, with a separate `config.json`):
- **Python (new checks, all passing):** an empty folder from both paths; API errors in both spellings; empty turns; pasted prompts; three submits at once start one agent; a lingering process doesn't block; a failed start doesn't block the next.
- **Real logs, replayed:** 40 Claude Code logs with no crashes, none older left "running", and 26 prompts with pasted text started a clean turn.
- **The real app, driven over a local DevTools port with simulated mouse events:**
  - Settings shows saved values, shows errors, gets replies and has no script errors;
  - text in the note, chat and agent box doesn't move the window, while the island, Lumi, the dashboard and panel headers do;
  - a real Claude Code run shows as failed with the login hint, and Codex starts straight after and finishes;
  - double Enter sends one run;
  - streaming past 52 s isn't cut off, and a stalled reply gets the card at 45 s;
  - no script errors.
- **One check failed once:** in one full run the Agents panel stayed open. It closed in the other full run and 6 out of 6 repeats, including right after Settings. The repeats show the real cursor crossing the island at times, and a cursor resting on the panel keeps it open on purpose. That's the likely cause, but it isn't proven.

**Not tested yet:** dragging and selecting text with a real mouse; a successful Claude Code run (the account still has no credit); the folder picker. Voice, multiple displays and hiding in full-screen apps weren't part of this test.

## Phase I: Skins (done, 6 Nov 2026)

You chose full characters (shape, details and accessories, not just a hat) in all four themes. Each is drawn in code, so it stays sharp and needs no image files.

| Theme | Skins |
|---|---|
| Original | Classic (the only skin that uses the Colour setting) |
| Animals | Cat, Bunny, Bear |
| Tech | Robot, Pixel, Hologram |
| Nature | Cloud, Slime, Sprout |
| Seasonal | Santa hat, Pumpkin, Party |

| Area | What changed |
|---|---|
| Moods | Moods used to repaint Lumi's body directly. They now set one variable, `--body`, which the body and the ears, tails and drips all use, so everything tints together and returns to the skin's colour afterwards |
| Drawings | `ui/lumi-skins.js` holds each skin's art, used by both the island and Settings, so the picker shows exactly what you'll get. `ui/lumi-skins.css` holds the shapes. Names and colours are in `SKINS` in `lumi/config.py` |
| Drawing rules | Art keeps clear of the eyes, the glasses and the "!", and fits the 15px under the island. Nothing outside the body is see-through, because the window's transparency is a colour key and soft edges would fringe. Details on the body (pumpkin ribs, cat stripes) are a shade of the current colour, so they suit every tint |
| Settings | Lumi and voice → **Skin**: a tile for each skin. Picking one applies at once, and Lumi comes out for a happy wiggle so you can see it even while peeking. With any skin but Classic, the Colour row is disabled and says why. The small Lumis in the command bar and Agents panel take the skin's colour |
| Seasonal | **Dress up for the season** (off by default): Pumpkin 24–31 October, Santa hat 18–26 December, Party 31 December–1 January. Your own skin comes back afterwards, and the change happens within a minute even if Lumi is left running |

**How it was tested** (a scratch copy of the app; your `config.json` wasn't touched, and with no `skin` saved you start on Classic):
- **Every skin in 13 moods, on one contact sheet, checked by eye.** This caught two things, both fixed: fixed-colour details clashed with mood tints (orange pumpkin ribs on blue), and the hologram's floor tilted with Lumi's head.
- **The real app, driven over a local DevTools port:** ears tint with the body and the skin's colour returns; a mood change never removes the skin; picking a skin dresses Lumi at once and brings it out; the Colour row disables and explains itself; an unknown skin is refused; back to Classic restores your colour and removes the accessories; the seasonal switch saves and leaves today alone; a reload keeps the skin; no script errors.
- **Real views:** peeking (ears and hats tuck behind the island), full view, the coding glasses, and a speech bubble.
- **Python:** the first and last date of each season and the days either side; a seasonal skin overriding the chosen one; a bad saved skin falling back to Classic.
- **Design detector:** nothing new to fix. The padding warnings are on older parts of the UI, and the stripes advisory is the hologram's scanlines, which are deliberate.

**Not tested yet:** how the skins look on your own desktop, against your wallpaper (the sheet used a plain dark background); a festive date arriving in the real app (only the date logic was tested); the skin picker with a keyboard or screen reader.

### More Christmas skins (9 Nov 2026)

You chose four more, and a different Christmas skin each day.

| Skin | Looks like |
|---|---|
| Reindeer | Brown, with antlers, soft ears, a lighter muzzle and a shiny red nose |
| Snowman | Snow-white, with a top hat, a carrot nose and a red striped scarf |
| Gingerbread | Biscuit brown, with white icing at the top and bottom, and two gumdrop buttons |
| Elf | A green hat with a gold bell, a red band, and pointy ears that tint with Lumi |

**Seasonal dress-up:** from 18 to 26 December Lumi now wears a different Christmas skin each day, in turn: Santa hat, Reindeer, Snowman, Gingerbread, Elf, then round again. Christmas Day is the Snowman. Halloween and New Year are unchanged. The list is `CHRISTMAS_SKINS` in `lumi/config.py`, and the Settings description says so.

**How it was tested** (a scratch copy of the app):
- **Python:** 17 to 27 December gives nothing, then the five skins in turn, then nothing; Halloween, New Year and an ordinary day are unchanged; every skin in `SKINS` has a drawing.
- **The new skins in 13 moods, next to the Bear, checked by eye:** they tint correctly and keep clear of the eyes, glasses and "!". The snowman's thin scarf stripes read like ruler marks at real size, so they're now bolder and fewer, checked again close up.
- **The real app:** peeking (hats and antlers tuck behind the island) and full view with the coding glasses; Settings shows 17 tiles and the new description; clicking Gingerbread, Snowman, Gingerbread and Santa hat dresses Lumi each time; no script errors.
- **One false alarm:** a check said picking Gingerbread didn't change Lumi. My first test run had already picked it, so the second click landed on the tile that was already chosen, where correctly nothing happens.

**Not tested yet:** a Christmas date arriving in the real app (only the date logic was tested).

### Christmas reactions (9 Nov 2026)

You asked for all five. They happen only from 18 to 26 December with **Dress up for the season** on, and some replace a reaction Lumi already had, so they add no extra noise. All five are also in Settings → Try a reaction → **Christmas**.

| Reaction | What you see | When |
|---|---|---|
| Snowfall | Snowflakes drift down past Lumi, who looks up and sways | Every 4–8 minutes while Lumi is quiet and you're at the PC (reusing the 20 s limit on small reactions) |
| Present | A gift pops up beside Lumi, the lid flies off, sparkles burst and Lumi hops | Instead of the hop when a focus session finishes |
| Jingle | A gold bell swings above Lumi while it wiggles with happy eyes | Instead of giggle (double-click) and happy (petting) |
| Brrr | A shiver, squeezed eyes, a small "o" and three puffs of frosty breath | Coming back after being away, before the usual welcome |
| Merry Christmas | Two hops, red and green sparkles, and a flurry of snow | Lumi's first hello on 25 December, in place of "Good morning" |

| Area | What changed |
|---|---|
| Python | `is_christmas()` in `lumi/config.py`. The page's preferences now carry `christmas`, and the once-a-minute check sends them again when Christmas begins or ends, even when the skin stays the same (if you'd already chosen the Santa hat). The greeting on 25 December is "Merry Christmas" |
| Page | New elements beside Lumi: snow, gift, bell and breath. Each is solid and leaves by shrinking, not fading, because half-see-through pixels would show grey through the window's colour key. Snowflakes have a pale blue edge so they show on light skins and wallpapers. With Animation off nothing appears, and Lumi keeps its face |
| No sound | Jingle is visual only for now; sound effects are the next step |

**How it was tested:**
- **Python:** 18 to 26 December only; the flag on only with the seasonal switch on; the watcher noticing Christmas starting with an unchanged skin; "Merry Christmas" on the 25th only with the switch on, and the usual greeting otherwise.
- **The real app (a scratch copy):** each reaction played from its Settings chip and captured at four moments; with Christmas off, focus finishing, double-click, coming back and petting still give the old reactions, and with it on the new ones; the welcome follows Brrr; gift, bell, snow and breath are hidden afterwards, and stay hidden with Animation off; no script errors.
- **Seen and fixed:** the snowflakes nearly vanished against a light Lumi, so they're now a little bigger with a pale blue edge, checked again on the Snowman and on Classic.

**Not tested yet:** the 4–8 minute snowfall timer running in the real app (its condition was reviewed, and the reaction itself tested); the reactions on your own wallpaper.

### Star and Jumper: skins from your followers (9 Nov 2026)

You asked your followers for Christmas skin ideas and got three. Two are built:

| Idea | Built as |
|---|---|
| "A star with a Christmas hat, holding a peppermint stick" | **Star**: a golden, softly rounded five-point star in a Santa hat, with a red-and-white candy cane in a tiny hand (Lumi's first hand). Built as suggested |
| "Minion with a Christmas hat" | Not built: Minions belong to Illumination and Universal, and a lookalike in an app you're launching could be taken down. What the reference pictures had in common was a cosy Christmas outfit, so that became **Jumper**: Lumi in a red knitted jumper with a collar, a green band of white knitted dots, a snowflake and a ribbed hem |

| Area | What changed |
|---|---|
| Star | The body is drawn in `lumi-skins.js` (the usual one steps aside), so moods tint the star itself. A star can't wear the listening ring (it would be a box), so on this skin listening shows as the blue tint and wider eyes |
| Click area | The painted area that makes Lumi clickable shows as a dark patch wherever nothing covers it, and the usual oval would poke out between the star's points. For the Star it's a smaller oval (`hitTargets` in `island.js` now allows a per-skin inset), and changing skin repaints it |
| Jumper | The jumper is part of the body's own fill (CSS layers), so it follows Lumi's shape exactly; the face above stays the skin's cream colour and tints with the moods |
| Rotation | Over Christmas, in turn: Star, Santa hat, Reindeer, Snowman, Gingerbread, Elf, Jumper. The Star opens it on 18 December and is back for Christmas Day |

**How it was tested:**
- **Both in 13 moods, next to the Santa hat, checked by eye:** they tint correctly, the hat and candy cane stay on through tilts, and the jumper never covers the mouth.
- **The star's click area, measured in the real app:** every point on the painted oval sits at least 3.4 units inside the star's edge, so there are no dark patches; other skins keep the usual, bigger oval.
- **The real app:** peeking (the star's eyes just under the island), full view, the coding glasses on the star, and the jumper; Settings shows 19 tiles; picking Star and Jumper dresses Lumi each time from a clean start; no script errors.
- **The rotation:** 18 to 26 December gives Star, Santa hat, Reindeer, Snowman, Gingerbread, Elf, Jumper, Star, Santa hat; nothing either side.
- **One false alarm:** a re-run said picking Star didn't work, because the first run had already saved Star. From a clean start it works every time.

**Not tested yet:** clicking the star with a real mouse (the click area was checked by geometry).

## Sound effects, phase 1: Christmas (9 Nov 2026)

**Decisions:** sounds are made in code, not from files, because the bundled sound files in `video/` have no recorded licence for shipping in an app. Sounds are **off by default**, and Lumi asks once (your choice). Phase 2 (everyday moments: focus done, break over, milestones, agents finishing, small cartoon sounds) is next.

| Area | What changed |
|---|---|
| Engine | New `ui/lumi-sounds.js`: each sound is a short recipe of tones and filtered noise, all in C major, timed to its animation. A reaction plays its sound when it starts (`onReaction` in `lumi-state.js`), so a queued reaction's sound waits for its turn |
| Sounds | Jingle (sleigh bells as the bell swings), Present (a pop as the lid flies off, then a rising sparkle), Snowfall (three far-off chimes, the softest), Brrr (teeth chattering through the shiver), Merry Christmas (four bright notes over the hops) |
| Quiet rules | Silent when Sounds is off; while Lumi listens or speaks, so the mic never hears it; while the island is out of sight for a full-screen app or Hide 1 hour (Python now tells the page, `visibility`); and at most one sound every 1.5 s |
| Asking once | Six seconds after start, never during the first-run tour, Lumi asks "Want me to make little sounds?" Showing it counts as asking (`sounds_offered`), answered or not. "Yes, please" turns sounds on and plays a jingle |
| Settings | Lumi and voice → **Sounds** (says what's covered and when it stays quiet) and **Sound volume** (0–100, default 60, disabled while sounds are off). Letting go of the slider plays a jingle at the new volume. With sounds on, the Christmas try-outs play their sounds too |

**How it was tested:**
- **Each sound rendered to a file in the real app and measured:** none clips at full volume; all are under 2.5 s. The first pass was uneven (the present's pop 6 dB louder than the jingle, Brrr barely audible), so they were rebalanced. Now Jingle, Present, Brrr and Merry Christmas peak at −12 to −13 dBFS, and Snowfall at −22 dBFS on purpose. The five sounds were exported at the default volume for you to judge by ear.
- **Python:** the offer once, and never during the tour; volume outside 0–100 refused; the answer turning sounds on and off; the preferences carry both settings.
- **The real app (scratch copy, sound output spied on, so nothing played):** the offer card appears by itself; off is silent; on plays at the chosen volume; reactions without a sound stay silent; silent while listening, speaking or hidden; a second sound within 1.5 s is skipped; Hide 1 hour really tells the page, and again when it's back; the answer turns sounds on; the Settings switch, slider (saves, then jingles at the new volume), refusal of 140 and disabling all work; no script errors (after fixing one: a test's offline renderer refused to be "resumed").
- **Not tested yet:** hearing the sounds through your speakers in the app (they were checked as files); the full-screen case for real (Hide 1 hour uses the same message); Windows' own volume and mute (sounds go through the normal Windows mixer).

## Character polish (9 Nov 2026)

You asked for Lumi's designs to look much better. Every skin and panel was captured from the real app first, enlarged, on a dark and a light background. The panels held up well, so this pass is about the characters, which looked flat and lost their edge on light wallpapers.

| Area | What changed |
|---|---|
| Depth | Every body now has light from the top left, shade to the bottom right and a thin darker rim (`--shade` in `ui/lumi-skins.css`). It's all inside the body, so nothing see-through meets the window's colour key. The listening ring is drawn on top of the shading instead of replacing it. Cloud, Pixel and Star keep flat bodies, because their shapes aren't a single rounded form |
| Edges | The rim gives pale skins (Bunny, Santa hat, Snowman, Classic) an edge on light wallpapers |
| Faces | Eyes have a larger glint and a second small one. Lumi has a faint blush all the time, which moods deepen; not on Robot, Pixel, Hologram or Star |
| Colour | Cloud is a soft blue-white (`#E6F0FF`) so it shows on light backgrounds; Slime and Pixel are slightly less neon. The Star has a highlight, and its sparkle is gold instead of white, which vanished on light backgrounds |
| Settings | The skin tiles use the same shading, eyes and blush, so the picker still shows exactly what you get |
| Panels | Text selection in notes and chat now uses Lumi's blue. Nothing else changed |

**How it was tested:** before and after sheets of all 19 skins at 3x on dark and light backgrounds, compared by eye; in the real app (a scratch copy), idle, listening (the ring and the shading together, with and without a mic level), shy, sad and the Star; the Settings tiles; no script errors.

**Not tested yet:** the new look on your own wallpaper; every mood on every skin after this change (the shading sits under the face, and five states were checked).

### Panel polish (9 Nov 2026)

You asked for the panels too. They were already clean, so this is a refinement, not a new look: the panels now share the characters' light from above.

| Area | What changed |
|---|---|
| Surfaces | New tokens in `ui/island.css`: `--surface` (a touch lighter at the top), `--surface-hover` and `--lift` (a hairline of light on the top edge). Dashboard tiles, focus chips, agent chips, chat bubbles, menu buttons, the selected command-bar row, the card and the speech bubble all use them. The island itself has a very slight top-to-bottom gradient |
| Buttons | The amber focus buttons, the blue send button and the card's main button have a soft gradient and a lit top edge, so they read as pressable |
| Dashboard rings | Drawn as a masked band instead of a ring with a painted centre, so they sit correctly on the new surface |
| Music | Larger artwork tile (60 px) with a violet tint when there's no cover, and tighter spacing |
| Notes | The small capitals "QUICK NOTE" label is now a proper title with an icon, matching Focus and Agents |
| Menu | Settings, Hide 1 hour and Quit each sit on their own button shape instead of bare text |
| Mini Lumis | The small Lumis in chat and the command bar have the same shading as the character |

**How it was tested:** every panel captured before and after from the real app (a scratch copy) and compared by eye: dashboard, music, focus, notes, menu, chat, Agents, command bar, the card and the speech bubble. Nothing overflows, and there are no script errors.

**Not tested yet:** hover and pressed states by eye (their styles were changed with the rest); the focus panel while a session runs.

## Fix: second bug pass, including poor connections (10 Nov 2026)

You asked for a check for bugs, glitches and poor connectivity. The whole test suite was run again first: nothing new had broken, so this pass fixes the medium and small bugs left open on 6 November, plus how Lumi behaves when the internet is poor.

| Area | Bug | Fix |
|---|---|---|
| Connection | "Offline" was decided from one address (1.1.1.1), which some networks block | Online if any of three addresses answers (`ONLINE_PROBES` in `lumi/system.py`) |
| Connection | With no internet, chat said the provider "didn't answer", and voice said the speech service was unreachable | Both now say you're offline, after a 2-second check; chat keeps Try again |
| Connection | An agent that failed for lack of internet showed the tool's raw error | Network errors become "No internet connection. Check your network, then try again." |
| Settings file | Saved in place, so a crash mid-save could leave half a file, and an unreadable file was silently replaced by defaults | Written beside the file and swapped in (retrying if another program holds it open, then falling back to a plain write). An unreadable file is kept as `config.json.bak` |
| Settings | Text such as "false" for a switch was stored as on; a negative display was accepted | Both refused |
| Focus | The timer counted ticks, so a slow page made it run late (60.7 s for a minute) | Counted from the clock: 60.01 s measured |
| Focus | "Today" counted sessions stopped early; the weekly recap didn't | Both count finished sessions |
| Focus | One bad line in `focus_log.json`, or a log of the wrong shape, crashed the summary | Bad entries are skipped |
| Focus | The weekly recap was never offered by itself | Offered 25 s after start, and it waits behind any card you haven't answered |
| Command bar | `focus 500` and `focus abc` quietly became 25 minutes | `focus 500` offers 240 minutes (the longest), `focus 0` one minute, and `focus abc` offers no session |
| Chat | A failed answer vanished when the panel was reopened | Kept in the conversation |
| Chat | A second question could use the first one's conversation while it was still answering | It gets its own |
| Chat | Every AI setting change left a speech thread running; stuck speech could hold the microphone for ever | The old conversation's thread ends; speech has a time limit |
| Lumi's tools | "Volume up 1%" did nothing but reported success | A small request moves one step |
| Agents | The page was told about updates while holding the lock, and the tools were looked for on disk 4 times a second | Told outside the lock; the search is remembered for 30 s |
| Agents | Two calls sharing a step showed it done when the first ended; "Starting up" and "Working" stayed in finished chains | A shared step is done with its last call; stand-ins are removed |
| Agents | A task starting with a dash was read as an option | Tasks are passed after `--` (checked with both real tools) |
| Island | Right-clicking in the note or the agent task box swapped the panel for the menu | Right-click in a text field leaves the panel alone |
| Island | The active dot's pulse restarted on every update, so it never showed | Dots are rebuilt only when the steps change |
| Island | Animations ran while the island was hidden | Paused while hidden; a resting Lumi also pauses its eyes, thought dots and the agent dots |

**How it was tested:**
- **Python (24 new checks, all passing):** one blocked address still counts as online; offline messages; failed answers kept; no leftover threads; a second question gets its own conversation; network hints; the lock; the update limit of about 4 a second; shared steps; stand-ins; tasks after `--`; 100 saves under constant reading with no half-written file; a broken file kept.
- **Earlier suites:** the first suite went from 26 flagged items to 8. Those 8 are not bugs: four are checks written against the old design (they don't use the new close and own-conversation paths, or use a reader that locks the file), two are prompt shapes that never occur in real logs, one recovers in practice as a new chain, and one is below.
- **Real tools:** Claude Code and Codex both accept a task after `--` (Codex answered; Claude Code reached its usual credit error, which means the task was read correctly).
- **The real app (a scratch copy):** right-click in the note and agent box keeps the panel, and elsewhere still opens the menu; the dot pulses through ten updates; animations pause while hidden; the recap waits behind a card; the focus commands; a real question answered in 6.9 s; Settings loads and refuses bad values; a 1-minute focus took 60.01 s and counted one session; no script errors. Two checks failed first because my own test had a focus session running, so the command bar rightly offered "Stop focus"; they pass with none running.

**Left alone, on purpose:** Claude chat with no key still fails with a general message instead of "add your key". The Claude library can also sign in through a saved profile, and I couldn't tell the two apart safely, so I left it rather than risk blocking a working setup.

**Not tested yet:** the app with the internet really cut (the offline paths were tested by simulating a dead connection); the recap arriving by itself in the real app (there's no focus history from last week on this PC); a real power cut during a save.

## Showcase panels (marketing images)

**What was added:** six App-Store-style portrait panels for Lumi, in `design/showcase/`. `panels.html` loads the app's own `ui/lumi-skins.js` and `ui/lumi-skins.css`, so every skin is the real art, never redrawn, and Lumi is identical in every panel. Skin colours come from `SKINS` in `lumi/config.py`; the face, glasses and mood colours are the ones in `ui/island.html` and `ui/island.css`.

| File | Panel |
|---|---|
| `lumi-panel-1.png` | Meet Lumi (hero) |
| `lumi-panel-2.png` | Just ask (listening blue, example commands from the README) |
| `lumi-panel-3.png` | Stay in the zone (focus amber, 15/25/45/60) |
| `lumi-panel-4.png` | Give agents a job (steps as in the Agents panel, reading glasses) |
| `lumi-panel-5.png` | Dress Lumi up (nine skins) |
| `lumi-panel-6.png` | Festive Lumi (the seven Christmas skins) |
| `lumi-all-panels.png` | All six together |

Also `design/lumi-showcase-prompts.md`, a prompt kit for making similar panels with an image generator.

**How it was tested:** rendered with headless Edge at 1290 x 2796 and looked at. A first pass showed the Christmas row overlapping and Lumi too small in two panels; both were fixed and re-rendered. To re-render: `msedge --headless=new --force-device-scale-factor=2 --window-size=645,1398 --screenshot=out.png "file:///.../panels.html?p=N"`.

**Not checked:** the fonts fall back to Segoe UI (Inter is not loaded), so the type will look slightly different on another machine. Texts are placeholders to edit. The "Done. 45 minutes, starting now." reply is illustrative, not a recorded Lumi answer. Nothing was checked on a real phone or in the App Store.

## Voice: faster answers, a natural voice, and a clearer mic (11 Nov 2026)

You said the voice feature and its placement were a bit off, slow to respond, and robotic. Each part was measured or looked at first.

**What was found**

| Problem | Cause |
|---|---|
| Slow to respond | Most of the wait was the AI "thinking" before answering a spoken question: first words after 2.6 to 7.5 s |
| Robotic | Lumi spoke with the old Windows voices (David and Zira) |
| Placement | The mic button sat on top of the lower half of Lumi's face |
| Felt stuck | After you stopped talking, the pill went on saying "Listening" while Lumi worked out the answer, and nothing showed what it had heard |

**What changed**

| Area | Change |
|---|---|
| Speed | Spoken questions to Gemini skip the thinking step (`quick` in `lumi/providers/gemini.py`); typed chat is unchanged. If a model refuses that setting, Lumi answers the usual way. Lumi also stops listening after 0.7 s of silence instead of 1 s |
| Voice | New `lumi/speech.py`: Microsoft's online neural voices through `edge-tts` (your choice; default **Ava**, also Ana, Sonia and Andrew). A reply is split into pieces fetched at once and played in order by the page, so the first sentence starts before the rest is ready. Lumi's mouth follows the real loudness of the sound |
| Fallback | If the first piece isn't ready in 4.5 s (offline, or the service is down), the Windows voice says the reply instead. A one-word warm-up request is made while you're still talking, because the first request after a while is slower |
| Privacy | Natural voices send the text of Lumi's reply to Microsoft. Settings says so, and so does the first-use voice notice. The service is unofficial and could stop working; the Windows voice is always there |
| Mic | Moved to Lumi's lower right, clear of the face, still touching the body so the pointer never crosses a gap. It's hidden while Lumi listens, thinks or speaks (the pill has Stop) |
| Feedback | The pill changes to "Thinking…" the moment you stop talking. What Lumi heard appears under it in quotes until the reply |
| Settings | Lumi and voice → Voice → **Lumi's voice**: the four natural voices or "Windows voice (works offline)", and **Hear it** |
| Command bar | `talk` starts listening |

**Measured**

| Step | Before | After |
|---|---|---|
| AI's first words on a spoken question | 2.6 to 7.5 s | about 1.1 to 1.3 s |
| End-of-speech wait | 1.0 s | 0.7 s |
| Voice starts after the reply is ready | at once (Windows voice) | usually 1.5 to 2.4 s (natural voice); 4.0 s on a cold first request |

So a spoken answer now starts about 2 to 5 s sooner than before, even though the natural voice itself costs about 2 s. Choosing the Windows voice in Settings is faster still, but robotic.

**How it was tested:**
- **Python (16 checks):** how replies are split; real requests to the voice service (8 in a row: 1.5 to 2.4 s); pieces reach the page in order; the fallback when the service fails; the Windows voice when chosen; Stop; quick answers with real Gemini, including a tool call (`start_focus` with 25 minutes).
- **The real app (a scratch copy, speakers silenced, no microphone):** the mic clear of the eyes and still touching Lumi; Listening, then Thinking, then what was heard, then the reply; "Hear it" played Ava on the island with the mouth following the sound (46 level updates) and told Python when it finished; choosing Windows and Sonia saves; an unknown voice is refused; Stop silences it at once; `talk` in the command bar; no script errors.
- **One check failed:** "first sound within 3 s" took 4.0 s, because it was the first request after starting, with no warm-up. In a real spoken question the warm-up happens while you talk.
- **One check failed once and couldn't be re-run:** "quick mode stayed on" after a tool question. By then my testing had used the day's Gemini allowance (see below), so the cause is unknown. The fallback it exercised is the safe one: Lumi answers the usual way.

**Your Gemini allowance:** your key is on the free tier, which allows 20 requests a day per model. This testing used the day's 20 for `gemini-3.5-flash`. Lumi kept working through the backup model (`gemini-3.5-flash-lite`), which is what the backup setting is for. In normal use you'd reach 20 a day quickly too.

**Not tested yet:** a real spoken question from your microphone, end to end; how Ava sounds on your speakers inside the app (the samples were files); the voice service over a slow connection.

## Showcase panels, set 2 (bold pop style)

**What was added:** six more panels in `design/showcase/`, in a bold flat-pop style taken from the user's new references (solid colour blocks, heavy type, hard ink shadows, an expression grid, sticker posters). Source `panels-pop.html`; it loads the app's real `ui/lumi-skins.js` and `.css`, so Lumi is unchanged and has no outline (the pop styling is on cards and backgrounds only). Files: `lumi-pop-1.png` to `lumi-pop-6.png` and `lumi-pop-all.png`.

| File | Panel |
|---|---|
| `lumi-pop-1.png` | Your new desktop roommate (cat skin, green) |
| `lumi-pop-2.png` | 14 moods, the expressions from the model sheet (red) |
| `lumi-pop-3.png` | Pick your Lumi (cat, bunny, bear, robot) |
| `lumi-pop-4.png` | One island, three jobs: Ask, Focus, Agents (purple) |
| `lumi-pop-5.png` | Gets out of your way (hides in full-screen, sounds off until you say yes) |
| `lumi-pop-6.png` | One shortcut: Win+Alt+Space and the command bar (orange) |

**How it was tested:** rendered with headless Edge at 1290 x 2796 and looked at. Fixed after the first look: the Panel 4 headline overlapped the posters and "AGENTS" was clipped; the Panel 1 headline was tight to the edge; a sticker touched Lumi in Panel 6.

**Not checked:** the expressions are drawn with CSS approximations of the model sheet (sad, shy, puzzled, thinking), not the app's own mood code, so they may differ slightly. Fonts fall back to Segoe UI Black. The "Gets out of your way" Lumi is the cloud skin, shown asleep for effect. Copy is placeholder.

## Security fixes from the audit (11 Nov 2026)

The full audit (report in `C:\Users\hp\security-audit-skill\Dynamic-Island-main\run-1\REPORT.md`) found 9 leads, none confirmed because nothing could be run during the audit. These changes fix the 8 that are in code. The ninth, a Gemini API key in git history (commit `abcc346`), needs the key revoked in Google AI Studio; no code change fixes it.

| Lead | Fix | Files |
|---|---|---|
| The page could call private objects through the bridge (`_ctrl.apply_setting`, the provider's API key) | The bridge now accepts only plain public method names, no dots and no leading underscore | `lumi/bridge.py` (new), `lumi/window.py` |
| Any document the webview showed got the bridge | Navigation away from Lumi's own loopback pages is cancelled, dropped files and links are refused (`AllowExternalDrop` off), file-URL access is off, and both pages have a Content-Security-Policy (no inline script) | `lumi/bridge.py`, `ui/island.html`, `ui/settings.html` |
| Task text could be re-read by `cmd.exe` when the agent is a `.cmd` file | The task now goes to Claude Code and Codex on stdin, never on the command line | `lumi/agents.py` |
| Claude "read only" still ran the folder's own `.claude` hooks | Read mode now offers only the read tools (`--tools`), loads only your user settings (`--setting-sources user`) and uses `--permission-mode dontAsk` | `lumi/agents.py` |
| Voice audio went to Google over plain HTTP | Speech recognition uses the HTTPS address | `lumi/chat.py` |
| Media titles and the note could steer Lumi's tools | Tool output is quoted, shortened (120 characters for titles, 4,000 for the note) and labelled as information; Lumi's instructions say tool text is never an instruction; note lines are capped at 500 characters; `open_app` needs at least 2 letters; live voice now checks arguments like typed chat, caps tool calls at 5 per turn and stops at Esc | `lumi/tools.py`, `lumi/chat.py`, `lumi/live.py` |
| The sound helper wrote `.wav` files anywhere and served the whole repo | It serves only the render page and `ui/lumi-sounds.js`, accepts names of a-z, 0-9 and dashes, and refuses other hosts and pages | `video/christmas/tools/save_server.py` |

`requirements.txt` now pins `pywebview==6.2.1` (the bridge guard hooks its internals) and `SpeechRecognition==3.17.0`.

**How it was tested:**
- **Read mode, real Claude Code (2.1.321), a throwaway folder whose `.claude/settings.json` had a hook that writes a marker file:** with the old flags the hook ran; with the new flags it did not. Both runs then stopped on "Credit balance is too low", because the test ran with this coding session's account settings rather than Lumi's.
- **Codex (stdin):** the task `Reply with exactly: STDIN-OK & echo NOT-RUN %USERNAME%` came back word for word, so `&` and `%USERNAME%` stayed text.
- **Speech:** one second of silence sent to the HTTPS address reached Google, which answered "no speech".
- **Bridge:** allowed names (`init`, `run_agent`, pywebview's own) pass; `_ctrl.apply_setting`, `_ctrl`, `init.__globals__` and dotted names are refused. Same-origin check: other ports, `file://`, other sites and `localhost` instead of `127.0.0.1` are refused. The patches are in place after `harden()`.
- **CSP:** both pages loaded in a browser with all their scripts and stylesheets and no CSP errors; `new Function` (which pywebview uses) works; an injected `onerror` handler was blocked.
- **Tools:** a 300-character title with a line break and an instruction comes back quoted, on one line, cut to 120 characters; a 600-character note line is refused; `</note>` is stripped; a one-letter app name is refused.
- **Sound helper (on a spare port):** the render page and `lumi-sounds.js` load; `notes.txt`, `config.json`, a rebound Host, a `../` name and a foreign Origin are refused; a normal save lands in `assets/lumi-sfx`.
- **The real app:** started and ran for 25 seconds with no errors and no refused bridge calls.

**Not tested:** dropping a file or link onto the island (the navigation cancel and `AllowExternalDrop` are in place but weren't exercised); a full agent run in either mode with a working account; a spoken question end to end; live voice with the new tool checks.

**Still to do by you:** an old copy of `save_server.py` from an earlier session is still running on port 8765 (the version with the bugs); close it. Revoke the Gemini key from commit `abcc346`.

## Fix: Codex sessions not followed, and agent-panel glitches (13 Nov 2026)

**Why Codex sessions never showed:** a Codex conversation keeps writing to the log in the folder of the day it *started* (`~/.codex/sessions/2026/11/05/...`). Lumi only looked in today's and yesterday's folders, so any conversation older than a day was invisible. The only recent logs it did find were Codex's "Guardian review" helper runs, which it skips on purpose.

**What changed (`lumi/agents.py`):**
- Lumi asks the Codex app's own list of conversations (`~/.codex/state_5.sqlite`, opened read-only) which logs were updated in the last hour, and skips helper reviews. If that list can't be read, it checks every Codex log, listed once a minute. Today's and yesterday's folders are still checked for brand-new conversations.
- Helper reviews are recognised from their first line even when Lumi starts reading near the end of a big log (before, a review over 400 KB could appear as a phantom session).
- Sessions take their title and folder from the Codex app's list, so they no longer start as "A session in a folder". A title that is a whole pasted prompt uses its first real line.
- A new question in a finished conversation starts a fresh chain ("Starting") at once, instead of showing the old "Done" and the old title on a running session.
- Tool steps are readable: browser and computer-use calls show their own title ("Checking connection dialog") or "Using the computer" instead of "Js"; "google_drive.get_spreadsheet" reads "Google drive: get spreadsheet".
- Robustness: logs are read at most 4 MB per check; one odd line (wrong shape, too deeply nested) is skipped without losing the rest; a log that shrinks is read again from the start; a huge unfinished line is skipped instead of being re-read every 1.5 seconds; Lumi's own agent runs keep reading their output after an odd event, so the agent can't stall.

**How it was tested:**
- The Codex app's list, at 12 Nov 12:30 (your last Codex use): it picks the 5 Nov conversation you were in (`FP AFRICA WORK`) and recognises the three Guardian logs as helpers.
- A replay of the last 6 MB of that real 63 MB log, fed to the watcher 15 lines at a time as if Codex were writing it: 371 lines, 24 island states, ending "Done". It showed the four glitches above; after the fixes the title and folder are right from the start, the gap between questions shows "Starting", and the step names read properly.
- Bad data: arrays, strings, wrong-shaped items and a 5,000-deep nested line are skipped while the good lines around them still show; a log that shrinks is re-read; a huge unfinished line is skipped and reading carries on; a helper log with a 500 KB first line is recognised.
- The real app ran for 30 seconds with following turned on: no errors.

**Not tested:** a Codex conversation running live while Lumi is open (none was running); Claude Code following, which uses the same reader but wasn't replayed this time.

## Fix: the Claude Code / Codex switch in the Agents panel (13 Nov 2026)

**What was wrong:** the switch only chose which agent your *next* task would go to. The session shown above it was always the newest one, whatever agent it belonged to, so flipping the switch changed nothing you could see. It also opened on the agent you last used, so it could sit on Claude while Codex was the one working.

**What changed (`ui/island.js`, `ui/island.css`):**
- The switch decides what the panel shows: that agent's sessions (running ones first, with tabs if it has more than one), or "Codex has no sessions right now. Give it a task below."
- The panel opens on the agent that's working. Asking by name ("codex …" in the command bar) still wins.
- While the panel is open, it follows an agent that starts working, until you pick one yourself; after that, your choice stays.
- Each agent with a running session gets a small pulsing blue dot on its side of the switch, so you can see who's at work whichever one is picked.
- Tabs name the folder (or the task) instead of repeating the agent's name.

**How it was tested:** the real `island.html` in a browser with made-up sessions: opened while Codex works (switch on Codex, its session shown, dot on Codex); clicking Claude Code shows Claude's session and clicking Codex shows Codex's; updates arriving don't override your choice; picking an agent with no sessions hides the session box and shows the note; a Codex session starting while the panel is open switches to it when you haven't chosen; the compact island reads "Codex · Using the computer".

**Not tested:** in the real app window with real sessions running.

## Agents panel: see the whole answer, know which chat it is, and reply in it (13 Nov 2026)

**What was missing:** a task run from the island showed each answer cut to one line, never said which Codex or Claude Code chat it became or where that was saved, and your next message always started a brand-new chat.

**What changed:**
- **Read the whole answer:** answers and the final "Done" keep their full text (up to 6,000 characters). Click one to open it on the island; click again to close it. An open answer stays open, and keeps its scroll position, while updates arrive.
- **Which chat it is:** under the steps, "Codex chat 01a1d243…" (hover for the full id) with two links: **Show where it's saved** opens File Explorer at the chat's file (`~/.codex/sessions/...` or `~/.claude/projects/...`), and **Copy resume command** copies e.g. `cd "<folder>"; codex resume <id>` to carry the chat on in a terminal. Sessions you run yourself show the same strip.
- **Reply in the same chat:** after a run from the island finishes, the box says "Reply to this chat…" and your message continues it (`codex exec resume <id>` / `claude -p --resume <id>`), in the same folder, with the earlier steps still above. **New chat** (next to the agent switch) starts a fresh one instead.
- Lumi now keeps each run's chat id (Codex's `thread.started`, Claude Code's `session_id`); a reply waits up to 10 seconds for the previous run in that chat to exit, because the chat stays locked until it does.
- The page asks for a chat's file or resume command by the island's session id; Python finds the path itself.

Files: `lumi/agents.py`, `lumi/api.py` (`run_agent` takes `continue_id`; new `show_agent_chat`, `copy_agent_resume`), `ui/island.html`, `ui/island.js`, `ui/island.css`.

**How it was tested:**
- Real Codex through Lumi's own agent code, read-only, in a throwaway folder with two text files: "How many .txt files…" answered "There are 2 .txt files", chat id captured; the reply "And what fruit is in the first one…" continued the same chat and answered "The first file mentions apples." The saved file was found in `~/.codex/sessions/2026/11/13/` and the resume command built.
- The first try at the reply came back empty: it started while the first Codex process still held the chat. The 10-second wait fixed it.
- The panel in a browser with a stand-in for Python: the chat strip and "Reply to this chat…" show; clicking an answer opens all 641 characters and it stays open through an update; a reply sends the session id, "New chat" sends none; both links ask by session id. Screenshot checked.

**Not tested:** the two links in the real app (the File Explorer window and the clipboard); replying in a Claude Code chat (same mechanism, not run); the real app window.

## Guides: a pop-up tour of every feature, found again any time (13 Nov 2026)

**What was added:** ten short guides that play on the island itself. Each one opens the panel it's about, puts a pulsing blue ring around the control it's explaining, and talks you through it on Lumi's card with Back / Next / Done ("Coding agents · 2 of 6").

| Guide | Steps | What it covers |
|---|---|---|
| Getting started | 4 | The island, the mic, your shortcut, where guides live (this replaces the old first-run tour) |
| Asking Lumi | 4 | Typing, what Lumi can do, talking, Esc |
| The command bar | 4 | Apps, shortcuts (focus 45, note …, talk, next), agents, questions, "guide" |
| Your PC at a glance | 3 | Memory, battery, network, quick buttons |
| Focus sessions | 4 | Lengths, starting, breaks, your totals and weekly summary |
| Your quick note | 2 | Saving as you type, adding from anywhere |
| Music | 2 | Controls, scrolling for volume, asking Lumi |
| Coding agents | 6 | The switch, edit/read only, folder, steps and answers, replying, following your own sessions |
| Lumi's looks and sounds | 2 | Skins, colours, seasonal looks, sounds (opens Settings) |
| The menu | 3 | Settings, Hide 1 hour, Guides |

**Finding them again:**
- **Guides** in the island's right-click menu opens the command bar listing every guide.
- In the command bar, type `guide` (or `tour`, `tutorial`, `help` on its own) for the list, or `guide focus`, `tour agents` to jump to one. "help me write…" still goes to Lumi as a question.
- Settings has a **Guides** page with every guide, a "Show me" button each, and a tick on the ones you've finished.
- The first time you open a feature (chat, command bar, dashboard, focus, note, music, agents), Lumi offers its guide once: "First time here? Want a quick tour of Focus sessions? It's 4 short steps." Not now is remembered.

**How it works:** the steps are in `ui/lumi-guides.js` (shared by the island and Settings); `ui/island.js` plays them, keeps panels open while a guide shows, and ends a guide if you open something else yourself or press Esc. `lumi/api.py` lists the guides for the command bar and Settings (`GUIDES`), and remembers finished and offered ones in `config.json` (`guides_seen`, `guides_offered`).

**How it was tested:**
- Every one of the 34 steps points at a control that exists in `ui/island.html`, and the guide ids match between the page and Python.
- Command bar: `guide` lists all 10; `guide agents`, `tour focus`, `tutorial music`, `guides codex` find the right one; `help me write an email` still asks Lumi.
- In a browser with a stand-in for Python opening panels as the app does: all ten guides played start to finish (right panel, right control ringed, mic and island highlights for Getting started and Asking Lumi, Settings opened for Lumi's looks); Back goes back a step; Esc closes and leaves nothing highlighted; Done shows "Find this again under Guides" and records the guide as finished; Getting started still completes the first-run tour; opening the note for the first time offered its guide once, and not again after "Not now".
- Settings' Guides page lists all ten with ticks, and "Show me" asks the island for that guide. Screenshots checked.
- The real app started and ran for 25 seconds with no errors.

**Bug found and fixed while testing:** the guide list was declared with `const`, which the island and Settings couldn't see as `window.LUMI_GUIDES`, so no guide played. It's now `window.LUMI_GUIDES`.

**Not tested:** guides in the real app window (only in a browser); the Settings "Show me" button reaching the island in the real app.

## Design fixes from the critique: safe agent runs, panels that stay open, keyboard answers, a warmer Lumi (13 Nov 2026)

The Impeccable critique of `ui/island.html` scored 24/40 (`.impeccable/critique/2026-11-13T09-36-47Z__ui-island-html.md`). You chose: safe agent runs first, a warmer Lumi, the top 3 issues.

**1. Safe agent runs (was P0: edit rights by default, no confirmation)**
- New installs start agents in **Read only** (`agent_mode` default `read`); after that, Lumi remembers your last choice.
- The permission chip says it plainly: **Read only** (eye) or **Edits files** (amber, pencil).
- The **first edit run in a folder asks once**: an amber bar "Codex will edit files in lumi-island. Run it?" with Cancel / Run, and the send arrow turns amber; Enter again runs. Changing the task, folder, agent or permission clears the question. Folders you've said yes to are kept in `agent_edit_folders`.
- Python decides, not the page: `AgentManager.run` refuses an edit run in a new folder unless `confirmed=True` (only a real `True` counts), and `claude …` / `codex …` in the command bar opens the panel with the task filled in instead of starting.
- While a run you started is working, the box reads "Waiting for Codex…" and it and the send arrow are disabled.

**2. Panels that stay open (was P1: panels close while reading)**
- An opened answer, or text you've selected in Agents, Notes or Chat, holds the panel for 15 s after the pointer leaves, instead of 0.6 s. Clicking another window closes it (but not when Lumi itself opened Explorer, the folder picker or the clipboard).
- A **pin** in the Agents and Notes headers keeps the panel open until you unpin it, press Esc or close it.

**3. Answers from the keyboard (was P1: mouse-only)**
- Each answer's label is a real button (`aria-expanded`, "Read it all" / "Hide the full text"); focus stays on it after opening. The long task title has a tooltip and expands when you tab to it. Reading, editing and commands keep their own icons.

**4. A warmer Lumi (you chose "warmer")**
- Lumi appears in the Chat and Agents headers (30 px, with eyes), and reads along (eyes moving) while an agent works; still with reduced motion.
- Short lines for runs started from the island: "On it." when it starts; "Codex is done. Have a look?" or "That didn't work out. The Agents panel says why." when it ends and the panel is closed.
- The empty Agents panel speaks as Lumi: "Tell me a task for Claude Code or Codex. I keep an eye on the sessions you run yourself, too."
- The agent switch's working dot no longer pulses (one moving thing at a time; Lumi reading along carries it).

**Files:** `lumi/config.py`, `lumi/agents.py`, `lumi/api.py`, `ui/island.html`, `ui/island.css`, `ui/island.js`, `ui/lumi-guides.js` (the agents guide's permission step).

**How it was tested:**
- Python, with a stand-in so no agent started: read mode runs; edit mode in a new folder returns "confirm first"; `confirmed=True` runs; a folder already OK'd runs (case doesn't matter); `confirmed="yes"` does not count; the command bar opens the panel instead; new installs default to read only.
- The panel in a browser with a stand-in for Python: Read only by default; the chip turns amber; the first Enter shows the question, editing the task removes it, Run sends `confirmed=true`, the bar clears, and the next run in the same folder doesn't ask; while running, "Waiting for Codex…" with the box and arrow disabled, Lumi reading, and "On it."; the answer button opens with the keyboard and keeps focus; an opened answer holds the panel, the pin holds it through a collapse, and Esc closes it and clears the pin. Screenshots checked: the question bar (including a very long folder name, cut with "…"), the opened answer with the pin, the running state, and the chat header.
- Bugs found and fixed while testing: the question stayed up after a successful run until the next update; the island didn't grow enough for the bar when it wrapped (the bar is now always one line, 38 px).
- The design detector finds the same 8 items as before the changes (no new ones); the pulsing-dot item is addressed by the steady dot.

**Not tested:** in the real app window (your Lumi was running, and two copies can't share WebView2); a real agent run through the new confirmation; the 15-second hold and click-outside with a real mouse; screen-reader output.

## Agents panel, round 2: clearer sessions, permission per task, keyboard (13 Nov 2026)

The re-run critique scored 28/40 (up from 24; `.impeccable/critique/2026-11-13T10-12-44Z__ui-island-html.md`). You chose: a clearer Agents panel first, permission chosen when you send, both P1s.

**Clearer sessions**
- Tabs are named by their task ("Fix the login bug"), not the folder, with a status icon (spinner while working, ✓ done, ✗ problem, ■ stopped). The tooltip and screen-reader label say it in words ("Fix the login bug, Working"), with the folder in the tooltip.
- "Waiting for Codex…" only shows on the session that's running. On another session the box says which task is busy ("Codex is busy with “fix the login bug”") and a **Show it** link jumps there. (Lumi runs one agent task at a time, so the box stays disabled until it finishes.)

**Permission chosen when you send** (replaces the "Read only / Edits files" toggle)
- **Enter** or the blue arrow runs **read only**. **Run with edits** (amber, pencil) beside it lets the agent change files. Nothing lingers between tasks.
- The first edit run in a folder still asks once ("Codex will edit files in lumi-island. Run it?"); while it asks, Enter answers it. Python still decides.
- `claude …` / `codex …` in the command bar always run read only now.

**Keyboard**
- The Claude Code / Codex switch and the session tabs are one Tab stop each; arrow keys (and Home/End) move and select. The tabs control the session area (`role="tabpanel"`).
- **Ctrl+1 / Ctrl+2** pick Claude Code / Codex while the panel is open.
- The task title is only a Tab stop when it's cut off.
- With a guide showing, focus moves to the card's Next button, and goes back where it was when the guide ends.
- Tab stops in the panel with two sessions: 8 (was 13).
- The task row has a real 4px inset around its buttons.

**Files:** `ui/island.html`, `ui/island.css`, `ui/island.js`, `ui/lumi-guides.js` (the agents guide now points at "Run with edits" and mentions Ctrl+1/2), `lumi/api.py` (command bar runs read only).

**How it was tested (browser, stand-in for Python):** Enter sent `mode "read"`; Run with edits asked the folder question, and Enter answered it (`confirmed=true`); two sessions in one folder showed as "fix the login bug" (spinner, "Working") and "explain the auth module" (✓, "Done"); on the running one "Waiting for Codex…", on the other "Codex is busy with “fix the login bug”" with Show it, which jumped to the running tab and focused it; ArrowRight moved between tabs; ArrowLeft on the switch picked Claude Code and moved focus; Ctrl+2 picked Codex; 8 Tab stops; the guide card took focus and gave it back to the task box. Screenshot checked. The design detector shows the same 7 known false positives (a new "cramped" flag on the task row was fixed with the inset). Python imports and both scripts parse.

**Not tested:** the real app window (your Lumi was running); a real agent run; a screen reader.

## Release packaging: Windows installer (15 Nov 2026)

**Changes**
- `.gitignore` now skips `video/**/node_modules/`, `video/renders/`, `build/`, `dist/` and the installer output.
- Added an MIT `LICENSE` (holder "Lumi Island contributors"; change if you prefer a name) and `VERSION = '1.0.0'` in `lumi/config.py`.
- `lumi/config.py`: when frozen, settings, notes and the focus log live in `%APPDATA%\Lumi Island`; from source they stay beside the code. `window.py`: Start with Windows registers the exe itself when frozen.
- `installer/LumiIsland.spec` (PyInstaller, one-folder, no console) and `installer/LumiIsland.iss` (Inno Setup, per-user install, optional desktop shortcut and autostart, uninstaller).

**Build**
```
pyinstaller installer/LumiIsland.spec --noconfirm --distpath dist --workpath build
ISCC installer\LumiIsland.iss        (writes installer\Output\LumiIsland-Setup-1.0.0.exe)
```

**Testing**
- PyInstaller build succeeds (173 MB folder). Launched `LumiIsland.exe`: the island and Lumi render, and `config.json` is created in `%APPDATA%\Lumi Island`.
- Not yet done: building the Setup.exe (Inno Setup not installed here), a clean-PC install, and checking voice, music, agents and autostart in the frozen build.

## App icon and README hero (15 Nov 2026)

**Changes**
- `design/brand/icon.html` draws the app icon (Lumi's neutral face on a dark rounded square); `installer/lumi.ico` holds 16 to 256 px sizes. Wired into the PyInstaller exe (`icon=`) and the installer (`SetupIconFile`).
- `design/brand/hero.html` renders `design/brand/hero.png` (1600x1000), shown at the top of the README. It follows the showcase panels: cloud background, peach rings, island pill, Lumi, skin cut-outs from the model sheet, and five feature cards.
- Re-render either with Edge headless: `msedge --headless=new --window-size=1600,1000 --screenshot=hero.png file:///.../hero.html`.

**Testing**
- Looked at the rendered PNGs. The rebuilt exe has an icon resource and the Setup.exe (75 MB) compiled. I haven't looked at the icon in Explorer or the taskbar yet.
