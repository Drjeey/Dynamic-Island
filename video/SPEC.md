# Lumi Island walkthrough: spec

GOAL:    the viewer understands what Lumi Island does in under two minutes and wants a small friend at the top of their screen.
OUTPUT:  HyperFrames, 1920 x 1080, 30 fps.
TIME:    101 s x 30 = 3030 frames. Narrated: the voice is the clock (Kokoro "Heart", warm female). No music bed (no local music source; see delivery note).

LOOK:
- Medium: the product's own UI, rebuilt from `ui/island.css` / `ui/island.html` / `ui/settings.css` with the real tokens: island #0B0B0D, tile #18181C, hairline rgba(255,255,255,.08), text #F2F2F5 / #A3A3AD, blue #4C8DFF, amber #F5B83D, violet #B98CFF, green #34C77B. Lumi body peach #FFD9C4 (one of the app's six presets), eyes #1C1C1E, cheeks #FF8FA3.
- Ground: a desktop wallpaper, flat moss #2F4A43 with one soft lighter pool (#3C5C53, radial, 900 px) behind the island and 2% grain. Not black, not navy, no purple or blue gradient.
- Type: Inter (stand-in for Segoe UI Variable, which can't be bundled). UI text at the app's real sizes (13 px) seen through a 2.4x camera = 31 px on screen. Captions Inter 600, 40 px, #FFFFFF on a scrim rgba(11,11,13,.55) sized to the text, radius 14, 96 px above the bottom edge.
- Depth: the island has the app's 1 px hairline; panels cast no glow. The Settings window: shadow 0 18px 48px rgba(0,0,0,.35).

OBJECTS:
- The island: the black pill, 120 x 34 compact; dashboard 548 x 104; music 360 x 150; focus 360 x 140; command 520 x 236; chat 460 x 300; radius from the app. Live activities: media (art tile, title, 4 violet EQ bars), volume bar, amber focus countdown, status with label and stop square.
- Lumi: the 60 x 50 blob (border-radius 55% 45% 42% 58% / 58% 48% 52% 42%), SVG face from the app (open eyes 8 x 12 with glint, happy arcs, closed lids, mouth ellipse, cheeks, the drawn "!" mark, thought dots). It peeks from under the pill (top 27 px, eyes at the edge) and drops to 60 px when it has something to say.
- The cursor: a white Windows arrow with a black outline, 64 px tall (6% of the frame); a click dips it to 0.86 scale for 4 frames.
- The Settings window: Windows 11 light Settings card layout from `settings.css` (bg #F3F3F3, cards #FFF, accent #2B6CDE).

MOTION:
- The app's spring for every change of island shape: GSAP "back.out(1.4)" over 13 frames (0.42 s) to expand, "power3.in" over 9 frames (0.28 s) to collapse.
- Camera: one world, a 2.4x push to the island (origin 960, 0) on "power3.inOut", 36 frames; pulls back to 1x only in shots 1 and 11.
- Lumi: springs on position and scale ("back.out(2)", damping feel about 0.5); never on opacity or colour.
- Text in panels types or streams; nothing that is being read moves.
- Something changes every 2-4 s.

SHOTS (each scene's voice starts 0.5 s in unless noted):
1. 0-7.5 Hook: full desktop at 1x, the pill tiny at top centre; push in to 2.4x. Lumi peeks, blinks, glances. Sound: whoosh on the push.
2. 7.5-17.5 Glance: cursor enters, Lumi drops out; click → dashboard morph (rings 62% memory, plug "AC", Online; Note and Focus tiles). Cursor leaves → collapse; Lumi tucks back to peek on "it just peeks". Sound: click, whoosh-in, whoosh-out.
3. 17.5-28 Music: media activity grows in; Lumi dances on the beat; scroll → volume bar 40→64; click → music panel. Sound: pop, ticks for scroll, click.
4. 28-38 Focus: focus panel, 25 min chip, Start → amber countdown, Lumi calm and amber; cut → "Focus done · 25 min" card, Lumi hops, sparkle burst. Sound: click, tick, sparkle.
5. 38-47.5 Command bar: Win + Alt + Space key caps press in; command bar opens (Lumi surprised); "calc" types → Calculator; then "focus 25". Sound: pop per key cap, key ticks.
6. 47.5-58.5 Chat: chat panel; question types; thought dots; "Starting focus…" → "✓ Focus started for 25 minutes"; "Adding to note…" → "✓ Added to your note"; reply streams with Lumi's mouth moving. Sound: ticks, pops on receipts.
7. 58.5-65.5 Stop: a long question; "Thinking…"; cursor clicks the stop square; "Stopped". Sound: click.
8. 65.5-73.5 Voice: cursor to Lumi, mic button, click; Lumi blue, ring pulsing with the level; "Checking music…"; Lumi green, mouth moving, bubble answer. Sound: click.
9. 73.5-83.5 Feelings: giggle (double-click), happy (pet), squish and hop, dizzy (pill shakes), shy, notice "!", yawn. About 1.3 s each. Sound: boing on the hop, pop on notice.
10. 83.5-94.5 Settings: window slides in; colour swatches peach → mint (Lumi recolours) → back; "When Lumi is quiet"; Try a reaction → Celebrate plays on Lumi; AI model list Gemini / Claude / OpenAI / Other. Sound: whoosh, clicks, sparkle.
11. 94.5-101 Close: pull back to 1x; Lumi hops and tucks back; end card "Lumi Island" with Lumi beside the wordmark, line "A little friend at the top of your screen." Sound: whoosh, sparkle.

BANNED: black or navy void; glow, bloom, particles; purple/blue gradients, glass cards; cream paper with serif; everything centred and fading up together; text that moves while read; corner labels and HUD; three cards in a row; the logo in a corner; invented features (WhatsApp, other apps' notifications); real personal content; a coloured square standing in for an app icon (the Calculator result uses the app's own letter-tile glyph, as the real command bar does for apps without an icon).

QA: 3 (hook push), 11 (dashboard open), 22 (music + Lumi dancing), 34 (focus countdown), 43 (command bar), 54 (chat receipts), 62 (stopped), 70 (listening ring), 78 (dizzy), 89 (settings), 99 (end card). Each must show the island large, readable UI text at 26 px or more, captions inside title-safe, and no clipped text.
