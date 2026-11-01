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
