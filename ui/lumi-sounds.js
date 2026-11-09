/* Lumi's sounds, made in code: no audio files, so nothing to license or bundle, and every sound is tuned to Lumi.
 * All of them sit in C major, short and soft. A reaction plays its sound when it starts (lumi-state.js, onReaction);
 * island.js decides whether it may play at all (the Sounds setting, and never while Lumi listens or speaks).
 * Pass { context } (an OfflineAudioContext) to render a sound for testing instead of playing it. */
function createLumiSounds(options = {}) {
    let ctx = null, master = null, noise = null;

    function start() {
        if (!ctx) {
            ctx = options.context || new AudioContext();
            master = ctx.createGain();
            master.connect(ctx.destination);
            noise = ctx.createBuffer(1, ctx.sampleRate, ctx.sampleRate);
            const data = noise.getChannelData(0);
            for (let i = 0; i < data.length; i++) data[i] = Math.random() * 2 - 1;
        }
        if (!options.context && ctx.state === 'suspended') ctx.resume().catch(() => {});  // a test's offline context starts when rendered
    }

    const note = n => 440 * 2 ** ((n - 69) / 12);  // MIDI note number -> Hz (72 is middle C's octave up, C5)
    const BELL = [[1, 1], [2.76, 0.35], [5.4, 0.12]];  // a small bell's uneven overtones
    const CHIME = [[1, 1], [2, 0.3], [3, 0.1]];

    // A struck tone: a sine per overtone, a 5 ms attack and an exponential fade
    function tone(t, freq, decay, level, partials = [[1, 1]]) {
        for (const [ratio, share] of partials) {
            const o = ctx.createOscillator(), g = ctx.createGain();
            o.frequency.value = freq * ratio;
            g.gain.setValueAtTime(0.0001, t);
            g.gain.exponentialRampToValueAtTime(level * share, t + 0.005);
            g.gain.exponentialRampToValueAtTime(0.0001, t + decay);
            o.connect(g).connect(master);
            o.start(t);
            o.stop(t + decay + 0.02);
        }
    }

    // A burst of filtered noise: the shake of a bell, a chattering tooth
    function hiss(t, length, level, freq, q, type = 'bandpass') {
        const s = ctx.createBufferSource(), f = ctx.createBiquadFilter(), g = ctx.createGain();
        s.buffer = noise;
        f.type = type; f.frequency.value = freq; f.Q.value = q;
        g.gain.setValueAtTime(level, t);
        g.gain.exponentialRampToValueAtTime(0.0001, t + length);
        s.connect(f).connect(g).connect(master);
        s.start(t, Math.random() * 0.5, length + 0.02);
    }

    // Each recipe starts at time t; its timings follow the reaction's animation in island.css
    const RECIPES = {
        // Sleigh bells: seven shakes while the bell swings (bell-ring, 1.4 s)
        jingle(t) {
            [0, 0.09, 0.2, 0.28, 0.41, 0.5, 0.62].forEach((d, i) => {
                hiss(t + d, 0.1, 0.22, 7000 + (i % 3) * 900, 0.8, 'highpass');
                tone(t + d, 2350 + (i % 3) * 240, 0.2, 0.09, BELL);
            });
        },
        // A pop as the lid flies off (lid-off, about 0.7 s in), then the sparkle rising out of the box
        present(t) {
            const p = t + 0.7, o = ctx.createOscillator(), g = ctx.createGain();
            o.frequency.setValueAtTime(700, p);
            o.frequency.exponentialRampToValueAtTime(220, p + 0.08);
            g.gain.setValueAtTime(0.0001, p);
            g.gain.exponentialRampToValueAtTime(0.22, p + 0.004);
            g.gain.exponentialRampToValueAtTime(0.0001, p + 0.12);
            o.connect(g).connect(master);
            o.start(p);
            o.stop(p + 0.15);
            [84, 88, 91, 96, 100].forEach((n, i) => tone(t + 0.8 + i * 0.06, note(n), 0.35, 0.1, BELL));
        },
        // Three far-off chimes as the flakes drift past: the quietest sound Lumi makes
        snowfall(t) {
            [[93, 0.2], [98, 0.95], [96, 1.7]].forEach(([n, d]) => tone(t + d, note(n), 1.1, 0.075, [[1, 1], [2, 0.2]]));
        },
        // Teeth chattering through the shiver (shiver, 12 x 0.09 s)
        brrr(t) {
            for (let i = 0; i < 11; i++) hiss(t + 0.08 + i * 0.075, 0.025, 1.2, 2200, 4);
        },
        // Four bright notes over the two hops
        merry(t) {
            [[88, 0, 0.5], [88, 0.17, 0.5], [91, 0.34, 0.5], [96, 0.6, 1.2]].forEach(([n, d, len]) => tone(t + d, note(n), len, 0.18, CHIME));
        }
    };

    return {
        has: name => Object.prototype.hasOwnProperty.call(RECIPES, name),
        /* volume: 0..1 (the Settings slider). Returns the context, so a test can render it. */
        play(name, volume = 0.6, at = 0) {
            if (!RECIPES[name]) return null;
            start();
            master.gain.value = volume;
            RECIPES[name]((at || ctx.currentTime) + 0.02);
            return ctx;
        }
    };
}
if (typeof module !== 'undefined') module.exports = { createLumiSounds };
