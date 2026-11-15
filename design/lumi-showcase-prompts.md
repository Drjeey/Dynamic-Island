# Lumi showcase designs: image-generator prompt kit

Goal: App-Store-style showcase panels (like your references) with Lumi looking identical in every one.
Source of truth for the character: `design/lumi-model-sheet.png`.

## The workflow that actually keeps Lumi consistent

Image generators drift when you describe a character in words alone. Do this instead:

1. **Always attach a reference image.** Use `lumi-model-sheet.png` (or a cropped main-pose PNG) with every generation.
   - Gemini / Nano Banana, ChatGPT image, Flux Kontext, Seedream: attach it as an input image and say "use this exact character".
   - Midjourney: `--oref <url>` (v7) or `--cref <url> --cw 100`.
2. **Paste the CHARACTER LOCK block below into every prompt.** Never reword it.
3. **Generate the background/layout and Lumi separately if it drifts.** Make the panel with an empty spot, then generate Lumi alone on a flat colour and composite in Figma.
4. **Never trust the generator with real UI or small text.** Make the phone/island screenshots yourself (or from the app) and add headlines in Figma. Ask the generator for "blank screen" or "empty headline space".
5. Once you get one great Lumi in a panel, use that panel as the reference for the next ones (chain it).

## CHARACTER LOCK (paste into every prompt)

```
Character "Lumi": a single soft, slightly lopsided peach blob (hex #FFD9C4), wider than tall at a 6:5 ratio. No neck, arms, legs, ears, nose or outline. Two tall dark pill-shaped eyes (#1C1C1E) in the upper middle, set apart by about one eye width, each with a large white glint at the top right and a tiny glint at the bottom left. Two small, faint pink oval blush marks (#FF8FA3) below and outside the eyes. No mouth at rest. Soft top-left highlight, gentle shade at the bottom right, thin slightly darker rim. Clean 3D-soft-vector look, cute, calm, minimal. Keep the eye shape and spacing exactly as in the reference image.
```

## STYLE LOCK (paste into every prompt)

```
Style: premium app-store marketing panel, portrait 9:19.5 rounded-corner card, lots of empty space, bold modern grotesque headline typography (Inter / Helvetica Now style), soft studio lighting from the top left, glossy 3D-soft shapes, one accent colour per panel. Palette: peach #FFD9C4, cloud #F2F2F7, mint #C9F0DA, sky #CFE2FF, lilac #E2D6FF, butter #FFF0B8, ink #1C1C1E. Listening blue #4C8DFF, speaking green #34C77B, focus amber #F5B83D, music violet #B98CFF used only as accents.
```

## NEGATIVE (append to every prompt, or the "avoid" field)

```
Avoid: outlines on Lumi, arms, legs, ears, nose, eyebrows, teeth, realistic textures, dark body colours, changing the eye shape or spacing, extra characters, gibberish text, fake logos, fake reviews or ratings, cluttered backgrounds.
```

## Panel prompts

Each is: `[CHARACTER LOCK] + [STYLE LOCK] + [panel text] + [NEGATIVE]`. Headlines are placeholders; change them freely, but keep claims to features that exist.

### 1. Hero: "Meet Lumi"
```
Panel on a soft cloud-white background. Top-left headline in large dark ink text: "Meet Lumi." with the word "Lumi" in a peach-to-butter gradient. Small grey subline: "A tiny AI pet that lives in your Dynamic Island." Lumi, large, centred in the lower half, happy expression (eyes curved into happy arcs, stronger blush), floating slightly with a soft contact shadow. Behind Lumi, a huge faint peach circle with concentric rings. Above Lumi, a black pill-shaped "island" bar with a tiny Lumi face inside it.
```

### 2. Talk to Lumi (dark panel)
```
Dark ink (#1C1C1E) panel. Headline in white: "Just ask." with "ask" in listening blue (#4C8DFF). Subline in grey: "Type or talk. Lumi can do things, too." Lumi in the centre, body tinted listening blue, eyes wide, small speech bubble beside it with the blank lines (no readable text). Two small floating glass chips below: "Focus 45" and "Pause music".
```

### 3. Focus mode (amber)
```
Butter-yellow (#FFF0B8) panel. Headline in ink: "Stay in the zone." with "zone" in focus amber (#F5B83D). Lumi tinted amber with calm half-lidded eyes, a thin circular timer ring around it showing most of a countdown. Island pill above Lumi showing "24:10". Subline: "Focus sessions, breaks and a daily total."
```

### 4. Agents (the bold one)
```
Cloud-white panel. Headline: "Give agents a job." with "job" in a blue-to-violet gradient. Lumi wearing round dark-rimmed reading glasses, eyes looking slightly down, thought dots above. Beside it a vertical chain of 4 small rounded nodes connected by a line, labelled with blurred placeholder text (no readable words), the active node glowing blue, finished ones grey. Subline: "Run Claude Code or Codex from the island and watch every step."
```

### 5. Skins wardrobe (grid)
```
Lilac (#E2D6FF) panel. Headline: "Dress Lumi up." with "up" in violet (#B98CFF). A 3x3 grid of rounded tiles on a lighter lilac. Each tile holds the same Lumi (identical face) wearing a different skin: cat, bunny, bear, robot, slime, Santa hat, reindeer, snowman, star. Keep the same two pill eyes and blush on every skin. Subline: "Same face, new body. Change by hand or let Lumi follow the seasons."
```

### 6. Seasonal / Christmas
```
Mint (#C9F0DA) panel with a few soft snowflakes. Headline: "Festive Lumi." with "Festive" in a red-to-green gradient. Lumi in a Santa hat, centred, with a small gift box and a falling snow layer around it. Subline: "A new Christmas skin every day."
```

### 7. Three-up onboarding screens (like your green reference)
```
Three portrait phone-style screens side by side, slightly tilted, deep green background. Each has a large headline in a bold serif-grotesque with a lime highlight under the key word: "Meet your" / "Lumi" / "Starts here"; "Something's" / "Ready" / "Always nearby"; "No more" / "Lost" / "Focus". Lumi appears in each screen in a different mood (happy, listening blue, sleepy) with identical face. Two buttons at the bottom of each ("Get started", "Learn more"), blank, no real text.
```

## Quick fixes when Lumi drifts

| Problem | Fix |
|---|---|
| Eyes become round or too small | Add: "tall dark pill eyes, exactly as in the reference, large top-right glint" |
| Lumi gets arms/legs | Add to the front of the prompt: "a limbless blob" |
| Colour wanders | Quote the hex values again and attach the reference |
| Text is garbled | Remove all text from the prompt, add it in Figma |
| Skins change the face | Say "same face, only the body details change" |

## Tool recommendations

- **Best consistency:** Gemini (Nano Banana) or ChatGPT image with the model sheet attached, iterating in one chat so it remembers Lumi.
- **Best polish for the 3D/glossy hero shots:** Midjourney with `--oref` and the model sheet.
- **Best for the final layouts:** generate art, then assemble in Figma with real fonts and real app screenshots.
