# Review: Lumi Island walkthrough

## Creative calls
- One world: Lumi Island's own UI, rebuilt from the app's real code (`ui/island.css`, `ui/island.html`, `ui/settings.css`). It uses the real tokens, panel sizes and Lumi's SVG face, on a moss-green desktop wallpaper. A 2.6x camera keeps the 13 px UI readable (34 px on screen).
- Lumi is peach (one of the app's six presets), so it reads against the green.
- The island morphs through a clip-path on one fixed black box (the contract forbids tweening width and height). Every Lumi expression is timeline-driven, so frames are deterministic.
- The voice is the clock. Each scene's actions land on the phrase that names them.
- No storyline choice was offered: the shot list was already written and approved in conversation, and the person asked to produce it.
- Local tools only (the person's choice): Kokoro "Heart" voice made on this PC, bundled and CC0 sound effects. **No music bed**: there is no local music source, and HeyGen sign-in was declined.

## Measured vs. looked at
- `check`: passes (lint, runtime, layout, contrast, audio lanes). The kept info findings are the camera layers that overflow on purpose (`data-layout-allow-overflow`) and the Settings dropdown deliberately covering the reaction chips.
- Frames looked at: the beat sheet (22 beats), plus targeted frames for every scene; the in-between frames of the dashboard morph and the focus-to-card handoff; the dizzy, notice and yawn expressions; the Settings dropdowns.
- Fixed after looking:
  - spinning eyes flew off Lumi's face (a CSS origin doubled GSAP's);
  - the end-card Lumi covered the wordmark;
  - captions doubled during cross-fades;
  - the island turned into a flat bar mid-morph (the browser rewrites `inset()` to 3 values, so tweens paired the wrong numbers);
  - Settings dropdowns opened below their boxes;
  - text sat under the 28 px floor.
- **Sound was measured, not heard.**
  - The first render was −18.9 LUFS. It was raised with ffmpeg `loudnorm` to **−15.2 LUFS integrated, −1.3 dB true peak, 0 clipped samples** (the video stream copied unchanged).
  - Deliverables in `renders/`: `lumi-island-walkthrough.mp4` (1080p30, H.264/AAC, 101 s), `lumi-island-walkthrough.srt` (48 captions) and `lumi-island-voiceover.wav` (the voice stem). There is no music stem, since there is no music.

## Weakest shot
- The Settings scene (83.5–94.5 s) is the busiest. The window, three colour picks, two dropdowns and a celebration all happen in 11 s.
- With more time: split it into "make it yours" (colour, animation) and "choose your AI" (provider list). Also show the Animation setting on its real page (General), not alongside the Lumi page's rows.

## Kept on purpose
- The Animation row appears on the "Lumi and voice" page for brevity. In the app it lives under General.
- The Calculator result uses the command bar's own letter-tile glyph ("C"), as the real app does for apps without an icon.
- No lower-third feature labels: the captions carry the words, and corner labels are on the banned list.

## Not built
- Music bed: needs a HeyGen sign-in (`npx hyperframes auth login`, free) or a local music model. Then drop a track in as an `<audio>` at about 0.14 volume under the voice.
