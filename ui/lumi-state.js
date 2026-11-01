/* Lumi's look, decided in one place.
 *
 * Three layers, highest first:
 *   reaction - a short one-shot (success hop, puzzled tilt, greeting, milestone spin); queued, and only bad news
 *              (puzzled, reconsider) cuts the one playing short, so it never shows after the moment has passed
 *   activity - what Lumi is doing right now (listening, thinking, speaking); a watchdog clears it if it's stuck
 *   ambient  - what's true about your PC (idle, music, focus, break, sleepy)
 *
 * Each state can have a minimum time on screen, so events arriving faster than animations don't make Lumi flicker.
 * The page tells this controller *what is happening*; only apply() touches the DOM.
 */
(function (root) {
    // How long a state must stay on screen before another (non-urgent) one replaces it
    const MIN_MS = { attentive: 300, thinking: 400, checking: 500, working: 500 };
    // How long each reaction plays
    const REACTION_MS = { success: 1200, celebrate: 1400, greet: 900, puzzled: 2500, nod: 380, reconsider: 650,
                          surprised: 900, shy: 1800, sad: 2200, giggle: 1100, happy: 1400, dizzy: 1800, yawn: 1600, notice: 1000 };
    // States that wait on something outside Lumi; if nothing changes for this long, Lumi gives up on them
    const WATCHED = new Set(['thinking', 'checking', 'working', 'attentive', 'replying']);
    // Reactions that replace the one playing instead of waiting behind it
    const INTERRUPTS = new Set(['puzzled', 'reconsider']);
    const MAX_QUEUE = 2;

    function createLumiState(options) {
        const apply = options.apply;
        const now = options.now || (() => performance.now());
        const setTimer = options.setTimer || ((fn, ms) => setTimeout(fn, ms));
        const clearTimer = options.clearTimer || (id => clearTimeout(id));
        const watchdogMs = options.watchdogMs || 45000;
        const onWatchdog = options.onWatchdog || (() => {});

        let ambient = 'idle', activity = null, reaction = null;
        let queue = [];
        let shown = null, shownAt = -Infinity;
        let renderTimer = null, reactionTimer = null, watchdogTimer = null;

        function wanted() { return reaction || activity || ambient; }

        // Reactions and listening are urgent (you should see them at once); everything else waits its turn
        function urgent(next) { return next === reaction || next === 'listening'; }

        function render() {
            clearTimer(renderTimer); renderTimer = null;
            const next = wanted();
            if (next === shown) return;
            const wait = (MIN_MS[shown] || 0) - (now() - shownAt);
            if (wait > 0 && !urgent(next)) { renderTimer = setTimer(render, wait); return; }
            shown = next;
            shownAt = now();
            apply(next);
        }

        function startReaction(name) {
            reaction = name;
            reactionTimer = setTimer(() => {
                reaction = null; reactionTimer = null;
                if (queue.length) startReaction(queue.shift());
                else render();
            }, REACTION_MS[name] || 800);
            render();
        }

        function armWatchdog() {
            clearTimer(watchdogTimer); watchdogTimer = null;
            if (!WATCHED.has(activity)) return;
            watchdogTimer = setTimer(() => {
                watchdogTimer = null;
                const stuck = activity;
                activity = null;
                render();
                onWatchdog(stuck);
            }, watchdogMs);
        }

        return {
            setAmbient(name) { if (name !== ambient) { ambient = name || 'idle'; render(); } },
            setActivity(name) {
                name = name || null;
                if (name === activity) { armWatchdog(); return; } // the same state again still counts as progress
                activity = name;
                armWatchdog();
                render();
            },
            react(name) {
                if (reaction && INTERRUPTS.has(name) && !INTERRUPTS.has(reaction)) {
                    clearTimer(reactionTimer); reactionTimer = null;
                    reaction = null; queue = [];
                } else if (reaction) {
                    queue.push(name);
                    if (queue.length > MAX_QUEUE) queue.shift(); // keep the newest
                    return;
                }
                startReaction(name);
            },
            reset() {
                [renderTimer, reactionTimer, watchdogTimer].forEach(clearTimer);
                renderTimer = reactionTimer = watchdogTimer = null;
                activity = reaction = null; queue = [];
                render();
            },
            snapshot() { return { shown, ambient, activity, reaction, queued: queue.slice() }; }
        };
    }

    root.createLumiState = createLumiState;
    if (typeof module !== 'undefined') module.exports = { createLumiState, MIN_MS, REACTION_MS };
})(typeof window !== 'undefined' ? window : globalThis);
