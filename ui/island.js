const $ = id => document.getElementById(id);
const dom = {
    island: $('island'), lumi: $('lumi-container'), lumiBody: $('lumi-body'), bubble: $('speech-bubble'),
    eyes: $('lumi-eyes'), mic: $('mic-btn'), notesUi: $('notes-ui'),
    ramRing: $('ram-ring'), batRing: $('bat-ring'), ramVal: $('ram-val'), ramLabel: $('ram-label'),
    batVal: $('bat-val'), batLabel: $('bat-label'), netIcon: $('net-icon'), netVal: $('net-val'),
    statusUi: $('status-ui'), statusIcon: $('status-icon'), statusText: $('status-text'),
    toastText: $('toast-text'), volumeIcon: $('volume-icon'), volumeBar: $('volume-bar'), volumeVal: $('volume-val'),
    focusTime: $('focus-timer'), focusLabel: $('focus-label'), focusBar: $('focus-progress-bar'), btnFocus: $('btn-focus'), btnFocusLabel: $('btn-focus-label'),
    mediaArt: $('media-art'), mediaTitle: $('media-title'), mediaEq: $('media-eq'),
    musicUi: $('music-ui'), albumArt: $('album-art'), trackTitle: $('track-title'), trackSub: $('track-sub'),
    btnPlay: $('btn-play'), playIcon: $('play-icon'),
    notesArea: $('notes-area'), saveMsg: $('save-msg'),
    cmdInput: $('cmd-input'), cmdPins: $('cmd-pins'), cmdResults: $('cmd-results'),
    card: $('card'), cardText: $('card-text'), cardStep: $('card-step'), cardPrimary: $('card-primary'), cardSecondary: $('card-secondary'),
    fpUi: $('focuspanel-ui'), fpTitle: $('fp-title'), fpToday: $('fp-today'), fpChips: $('fp-chips'), fpStart: $('fp-start'), fpTime: $('fp-time'),
    chatLog: $('chat-log'), chatForm: $('chat-form'), chatInput: $('chat-input')
};
const api = () => window.pywebview && window.pywebview.api;
function call(name, ...args) { const a = api(); return a && a[name] ? a[name](...args) : Promise.resolve(null); }

const EXPANDED = ['dashboard', 'notes', 'music', 'menu', 'command', 'focus', 'chat'];
// Where Lumi sits under each island size (the command bar's and chat's heights vary, see lumiTop)
const LUMI_TOP = { idle: 60, dashboard: 130, music: 176, notes: 206, menu: 90, focus: 166 };

let state = 'idle';
let prefs = { motion: 'system', lumi_visible: true, scroll_volume: true, hotkey: 'Win+Alt+Space' };
let focusRunning = false;
let focusKind = 'focus';      // 'focus' or 'break' while running
let focusInfo = { today: { minutes: 0, sessions: 0 }, last_minutes: 25, durations: [15, 25, 45, 60] };
let focusMinutes = 25;        // the length picked in the focus panel
let statusActive = false;     // listening, thinking or speaking is showing in the compact island
let media = { active: false };
let previewAmbient = null;  // a mood being tried out from Settings
let toast = null;             // { kind: 'toast' | 'volume' } while a short confirmation shows
let chatWaiting = false;
let chatToken = 0;
let lastQuestion = '', lastRunSource = '';  // for "Try again"
let failedRuns = 0;  // failed requests in a row            // which typed question the chat panel is waiting for (a stopped one is ignored)      // a typed question is with Gemini
let away = false;             // no keyboard or mouse input anywhere for 10 minutes (reported by Python)
let pendingQuestion = null;   // asked from the command bar; sent once the chat panel opens
let bubbleTimer = null, collapseTimer = null, saveTimeout = null, toastTimer = null;

function escapeHtml(s) { return String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])); }

// --- SPEECH BUBBLE ---
// time 0 keeps the bubble up until the next status arrives (e.g. while Lumi is speaking)
function showBubble(text, time = 4000, isError = false) {
    clearTimeout(bubbleTimer);
    dom.bubble.textContent = text;
    dom.bubble.classList.toggle('error', isError);
    dom.bubble.classList.add('visible');
    syncPeek();
    if (time) bubbleTimer = setTimeout(hideBubble, time);
    trackHitAreas(400);
}
function hideBubble() { clearTimeout(bubbleTimer); dom.bubble.classList.remove('visible'); syncPeek(); trackHitAreas(400); }

// --- CARD (tour steps, and questions like "Take a break?") ---
let cardActions = null;
function showCard({ html, step = '', primary, secondary, onPrimary, onSecondary }) {
    hideBubble();
    cardActions = { onPrimary, onSecondary };
    dom.cardText.innerHTML = html;
    dom.cardStep.textContent = step;
    dom.cardPrimary.textContent = primary;
    dom.cardSecondary.textContent = secondary || '';
    dom.cardSecondary.style.display = secondary ? '' : 'none';
    dom.card.classList.add('visible');
    syncPeek();
    dom.card.style.top = (lumiTop(state) + 62) + 'px';
    trackHitAreas(400);
}
function hideCard() {
    cardActions = null;
    dom.card.classList.remove('visible');
    document.body.classList.remove('highlight-island', 'show-mic');
    syncPeek();
    trackHitAreas(400);
}
dom.cardPrimary.addEventListener('click', () => { const a = cardActions; hideCard(); if (a && a.onPrimary) a.onPrimary(); });
dom.cardSecondary.addEventListener('click', () => { const a = cardActions; hideCard(); if (a && a.onSecondary) a.onSecondary(); });

// --- LUMI ---
// Lumi's look is decided by the state controller (lumi-state.js). This page only reports what's happening:
// the ambient context, the current activity, and one-shot reactions.
const STATE_CLASS = {
    idle: 'mood-idle', listening: 'mood-listening', thinking: 'mood-thinking', speaking: 'mood-speaking',
    success: 'mood-success', greet: 'mood-success greet', celebrate: 'mood-success celebrate', puzzled: 'mood-error',
    music: 'mood-music', focus: 'mood-focus', break: 'mood-break', sleepy: 'mood-sleepy',
    attentive: 'mood-attentive', checking: 'mood-checking', working: 'mood-working', replying: 'mood-replying',
    nod: 'mood-nod', reconsider: 'mood-reconsider', waiting: 'mood-waiting',
    surprised: 'mood-surprised', shy: 'mood-shy', sad: 'mood-sad', giggle: 'mood-giggle', happy: 'mood-happy',
    dizzy: 'mood-dizzy', yawn: 'mood-yawn', notice: 'mood-notice', dance: 'mood-dance'
};
const lumiState = createLumiState({
    apply: s => { dom.lumi.className = STATE_CLASS[s] || 'mood-idle'; queueMicrotask(syncPeek); },
    // A stuck "thinking" (nothing heard back for 45 s) never leaves Lumi hanging, and offers a way to try again
    onWatchdog: () => {
        if (currentRun) cancelRun();
        chatWaiting = false;
        statusActive = false;
        if (state === 'idle') renderCompact();
        const retry = lastRunSource === 'chat' && lastQuestion ? () => { pendingQuestion = lastQuestion; call('open_chat'); }
            : lastRunSource === 'voice' ? () => call('start_listening') : null;
        showCard({ html: 'That took too long.', primary: retry ? 'Try again' : 'OK', secondary: retry ? 'Not now' : '', onPrimary: retry });
    }
});

// --- PEEK: while quiet, Lumi waits tucked under the island and comes out when it has something to say ---
const PEEK_TOP = 27;  // the eyes sit just below the island's edge
let peeking = false, peekTimer = null, previewing = false;
function wantsPeek() {
    if (previewing || prefs.lumi_idle === 'always' || !prefs.lumi_visible || state !== 'idle' || overIsland || overLumi) return false;
    if (dom.bubble.classList.contains('visible') || dom.card.classList.contains('visible') || tourStep >= 0) return false;
    const s = lumiState.snapshot();
    return !s.activity && !s.reaction && !currentRun;
}
function syncPeek() {
    clearTimeout(peekTimer);
    if (!wantsPeek()) { setPeek(false); return; }
    if (!peeking) peekTimer = setTimeout(() => { if (wantsPeek()) setPeek(true); }, 1500);  // settle first, then tuck in
}
function setPeek(on) {
    if (on === peeking) return;
    peeking = on;
    document.body.classList.toggle('lumi-peeking', on);
    placeLumi();
    trackHitAreas(500);
}
// What's true about the PC right now; shown whenever Lumi isn't busy or reacting
function syncAmbient() {
    lumiState.setAmbient(previewAmbient || (state === 'music' ? 'music'
        : focusRunning ? (focusKind === 'break' ? 'break' : 'focus')
        : away ? 'sleepy'
        : media.active && media.playing && intensity !== 'off' ? 'dance'  // Lumi dances while music plays
        : 'idle'));
}
// A short happy hop after Lumi does something for you
function celebrate() { lumiState.react('success'); }

// --- ACTIVITY (real steps of a request, from activity.py) ---
// Each request is a run; events carry the run id and a sequence number, so late or repeated ones are ignored.
let currentRun = null, lastSeq = 0, runErrorShown = false;
let typingEl = null, streamEl = null;  // the chat panel's "working" line and the reply being streamed
const ACTIVITY_LOOK = { thinking: ['thinking', 'i-dots'], checking: ['checking', 'i-search'], working: ['working', 'i-spin'],
                        waiting: ['thinking', 'i-dots'] };
const cancelledRuns = new Set();  // runs you stopped: anything still arriving from them is ignored

// Esc or a stop button while Lumi is working: the run ends at once, with no reaction
function cancelRun() {
    if (!currentRun && !chatWaiting) return false;
    if (currentRun) cancelledRuns.add(currentRun);
    call('cancel_run');
    lumiState.setActivity(null);
    hideActivityLabel();
    if (typingEl) { typingEl.remove(); typingEl = null; }
    if (chatWaiting) {
        // The chat is free at once: the stopped question's reply, if it still arrives, is ignored
        chatToken++;
        chatWaiting = false;
        setSendButton(false);
        if (streamEl) { streamEl.classList.add('stopped'); streamEl = null; }
        addMessage('note', 'Stopped');
    }
    return true;
}
$('status-stop').addEventListener('click', e => { e.stopPropagation(); cancelRun(); });

// Small reactions to what happens on the PC (music starting, a break beginning); only while Lumi isn't busy,
// and at most one every 20 s so they stay a nice surprise
let lastContextReaction = -Infinity;
function reactToContext(name) {
    const s = lumiState.snapshot();
    if (s.activity || s.reaction || currentRun || performance.now() - lastContextReaction < 20000) return;
    lastContextReaction = performance.now();
    lumiState.react(name);
}

function onActivity(e) {
    if (e.phase === 'run_started') {
        currentRun = e.run; lastSeq = e.seq; runErrorShown = false; lastReceipt = ''; lastRunSource = e.source;
        lumiState.setActivity('attentive');
        if (state === 'idle') renderCompact();
        return;
    }
    if (e.run !== currentRun || e.seq <= lastSeq) return;
    lastSeq = e.seq;
    switch (e.phase) {
        case 'listening': lumiState.setActivity('listening'); return;
        case 'transcribing':
        case 'understanding': showActivity('thinking', e.label); return;
        case 'tool_started': showActivity(e.kind === 'lookup' ? 'checking' : 'working', e.label); return;
        // Lumi asked something and waits for your answer (for approvals and choices; no time limit)
        case 'needs_input': showActivity('waiting', e.label); return;
        case 'tool_finished':
            lumiState.react(e.reaction || (e.status === 'ok' ? 'nod' : 'reconsider'));
            addReceipt(e.status, e.receipt, e.kind);
            return;
        case 'responding':
            // Typed answers stream in with a moving mouth; spoken ones switch to "speaking" when the voice starts
            if (e.source === 'chat') { lumiState.setActivity('replying'); hideActivityLabel(); }
            return;
        case 'run_finished':
            currentRun = null;
            lumiState.setActivity(null);
            hideActivityLabel();
            if (state === 'idle') renderCompact();
            if (e.status === 'ok' && lastReceipt && state === 'idle') showToast(lastReceipt, 'toast', 2200);
            failedRuns = e.status === 'error' ? failedRuns + 1 : e.status === 'ok' ? 0 : failedRuns;
            if (e.status === 'error' && !runErrorShown) { lumiState.react(failedRuns >= 2 ? 'sad' : 'puzzled'); runErrorShown = true; }
            return;
    }
}

// The label goes in the compact island, or on the chat panel's "working" line while the chat is open
function showActivity(look, label) {
    lumiState.setActivity(look);
    if (!label) return;
    if (state === 'chat') { if (typingEl) { typingEl.textContent = label; typingEl.classList.add('labelled'); } return; }
    if (state !== 'idle' || (statusActive && dom.statusUi.classList.contains('listening'))) return;
    const [kind, icon] = ACTIVITY_LOOK[look];
    setStatus(kind, icon, label);
    statusActive = true;
    dom.island.setAttribute('aria-label', 'Lumi: ' + label);
    renderCompact();
}
function hideActivityLabel() {
    if (!statusActive || !['thinking', 'checking', 'working', 'done'].some(k => dom.statusUi.classList.contains(k))) return;
    statusActive = false;
    if (state === 'idle') renderCompact();
}
// A receipt says what a tool did: a line in the chat; in the compact island it replaces the label inside the same
// shape (so the pill doesn't jump and Stop stays), and the last one is confirmed once the request ends
let lastReceipt = '';
function addReceipt(status, text, kind) {
    if (!text) return;
    if (state === 'chat') {
        const div = document.createElement('div');
        div.className = 'receipt ' + (status === 'ok' ? 'ok' : 'failed');
        div.textContent = text;
        dom.chatLog.insertBefore(div, typingEl && typingEl.parentNode === dom.chatLog ? typingEl : null);
        layoutChat();
    } else if (status === 'ok') {
        if (kind === 'lookup') return;  // what Lumi looked up is in its answer
        lastReceipt = text;
        if (currentRun && statusActive && state === 'idle') setStatus('done', 'i-check', text);
    } else {
        showBubble(text, 3500, true);
    }
}
// A typed reply arriving piece by piece
function onChatDelta(d) {
    if (state !== 'chat' || cancelledRuns.has(d.run) || d.run !== currentRun && currentRun !== null) return;
    if (!streamEl) {
        if (typingEl) { typingEl.remove(); typingEl = null; }
        streamEl = addMessage('lumi', '');
    }
    streamEl.textContent = d.text;
    layoutChat();
}

// --- VOICE LEVELS (levels.py): the listening ring follows your voice, the mouth follows Lumi's ---
// Kept in custom properties (--mic, --voice) and data attributes on Lumi, which mood changes leave alone
const levelTimers = {};
function onLevel(d) {
    const kind = d.kind === 'mic' ? 'mic' : 'voice', prop = '--' + kind;
    clearTimeout(levelTimers[kind]);
    clearTimeout(levelTimers[kind + '-pulse']);
    if (d.end || intensity === 'off') {
        delete dom.lumi.dataset[kind];
        dom.lumi.style.setProperty(prop, 0);
        return;
    }
    dom.lumi.dataset[kind] = '';
    dom.lumi.style.setProperty(prop, d.value);
    // A word starting opens the mouth; it nearly closes again until the next word
    if (d.pulse) levelTimers[kind + '-pulse'] = setTimeout(() => dom.lumi.style.setProperty(prop, 0.15), 140);
    // Levels that stop without an "end" (say, a lost message) hand back to the normal animation
    levelTimers[kind] = setTimeout(() => onLevel({ kind, end: true }), d.pulse ? 1500 : 600);
}
function celebrateMilestone() { if (prefs.celebrations) lumiState.react('celebrate'); }

// --- SMALL SIGNS OF LIFE ---
// How much Lumi moves: 'full', 'subtle' or 'off', from the Motion setting and Windows' reduced-motion setting
let intensity = 'full';
const reducedMotionQuery = matchMedia('(prefers-reduced-motion: reduce)');
function resolveIntensity() {
    const m = prefs.motion;
    if (m === 'system') return reducedMotionQuery.matches ? 'off' : 'full';
    if (m === 'reduced') return 'off'; // older setting name
    return ['full', 'subtle', 'off'].includes(m) ? m : 'full';
}
// Greeting: once a day on first open, and when you come back after being away
function greet(text) {
    lumiState.react('greet');
    if (text && state === 'idle' && !statusActive) showToast(text, 'toast', 2200);
}
// Eyes briefly look somewhere, unless Lumi is busy with something else
let eyesBusyUntil = 0, lastPointerMove = 0;
function lookBriefly(x, y, ms) {
    if (intensity === 'off' || !dom.lumi.classList.contains('mood-idle')) return;
    dom.eyes.style.transform = `translate(${x}px, ${y}px)`;
    eyesBusyUntil = performance.now() + ms;
    setTimeout(() => { if (performance.now() >= eyesBusyUntil) dom.eyes.style.transform = ''; }, ms);
}
function glanceAtIsland() { lookBriefly(0, -3, 400); }
// Every 20-40 s of quiet (no pointer nearby), Lumi glances to one side; full intensity only
(function glance() {
    setTimeout(() => {
        if (intensity === 'full' && state === 'idle' && performance.now() - lastPointerMove > 5000) {
            lookBriefly(Math.random() < 0.5 ? -3 : 3, -0.5, 800);
        }
        glance();
    }, 20000 + Math.random() * 20000);
})();
// Pressing Lumi gives a little squash ("boop") before the chat opens
dom.lumiBody.addEventListener('pointerdown', () => {
    if (intensity === 'off') return;
    dom.lumiBody.classList.remove('boop');
    void dom.lumiBody.offsetWidth; // restart the animation
    dom.lumiBody.classList.add('boop');
    setTimeout(() => dom.lumiBody.classList.remove('boop'), 300);
});
function fmtMinutes(m) {
    const h = Math.floor(m / 60), r = m % 60;
    return h ? `${h} h${r ? ' ' + r + ' min' : ''}` : `${m} min`;
}

// Eyes follow the cursor while Lumi is idle
document.addEventListener('mousemove', (e) => {
    wake();
    lastPointerMove = performance.now();
    if (lastPointerMove < eyesBusyUntil) return; // a glance is playing
    if (!dom.lumi.classList.contains('mood-idle')) return;
    const rect = dom.lumi.getBoundingClientRect();
    const anchorX = rect.left + rect.width / 2, anchorY = rect.top + rect.height / 2;
    const angle = Math.atan2(e.clientY - anchorY, e.clientX - anchorX);
    const dist = Math.min(3, Math.hypot(e.clientX - anchorX, e.clientY - anchorY) / 50);
    dom.eyes.style.transform = `translate(${Math.cos(angle) * dist}px, ${Math.sin(angle) * dist}px)`;
});

// Blink every 4-9 s
(function blink() {
    setTimeout(() => {
        dom.lumi.classList.add('blink');
        setTimeout(() => { dom.lumi.classList.remove('blink'); blink(); }, 140);
    }, 4000 + Math.random() * 5000);
})();

// Hold still after two minutes without the mouse nearby, to save power
let restTimer = null, lastYawn = -Infinity;
function wake() {
    document.body.classList.remove('resting');
    clearTimeout(restTimer);
    restTimer = setTimeout(() => {
        const yawn = intensity === 'full' && performance.now() - lastYawn > 20 * 60000 && !lumiState.snapshot().activity;
        if (yawn) { lastYawn = performance.now(); lumiState.react('yawn'); }
        setTimeout(() => document.body.classList.add('resting'), yawn ? 1700 : 0);
    }, 120000);
}
wake();

// --- PREFERENCES ---
function applyPrefs(p) {
    prefs = Object.assign(prefs, p || {});
    intensity = resolveIntensity();
    const html = document.documentElement;
    // Off: no motion at all (Lumi still changes colour and face). An explicit Full/Subtle overrides Windows' setting.
    html.classList.toggle('motion-reduced', intensity === 'off');
    html.classList.toggle('motion-full', prefs.motion !== 'system' && intensity !== 'off');
    html.classList.toggle('motion-subtle', intensity === 'subtle');
    html.classList.toggle('lumi-float', intensity === 'full');
    document.body.classList.toggle('lumi-hidden', !prefs.lumi_visible);
    if (prefs.lumi_hex) document.documentElement.style.setProperty('--lumi', prefs.lumi_hex);
    syncPeek();
    trackHitAreas(400);
}

// --- STATE ENGINE ---
function lumiTop(st) {
    if (peeking && st === 'idle') return PEEK_TOP;
    if (st === 'command' || st === 'chat') return dom.island.offsetTop + parseFloat(dom.island.style.height || 300) + 16;
    return LUMI_TOP[st] ?? 60;
}
function placeLumi() {
    const top = lumiTop(state);
    dom.lumi.style.top = top + 'px';
    dom.bubble.style.top = (top + 60) + 'px';
    dom.card.style.top = (top + 62) + 'px';
}

function setIslandState(st) {
    const leaving = state;
    state = st;
    if (st !== 'command' && st !== 'chat') dom.island.style.height = '';
    placeLumi();
    if (st === 'idle') renderCompact();
    else dom.island.className = st + ' pywebview-drag-region'; // Ensure drag class stays
    // Compact, the island itself is the button; expanded, it's a group holding the panel's own buttons
    const compact = st === 'idle';
    dom.island.setAttribute('role', compact ? 'button' : 'group');
    if (!statusActive && !compact) dom.island.setAttribute('aria-label', 'Lumi Island, ' + st);
    if ((st === 'dashboard') !== (leaving === 'dashboard')) call('watch_stats', st === 'dashboard');
    const expanded = EXPANDED.includes(st);
    if (expanded !== trackingPointer) { trackingPointer = expanded; call('track_pointer', expanded); }
    if (expanded !== EXPANDED.includes(leaving)) glanceAtIsland(); // a panel opened or closed
    syncAmbient();
    syncPeek();
}
let trackingPointer = false;

// The compact island shows the most important live thing: status > confirmation > focus/break > now playing
function renderCompact() {
    let act = '';
    if (statusActive) act = 'status';
    else if (toast) act = toast.kind;
    else if (focusRunning) act = 'focus';
    else if (media.active) act = 'media';
    dom.island.className = 'idle' + (act ? ' act-' + act : '') + (act === 'focus' && focusKind === 'break' ? ' break' : '')
        + (act === 'status' && currentRun ? ' can-stop' : '') + ' pywebview-drag-region';
    if (act === 'status') fitStatus();
    // What a screen reader hears, and what Enter will open
    else dom.island.setAttribute('aria-label', compactLabel(act));
}
function compactLabel(act) {
    if (act === 'media') return `Now playing: ${media.title || 'music'}${media.artist ? ' by ' + media.artist : ''}. Press Enter for the player`;
    if (act === 'focus') return `${focusKind === 'break' ? 'Break' : 'Focus'}, ${dom.focusTime.textContent} left. Press Enter for the timer`;
    if (act === 'toast') return dom.toastText.textContent;
    return 'Lumi Island. Press Enter to open the dashboard';
}

function showToast(text, kind = 'toast', ms = 1800) {
    clearTimeout(toastTimer);
    toast = { kind };
    if (kind === 'toast') dom.toastText.textContent = text;
    if (state === 'idle') renderCompact();
    toastTimer = setTimeout(() => { toast = null; if (state === 'idle') renderCompact(); }, ms);
}

function showVolume(v) {
    dom.volumeBar.style.width = v.level + '%';
    dom.volumeVal.textContent = v.muted ? 'Muted' : v.level;
    dom.volumeIcon.setAttribute('href', v.muted || v.level === 0 ? '#i-mute' : '#i-volume');
    showToast('', 'volume', 1200);
}

function renderMedia() {
    const m = media;
    dom.mediaTitle.textContent = m.title || '';
    dom.mediaArt.style.backgroundImage = m.art ? `url("${m.art}")` : '';
    dom.mediaArt.firstElementChild.style.display = m.art ? 'none' : '';
    dom.mediaEq.classList.toggle('paused', !m.playing);
    dom.musicUi.classList.toggle('empty', !m.active);
    dom.trackTitle.textContent = m.active ? m.title : 'Nothing playing';
    dom.trackSub.textContent = m.active ? [m.artist, m.app].filter(Boolean).join(' · ') : 'Play something in any app';
    dom.albumArt.style.backgroundImage = m.art ? `url("${m.art}")` : '';
    dom.albumArt.classList.toggle('has-art', !!m.art);
    dom.albumArt.classList.toggle('paused', m.active && !m.playing);
    dom.playIcon.setAttribute('href', m.playing ? '#i-pause' : '#i-play');
    dom.playIcon.parentElement.classList.toggle('solid', !m.playing);
    dom.btnPlay.setAttribute('aria-label', m.playing ? 'Pause' : 'Play');
    if (state === 'idle') renderCompact();
}

function renderStats(data) {
    // bat is null on machines without a battery
    const onAC = data.bat === null;
    dom.ramRing.style.setProperty('--pct', data.ram + '%');
    dom.ramRing.classList.toggle('high', !!data.ram_high);
    dom.ramVal.textContent = data.ram + '%';
    dom.ramLabel.textContent = data.ram_high ? 'Memory high' : 'Memory';
    dom.batRing.style.setProperty('--pct', (onAC ? 100 : data.bat) + '%');
    dom.batVal.textContent = onAC ? 'AC' : data.bat + '%';
    dom.batLabel.textContent = onAC ? 'Plugged in' : (data.charging ? 'Charging' : 'Battery');
    dom.netVal.textContent = data.online === null ? 'Checking' : (data.online ? 'Online' : 'Offline');
    dom.netIcon.classList.toggle('online', data.online === true);
    dom.netIcon.classList.toggle('offline', data.online === false);
}

window.updateState = function(msg) {
    const data = msg.data || {};
    switch (msg.state) {
        // Python reports whether the pointer is over the island or Lumi while a panel is open
        case 'pointer': overIsland = data.inside; overLumi = false; updatePointer(); return;
        case 'prefs': applyPrefs(data); return;
        case 'stats': if (state === 'dashboard') renderStats(data); return;
        case 'media': {
            const was = media;
            media = data;
            renderMedia();
            // Music starting gets a little nod; a new track, a glance up at the title
            if (data.active && data.playing && !(was.active && was.playing)) reactToContext('nod');
            else if (data.playing && was.title && data.title !== was.title) lookBriefly(0, -3, 600);
            syncAmbient();
            return;
        }
        case 'onboard': startOnboarding(); return;
        case 'lumi_action': showToast(data.text); celebrate(); return; // older tools; receipts replace this
        case 'activity': onActivity(data); return;
        case 'chat_delta': onChatDelta(data); return;
        case 'level': onLevel(data); return;
        case 'shake': lumiState.react('dizzy'); return;  // you shook the island
        case 'preview': preview(data.name, data.label); return;
        // You've been away from the PC for 10 minutes (or just came back)
        case 'presence': {
            const wasAway = away;
            away = data.away;
            if (away && !wasAway) lumiState.react('yawn');  // a yawn, then off to sleep
            syncAmbient();
            if (wasAway && !away) greet('Welcome back'); // a little stretch on waking
            return;
        }
        case 'summary': showSummary(data); return;
        // The focus timer ticks without taking over whatever panel is open
        case 'focus_tick': {
            const wasKind = focusRunning ? focusKind : null;
            focusRunning = true;
            focusKind = data.kind || 'focus';
            if (focusKind === 'break' && wasKind !== 'break') reactToContext('greet');  // a little stretch for the break
            dom.focusTime.textContent = dom.fpTime.textContent = data.timer;
            dom.focusLabel.textContent = focusKind === 'break' ? 'Break' : 'Focus';
            dom.focusBar.style.width = (100 * (1 - data.remaining / data.total)) + '%';
            syncFocusButton();
            if (state === 'focus') renderFocusPanel();
            if (state === 'idle') renderCompact();
            syncAmbient();
            return;
        }
        case 'focus_end':
            if (data.stopped && data.kind === 'focus') lumiState.react('sad');  // stopped early: a small sigh
            focusRunning = false;
            if (data.today) focusInfo.today = data.today;
            syncFocusButton();
            if (state === 'focus') renderFocusPanel();
            if (state === 'idle') renderCompact();
            syncAmbient();
            if (data.finished) offerNext(data);
            if (data.milestone) { celebrateMilestone(); showBubble(data.milestone, 5000); }
            return;
        case 'command': openCommandBar(data.pins || []); return;
    }

    // Listening/thinking/speaking take over the compact island (you started them); other statuses never close a panel
    const prevState = state;
    let st = msg.state;
    const statusShown = ['listening', 'thinking', 'speaking'].includes(data.status);
    if (statusShown && state !== 'chat') st = 'idle';
    else if (st === 'idle' && EXPANDED.includes(state) && data.status) st = state;
    statusActive = statusShown && st === 'idle';
    if (st === 'focus' && 'durations' in data) { focusInfo = data; focusMinutes = data.last_minutes || 25; }
    setIslandState(st);
    if (statusActive) dom.island.setAttribute('aria-label', 'Lumi is ' + data.status);

    // Statuses from Python become Lumi's activity (or a reaction); the controller decides how that looks
    if (data.status === 'listening') {
        setStatus('listening', 'i-mic', 'Listening');
        lumiState.setActivity('listening');
        hideBubble();
    } else if (data.status === 'thinking') {
        setStatus('thinking', 'i-dots', 'Thinking');
        lumiState.setActivity('thinking');
    } else if (data.status === 'speaking') {
        setStatus('speaking', 'i-bars', 'Speaking');
        lumiState.setActivity('speaking');
        showBubble(data.text, 0);
    } else if (data.status === 'error') {
        lumiState.setActivity(null);
        lumiState.react('puzzled');
        if (currentRun) runErrorShown = true;
        // Something only Settings can fix gets a card with the button; anything else a short bubble
        if (data.action === 'settings') showSettingsCard(data.text);
        else showBubble(data.text, 6000, true);
    } else if (data.status === 'notice') {
        lumiState.react('notice');
        showBubble(data.text, 12000);
    } else if (data.status === 'idle') {
        lumiState.setActivity(null);
        hideBubble();
    }

    if (st === 'dashboard' && 'ram' in data) renderStats(data);
    if (st === 'music' && 'active' in data) { media = data; renderMedia(); }
    if (st === 'notes' && typeof data.note === 'string' && document.activeElement !== dom.notesArea) dom.notesArea.value = data.note;
    if (st === 'notes') dom.notesUi.classList.toggle('empty', !dom.notesArea.value.trim());
    if (st === 'focus') renderFocusPanel();
    if (st === 'chat' && 'messages' in data) openChat(data.messages);

    if (EXPANDED.includes(st)) {
        if (st !== prevState) startGrace();
        scheduleCollapse(pointerInside ? 600 : 4000);
    } else clearTimeout(collapseTimer);
};

function setStatus(kind, icon, text) {
    dom.statusUi.className = 'content compact ' + kind;
    dom.statusIcon.setAttribute('href', '#' + icon);
    dom.statusText.textContent = text;
    fitStatus();
}
// The pill is as wide as its label needs (on one line; a very long one ends in "…"), plus the stop button
const measureCtx = document.createElement('canvas').getContext('2d');
function fitStatus() {
    const cs = getComputedStyle(dom.statusText);
    measureCtx.font = `${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`;
    const label = Math.ceil(measureCtx.measureText(dom.statusText.textContent).width);
    const stop = currentRun ? 30 : 0;  // the stop button and the gap before it
    dom.island.style.setProperty('--status-w', Math.min(280, Math.max(140, 14 + 16 + 8 + label + stop + 14 + 4)) + 'px');
}

function syncFocusButton() {
    dom.btnFocusLabel.textContent = focusRunning ? (focusKind === 'break' ? 'Break' : dom.focusTime.textContent) : 'Focus';
}

// --- FOCUS PANEL ---
function renderFocusPanel() {
    const t = focusInfo.today || { minutes: 0, sessions: 0 };
    dom.fpToday.textContent = `Today: ${t.minutes} min · ${t.sessions} ${t.sessions === 1 ? 'session' : 'sessions'}`;
    dom.fpUi.classList.toggle('running', focusRunning);
    dom.fpTitle.textContent = focusRunning && focusKind === 'break' ? 'Break' : 'Focus';
    dom.fpChips.innerHTML = (focusInfo.durations || [15, 25, 45, 60]).map(m =>
        `<button class="fp-chip" type="button" role="radio" aria-checked="${m === focusMinutes}" tabindex="${m === focusMinutes ? 0 : -1}" data-min="${m}">${m} min</button>`).join('');
    dom.fpStart.textContent = `Start ${focusMinutes} min`;
}
dom.fpChips.addEventListener('click', e => {
    const b = e.target.closest('[data-min]');
    if (b) { focusMinutes = +b.dataset.min; renderFocusPanel(); }
});
dom.fpChips.addEventListener('keydown', e => {
    const step = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[e.key];
    if (!step) return;
    e.preventDefault();
    const list = focusInfo.durations || [15, 25, 45, 60];
    focusMinutes = list[(list.indexOf(focusMinutes) + step + list.length) % list.length];
    renderFocusPanel();
    dom.fpChips.querySelector('[aria-checked="true"]').focus();
});
dom.fpStart.addEventListener('click', () => { call('start_focus', focusMinutes); collapseSoon(); });
$('fp-break').addEventListener('click', () => { call('start_break', 5); collapseSoon(); });
$('fp-stop').addEventListener('click', () => call('stop_focus'));

// When a session ends, offer the natural next step
function offerNext(data) {
    if (data.kind === 'break') {
        lumiState.react('notice');
        showCard({ html: "Break's over. Ready for another round?", primary: `Focus ${focusInfo.last_minutes || 25} min`, secondary: 'Not now',
                   onPrimary: () => call('start_focus', focusInfo.last_minutes || 25) });
    } else {
        const t = data.today || {};
        showCard({ html: `Focus done · ${data.minutes} min. That's ${t.minutes || data.minutes} min today.<br>Take a 5-minute break?`,
                   primary: 'Take a break', secondary: 'Not now', onPrimary: () => call('start_break', 5) });
        // A milestone gets its own spin instead; one celebration at a time is enough
        if (!(data.milestone && prefs.celebrations)) celebrate();
    }
}

// --- WEEKLY SUMMARY ---
function showSummary(data) {
    lumiState.react('notice');
    const w = data.last_week || {}, now = data.this_week || {};
    let html;
    const hadFocus = w.sessions || w.minutes;
    if (hadFocus) {
        html = `Last week you focused for <b>${fmtMinutes(w.minutes)}</b> over ${w.sessions} ${w.sessions === 1 ? 'session' : 'sessions'} on ${w.days} ${w.days === 1 ? 'day' : 'days'}.`;
    } else {
        html = 'No focus sessions last week.';
    }
    if (now.minutes) html += ` This week so far: <b>${fmtMinutes(now.minutes)}</b>.`;
    else if (!hadFocus) html += ' Start one from the dashboard or with "focus 25" in the command bar.';
    if (w.streak > 1) html += ` Current streak: ${w.streak} days.`;
    showCard({ html, primary: hadFocus || now.minutes ? 'Nice' : 'OK', secondary: data.asked ? '' : 'Stop weekly recaps',
               onSecondary: () => call('stop_weekly_summaries') });
}

// --- CHAT ---
function renderMessages(messages) {
    dom.chatLog.innerHTML = messages.length
        ? messages.map(m => `<div class="msg ${m.role === 'user' ? 'user' : 'lumi'}">${escapeHtml(m.text)}</div>`).join('')
        : '<div class="chat-empty">Ask me anything, or ask me to start a focus session, add to your note, or play the next song.</div>';
}
function addMessage(cls, text) {
    dom.chatLog.querySelector('.chat-empty')?.remove();
    const div = document.createElement('div');
    div.className = 'msg ' + cls;
    div.textContent = text;
    dom.chatLog.appendChild(div);
    layoutChat();
    return div;
}
function layoutChat() {
    dom.chatLog.style.height = 'auto';
    const logH = Math.max(60, Math.min(260, dom.chatLog.scrollHeight));
    dom.chatLog.style.height = logH + 'px';
    dom.island.style.height = (10 + 26 + 8 + logH + 8 + 36 + 10) + 'px';
    if (state === 'chat') placeLumi();
    dom.chatLog.scrollTop = dom.chatLog.scrollHeight;
}
function openChat(messages) {
    hideCard();
    renderMessages(messages || []);
    layoutChat();
    setTimeout(() => dom.chatInput.focus(), 30);
    if (pendingQuestion) { const q = pendingQuestion; pendingQuestion = null; sendChat(q); }
}
function sendChat(text) {
    text = text.trim();
    if (!text || chatWaiting) return;
    addMessage('user', text);
    typingEl = addMessage('lumi typing', '•••');
    streamEl = null;
    chatWaiting = true;
    setSendButton(true);
    lumiState.setActivity('attentive');
    const token = ++chatToken;
    lastQuestion = text;
    const compliment = /\b(thanks?|thank you|cute|adorable|love (you|u)|good job|well done|you('re| are) (great|amazing|the best|awesome))\b/i.test(text);
    call('ask', text).then(res => {
        if (token !== chatToken) return;  // you stopped this one
        if (typingEl) { typingEl.remove(); typingEl = null; }
        chatWaiting = false;
        setSendButton(false);
        lumiState.setActivity(null);
        if (res && res.cancelled) {
            // Stopped: keep whatever had arrived, marked as stopped
            if (streamEl) streamEl.classList.add('stopped');
            addMessage('note', 'Stopped');
        } else if (res && res.reply) {
            if (streamEl) streamEl.textContent = res.reply; else addMessage('lumi', res.reply);
            if (compliment) setTimeout(() => lumiState.react('shy'), 300);
        }
        else { addError((res && res.error) || "I couldn't reply.", res && res.action); if (!runErrorShown) lumiState.react('puzzled'); }
        streamEl = null;
        layoutChat();
        if (state !== 'chat') return;
        dom.chatInput.focus();
    });
}
// An error in the chat, with its way out next to it
function addError(text, action) {
    const div = addMessage('error', text);
    if (action !== 'settings' && action !== 'retry') return;
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'msg-action';
    b.textContent = action === 'settings' ? 'Open Settings' : 'Try again';
    b.addEventListener('click', () => {
        if (action === 'settings') { call('open_settings'); return; }
        b.disabled = true;
        sendChat(lastQuestion);
    });
    div.appendChild(b);
    layoutChat();
}
function showSettingsCard(text) {
    showCard({ html: escapeHtml(text), primary: 'Open Settings', secondary: 'Not now', onPrimary: () => call('open_settings') });
}

function setSendButton(working) {
    const b = dom.chatForm.querySelector('.chat-send');
    b.querySelector('use').setAttribute('href', working ? '#i-stop' : '#i-send');
    b.setAttribute('aria-label', working ? 'Stop' : 'Send');
    b.title = working ? 'Stop (Esc)' : '';
    b.classList.toggle('stop', working);
}
dom.chatForm.addEventListener('submit', e => {
    e.preventDefault();
    if (chatWaiting) { cancelRun(); return; }  // the button is "Stop" while Lumi works
    const text = dom.chatInput.value;
    dom.chatInput.value = '';
    sendChat(text);
});
$('chat-close').addEventListener('click', () => collapse());
// Click Lumi (not the mic) to chat
// Click Lumi to chat; double-click makes it giggle; press and hold squishes it, and it hops when you let go
let clickTimer = null, holdTimer = null, held = false;
dom.lumiBody.addEventListener('click', e => {
    if (held) { held = false; return; }
    if (e.detail >= 2) { clearTimeout(clickTimer); lumiState.react('giggle'); return; }
    clickTimer = setTimeout(() => { if (state !== 'chat') call('open_chat'); }, 260);
});
dom.lumiBody.addEventListener('pointerdown', () => {
    clearTimeout(holdTimer);
    holdTimer = setTimeout(() => { held = true; dom.lumiBody.classList.add('squish'); }, 450);
});
function releaseHold() {
    clearTimeout(holdTimer);
    if (!dom.lumiBody.classList.contains('squish')) return;
    dom.lumiBody.classList.remove('squish');
    lumiState.react('success');
}
dom.lumiBody.addEventListener('pointerup', releaseHold);
dom.lumiBody.addEventListener('pointerleave', () => { releaseHold(); held = false; });
// Rub the pointer back and forth over Lumi to pet it; rest the pointer on it and it gets shy
let petLastX = null, petDir = 0, petTurns = [], petCooldown = 0, shyTimer = null, shyShown = false;
dom.lumi.addEventListener('mousemove', e => {
    const now = performance.now();
    clearTimeout(shyTimer);
    if (!shyShown) shyTimer = setTimeout(() => { shyShown = true; if (!lumiState.snapshot().activity) lumiState.react('shy'); }, 2500);
    if (petLastX !== null && Math.abs(e.clientX - petLastX) >= 3) {
        const dir = Math.sign(e.clientX - petLastX);
        if (petDir && dir !== petDir) petTurns.push(now);
        petDir = dir;
    }
    petLastX = e.clientX;
    petTurns = petTurns.filter(t => now - t < 1000);
    if (petTurns.length >= 4 && now > petCooldown) { petCooldown = now + 3000; petTurns = []; lumiState.react('happy'); }
});
dom.lumi.addEventListener('mouseleave', () => { clearTimeout(shyTimer); shyShown = false; petLastX = null; petDir = 0; petTurns = []; });

// --- TRY A REACTION (Settings): plays a reaction, a working state or a mood on Lumi for a few seconds ---
const PREVIEW_ACTIVITIES = ['listening', 'thinking', 'checking', 'working', 'replying', 'speaking', 'waiting'];
const PREVIEW_MOODS = ['dance', 'music', 'focus', 'break', 'sleepy'];
let previewTimer = null, previewLevels = null;
function preview(name, label) {
    if (currentRun) return;  // never over a real request
    endPreview();
    previewing = true;
    syncPeek();
    if (PREVIEW_MOODS.includes(name)) { previewAmbient = name; syncAmbient(); }
    else if (PREVIEW_ACTIVITIES.includes(name)) {
        lumiState.setActivity(name);
        if (name === 'listening' || name === 'speaking') {  // made-up levels, so the ring and mouth move as they would
            const kind = name === 'listening' ? 'mic' : 'voice';
            let t = 0;
            previewLevels = setInterval(() => onLevel({ kind, value: Math.round(Math.abs(Math.sin(++t * 0.7)) * 90) / 100 }), 90);
        }
    } else lumiState.react(name);
    if (state === 'idle') showToast(label || name, 'toast', 2600);
    previewTimer = setTimeout(endPreview, PREVIEW_MOODS.includes(name) || PREVIEW_ACTIVITIES.includes(name) ? 3500 : 2600);
}
function endPreview() {
    clearTimeout(previewTimer);
    if (!previewing) return;
    clearInterval(previewLevels);
    previewLevels = null;
    onLevel({ kind: 'mic', end: true });
    onLevel({ kind: 'voice', end: true });
    if (previewAmbient) { previewAmbient = null; syncAmbient(); }
    if (!currentRun) lumiState.setActivity(null);
    previewing = false;
    syncPeek();
}

// --- COLLAPSING ---
// Panels close when the mouse leaves (or on Esc), never while you're pointing at them, typing, or waiting for Lumi.
// The command bar closes only on Esc, when you run something, or when you switch to another window.
let overIsland = false, overLumi = false;
let pointerInside = false;
// A newly opened panel can be smaller than the one before (dashboard -> focus), leaving the pointer outside it.
// It stays open until the pointer has been inside it once, or for 4 s.
let graceUntil = 0, pointerSeenInside = false;
function startGrace() { graceUntil = performance.now() + 4000; pointerSeenInside = false; }
function updatePointer() {
    pointerInside = overIsland || overLumi;
    syncPeek();  // the pointer coming near brings Lumi out
    if (pointerInside) pointerSeenInside = true;
    if (pointerInside) clearTimeout(collapseTimer); else scheduleCollapse(600);
}
// Stay open while typing or moving through the panel with the keyboard (not after a mere click)
function focusKeepsOpen() {
    const a = document.activeElement;
    if (a === dom.notesArea || (a === dom.chatInput && a.value)) return true;
    return a !== dom.island && a !== dom.chatInput && dom.island.contains(a) && a.matches(':focus-visible');
}
function scheduleCollapse(delay) {
    clearTimeout(collapseTimer);
    if (state === 'command' || (state === 'chat' && chatWaiting)) return;
    if (!pointerSeenInside) delay = Math.max(delay, graceUntil - performance.now());
    collapseTimer = setTimeout(() => {
        if (pointerInside || focusKeepsOpen() || (state === 'chat' && chatWaiting)) return;
        collapse();
    }, delay);
}
function collapse() {
    if (!EXPANDED.includes(state)) return;
    const wasCommand = state === 'command';
    if (dom.island.contains(document.activeElement)) document.activeElement.blur();
    window.updateState({ state: 'idle' });
    if (wasCommand) call('command_closed');
}
dom.island.addEventListener('mouseenter', () => { overIsland = true; updatePointer(); });
dom.island.addEventListener('mouseleave', () => { overIsland = false; updatePointer(); });
dom.lumi.addEventListener('mouseenter', () => { overLumi = true; updatePointer(); });
dom.lumi.addEventListener('mouseleave', () => { overLumi = false; updatePointer(); });
dom.notesArea.addEventListener('blur', () => { if (!pointerInside) scheduleCollapse(600); });
// Leaving the panel by keyboard closes it like leaving it with the mouse
dom.island.addEventListener('focusout', e => { if (!dom.island.contains(e.relatedTarget) && !pointerInside) scheduleCollapse(600); });
// Esc stops what Lumi is doing first; pressed again (or with nothing running) it closes things as before
document.addEventListener('keydown', e => {
    if (e.key !== 'Escape') return;
    if (cancelRun()) { e.preventDefault(); return; }
    if (tourStep >= 0) endTour(false);
    hideCard();
    collapse();
});
window.addEventListener('blur', () => { if (state === 'command') { window.updateState({ state: 'idle' }); } });

// --- ACTIONS ---
// Click (or Enter/Space on) the compact island: now playing opens the player, a running timer the focus panel,
// anything else the dashboard. Clicks that ended a drag are ignored.
function openFromCompact() {
    if (state !== 'idle') return;
    if (dom.island.classList.contains('act-media')) call('open_music');
    else if (dom.island.classList.contains('act-focus')) call('open_focus');
    else call('open_dashboard');
}
let downX = 0, downY = 0;
dom.island.addEventListener('mousedown', e => { downX = e.screenX; downY = e.screenY; });
dom.island.addEventListener('click', e => {
    if (Math.hypot(e.screenX - downX, e.screenY - downY) > 5) return;
    if (e.target.closest('button, input, textarea, .chat-log')) return;
    openFromCompact();
});
dom.island.addEventListener('keydown', e => {
    if (e.target !== dom.island || (e.key !== 'Enter' && e.key !== ' ')) return;
    e.preventDefault();
    openFromCompact();
});

dom.mic.addEventListener('click', e => { e.stopPropagation(); call('start_listening'); });
$('btn-notes').addEventListener('click', () => call('open_notes'));
dom.btnFocus.addEventListener('click', () => call('open_focus'));
document.querySelectorAll('[data-media]').forEach(b => b.addEventListener('click', () => call('media', b.dataset.media)));
$('menu-settings').addEventListener('click', () => { call('open_settings'); collapseSoon(); });
$('menu-hide').addEventListener('click', () => { collapseSoon(); call('hide_for', 60); });
$('menu-quit').addEventListener('click', () => call('quit'));
// After an action that's finished with the panel (starting focus, opening Settings), close it even under the mouse
function collapseSoon() { clearTimeout(collapseTimer); collapseTimer = setTimeout(collapse, 250); }

dom.notesArea.addEventListener('input', () => {
    dom.notesUi.classList.toggle('empty', !dom.notesArea.value.trim());
    clearTimeout(saveTimeout);
    saveTimeout = setTimeout(() => {
        call('save_note', dom.notesArea.value);
        dom.saveMsg.style.opacity = '1';
        setTimeout(() => dom.saveMsg.style.opacity = '0', 1000);
    }, 800);
});

// Removed manual drag logic to use Native Dragging
window.addEventListener('contextmenu', e => { e.preventDefault(); if (state !== 'command' && state !== 'chat') call('open_menu'); });

// Scroll on the island changes the volume, with a level shown in the island
let lastWheel = 0;
dom.island.addEventListener('wheel', e => {
    if (!prefs.scroll_volume || state !== 'idle') return;
    e.preventDefault();
    const now = performance.now();
    if (now - lastWheel < 60) return; // touchpads send a flood of small wheel events
    lastWheel = now;
    call('scroll', e.deltaY).then(v => { if (v) showVolume(v); });
}, { passive: false });

// --- COMMAND BAR ---
let cmdItems = [];     // what Enter and the arrow keys move through (pins or results)
let cmdSelected = 0;
let cmdSeq = 0;

function openCommandBar(pins) {
    reactToContext('surprised');  // summoned out of nowhere
    if (tourStep >= 0) endTour(false);
    hideCard();
    statusActive = false;
    dom.cmdInput.value = '';
    renderCommand({ pins, results: [] });
    setIslandState('command');
    setTimeout(() => dom.cmdInput.focus(), 30);
}

function glyph(name) { return `<svg class="icon"><use href="#i-${name}"/></svg>`; }
function iconFor(item) {
    if (item.icon) return `<img src="${item.icon}" alt="">`;
    if (item.glyph === 'lumi') return '<span class="glyph-lumi" aria-hidden="true"></span>';
    if (item.glyph) return glyph(item.glyph);
    return `<span class="glyph-tile">${escapeHtml((item.title || '?')[0].toUpperCase())}</span>`;
}

function renderCommand({ pins, results }) {
    cmdItems = results.length ? results : pins.map(p => ({ kind: 'app', id: p.id, title: p.name, icon: p.icon }));
    cmdSelected = 0;
    dom.cmdPins.innerHTML = results.length ? '' : pins.map((p, i) =>
        `<button class="cmd-pin" type="button" role="option" id="cmd-opt-${i}" data-index="${i}" tabindex="-1">${iconFor({ icon: p.icon, title: p.name })}<span class="ellipsis">${escapeHtml(p.name)}</span></button>`).join('');
    dom.cmdResults.innerHTML = results.map((r, i) =>
        `<li class="cmd-result" role="option" id="cmd-opt-${i}" data-index="${i}">${iconFor(r)}<span class="name ellipsis">${escapeHtml(r.title)}</span><span class="hint">${r.kind === 'app' ? 'Open' : r.kind === 'ask' ? 'Ask' : 'Run'} ↵</span></li>`).join('');
    highlightCommand();
    layoutCommand();
}

function layoutCommand() {
    const pinsH = dom.cmdPins.children.length ? 70 : 0;
    const rows = dom.cmdResults.children.length;
    const h = 8 + 40 + 6 + (pinsH ? pinsH + 6 : 0) + (rows ? rows * 42 + 6 : 0) + 20 + 10;
    dom.island.style.height = h + 'px';
    if (state === 'command') placeLumi();
}

function highlightCommand() {
    const nodes = [...dom.cmdPins.children, ...dom.cmdResults.children];
    nodes.forEach((n, i) => { n.classList.toggle('selected', i === cmdSelected); n.setAttribute('aria-selected', i === cmdSelected); });
    // Screen readers follow the highlight while the keyboard stays in the field
    dom.cmdInput.setAttribute('aria-controls', dom.cmdPins.children.length ? 'cmd-pins' : 'cmd-results');
    dom.cmdInput.setAttribute('aria-expanded', nodes.length > 0);
    if (nodes[cmdSelected]) dom.cmdInput.setAttribute('aria-activedescendant', nodes[cmdSelected].id);
    else dom.cmdInput.removeAttribute('aria-activedescendant');
}

function runCommand(item) {
    if (!item) return;
    if (item.kind === 'ask') {
        // Questions move straight into the chat panel; the keyboard stays with the island
        pendingQuestion = item.arg;
        call('open_chat');
        return;
    }
    call('run', item).then(confirmation => {
        if (confirmation) showToast(confirmation);
    });
    collapse();
}

dom.cmdInput.addEventListener('input', () => {
    const seq = ++cmdSeq;
    call('search', dom.cmdInput.value).then(res => { if (res && seq === cmdSeq && state === 'command') renderCommand(res); });
});
dom.cmdInput.addEventListener('keydown', e => {
    if (['ArrowDown', 'ArrowUp', 'ArrowRight', 'ArrowLeft'].includes(e.key)) {
        if (!cmdItems.length) return;
        const pinsMode = dom.cmdPins.children.length > 0;
        const forward = e.key === 'ArrowDown' || (pinsMode && e.key === 'ArrowRight');
        const back = e.key === 'ArrowUp' || (pinsMode && e.key === 'ArrowLeft');
        if (!forward && !back) return;
        e.preventDefault();
        cmdSelected = (cmdSelected + (forward ? 1 : -1) + cmdItems.length) % cmdItems.length;
        highlightCommand();
    } else if (e.key === 'Enter') {
        e.preventDefault();
        runCommand(cmdItems[cmdSelected]);
    }
});
[dom.cmdPins, dom.cmdResults].forEach(list => {
    list.addEventListener('mousemove', e => {
        const el = e.target.closest('[data-index]');
        if (el && +el.dataset.index !== cmdSelected) { cmdSelected = +el.dataset.index; highlightCommand(); }
    });
    list.addEventListener('mousedown', e => e.preventDefault()); // keep focus in the input
    list.addEventListener('click', e => {
        const el = e.target.closest('[data-index]');
        if (el) runCommand(cmdItems[+el.dataset.index]);
    });
});

// --- ONBOARDING ---
const TOUR = [
    { text: () => "Hi, I'm Lumi. Click the island any time to see your PC at a glance.", body: 'highlight-island' },
    { text: () => 'Hover over me and press the mic to talk to me, or click me to type.', body: 'show-mic' },
    { text: () => `Press <kbd>${escapeHtml(prefs.hotkey)}</kbd> anywhere to open apps, start focus, or ask me something.`, body: '' },
    { text: () => "You're all set. Right-click the island for Settings.", body: '' }
];
let tourStep = -1;
function startOnboarding() {
    if (state !== 'idle') window.updateState({ state: 'idle' });
    tourStep = 0;
    renderTour();
}
function renderTour() {
    const step = TOUR[tourStep];
    const last = tourStep === TOUR.length - 1;
    showCard({
        html: step.text(), step: `${tourStep + 1} of ${TOUR.length}`,
        primary: last ? 'Done' : 'Next', secondary: last ? '' : 'Skip',
        onPrimary: () => { if (last) endTour(true); else { tourStep++; renderTour(); } },
        onSecondary: () => endTour(false)
    });
    document.body.classList.remove('highlight-island', 'show-mic');
    if (step.body) document.body.classList.add(step.body);
}
function endTour(finished) {
    if (tourStep < 0) return;
    tourStep = -1;
    hideCard();
    call('finish_onboarding');
    if (finished) showToast("You're set");
}

// --- HIT AREAS AND WINDOW HEIGHT ---
// The window background is see-through and click-through; Python paints these shapes
// (slightly inset, hidden behind the page) so only the island, Lumi, the mic and the card catch the mouse.
// It also reports how tall the content is, so the window can grow to fit it. Measured only while something moves.
const hitTargets = [
    { el: dom.island, inset: 2 },
    { el: dom.lumiBody, inset: 4, ellipse: true },
    { el: dom.mic, inset: 1, ellipse: true },
    { el: dom.card, inset: 2 }
];
let lastHitAreas = '';

function contentBottom() {
    let bottom = dom.island.getBoundingClientRect().bottom;
    if (prefs.lumi_visible) bottom = Math.max(bottom, dom.lumi.getBoundingClientRect().bottom + 22);
    if (dom.bubble.classList.contains('visible')) bottom = Math.max(bottom, dom.bubble.getBoundingClientRect().bottom);
    if (dom.card.classList.contains('visible')) bottom = Math.max(bottom, dom.card.getBoundingClientRect().bottom);
    return Math.ceil(bottom);
}

function reportHitAreas() {
    const a = api();
    if (!a || !a.set_hit_areas) return false;
    const shapes = [];
    for (const t of hitTargets) {
        const style = getComputedStyle(t.el);
        const r = t.el.getBoundingClientRect();
        if (style.opacity === '0' || style.display === 'none' || r.width <= 2 * t.inset || r.height <= 2 * t.inset) continue;
        shapes.push({
            x: Math.round(r.left + t.inset), y: Math.round(r.top + t.inset),
            w: Math.round(r.width - 2 * t.inset), h: Math.round(r.height - 2 * t.inset),
            ellipse: !!t.ellipse,
            radius: Math.round(Math.max(0, Math.min(parseFloat(style.borderTopLeftRadius) || 0, r.height / 2) - t.inset))
        });
    }
    const height = contentBottom();
    const json = JSON.stringify(shapes) + height;
    if (json !== lastHitAreas) {
        lastHitAreas = json;
        a.set_hit_areas(shapes, window.innerWidth, height).then(ok => { if (!ok) { lastHitAreas = ''; setTimeout(trackHitAreas, 300); } });
    }
    return true;
}

let hitLoop = null, loopUntil = 0, runningTransitions = 0, lastTransitionEvent = 0;
function trackHitAreas(ms = 150) {
    loopUntil = Math.max(loopUntil, performance.now() + ms);
    if (hitLoop) return;
    const step = () => {
        if (!reportHitAreas()) { hitLoop = null; setTimeout(trackHitAreas, 300); return; }
        const now = performance.now();
        // A transition that never reports its end must not keep the loop alive for ever
        if (now - lastTransitionEvent > 2000) runningTransitions = 0;
        hitLoop = (now < loopUntil || runningTransitions > 0) ? requestAnimationFrame(step) : null;
    };
    hitLoop = requestAnimationFrame(step);
}
document.addEventListener('transitionrun', () => { runningTransitions++; lastTransitionEvent = performance.now(); trackHitAreas(); }, true);
const transitionDone = () => { runningTransitions = Math.max(0, runningTransitions - 1); lastTransitionEvent = performance.now(); trackHitAreas(100); };
document.addEventListener('transitionend', transitionDone, true);
document.addEventListener('transitioncancel', transitionDone, true);
window.addEventListener('resize', () => { lastHitAreas = ''; trackHitAreas(); });

// --- STARTUP ---
function init() {
    call('init').then(info => {
        if (!info) return;
        applyPrefs(info.prefs);
        if (info.media) { media = info.media; renderMedia(); }
        if (info.hotkey_error) showSettingsCard(info.hotkey_error);
        if (info.onboarding) setTimeout(startOnboarding, 1200);
        else if (info.greeting) setTimeout(() => greet(info.greeting), 800);
    });
    call('activity_snapshot').then(e => { if (e) { currentRun = e.run; lastSeq = e.seq - 1; onActivity(e); } });
    // Follow Windows if its reduced-motion setting changes while Lumi is running
    reducedMotionQuery.addEventListener('change', () => applyPrefs({}));
    lastHitAreas = '';
    trackHitAreas();
}
if (api() && api().init) init();
else window.addEventListener('pywebviewready', init);
trackHitAreas();
