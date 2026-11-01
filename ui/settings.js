const $ = id => document.getElementById(id);
const api = () => window.pywebview && window.pywebview.api;

// --- NAVIGATION ---
document.querySelectorAll('.nav').forEach(b => b.addEventListener('click', () => {
    document.querySelectorAll('.nav').forEach(n => n.classList.toggle('selected', n === b));
    document.querySelectorAll('.page').forEach(p => { p.hidden = p.id !== 'page-' + b.dataset.page; });
}));

// --- SAVING ---
function save(key, value, messageEl) {
    return api().set(key, value).then(res => {
        if (messageEl) {
            messageEl.textContent = res.ok ? 'Saved' : res.error;
            messageEl.className = 'message ' + (res.ok ? 'ok' : 'error');
            if (res.ok) setTimeout(() => { if (messageEl.textContent === 'Saved') messageEl.textContent = ''; }, 2000);
        }
        return res;
    });
}

function syncPositionRow() {
    const free = document.querySelector('input[name=anchor]:checked')?.value === 'free';
    $('row-monitor').classList.toggle('disabled', free);
    $('monitor').disabled = free;
}

let values = {}, providers = {}, keys = {};

function load() {
    api().get().then(res => {
        ({ values, providers, keys } = res);
        const { monitors, hotkey_error, colors } = res;
        for (const key of TOGGLES) $(key).checked = !!values[key];
        renderSwatches(colors, values.lumi_color);
        document.querySelectorAll('input[name=anchor]').forEach(r => { r.checked = r.value === values.anchor; });
        $('monitor').innerHTML = monitors.map((m, i) => `<option value="${i}">${m}</option>`).join('');
        $('monitor').value = String(Math.min(values.monitor, monitors.length - 1));
        $('motion').value = values.motion === 'reduced' ? 'off' : values.motion; // older setting name
        $('lumi_idle').value = values.lumi_idle === 'always' ? 'always' : 'peek';
        $('row-lumi-idle').classList.toggle('disabled', !values.lumi_visible);
        $('hotkey').value = values.hotkey;
        $('voice_mode').value = values.voice_mode;
        $('live_model').value = values.live_model;
        $('custom_url').value = values.custom_url;
        $('ai_provider').innerHTML = Object.entries(providers).map(([name, p]) => `<option value="${name}">${p.label}</option>`).join('');
        $('ai_provider').value = values.ai_provider in providers ? values.ai_provider : 'gemini';
        syncProvider();
        if (hotkey_error) { $('msg-hotkey').textContent = hotkey_error; $('msg-hotkey').className = 'message error'; }
        syncPositionRow();
        syncVoiceRow();
    });
}

const TOGGLES = ['auto_start', 'hide_in_fullscreen', 'scroll_volume', 'lumi_visible', 'celebrations', 'weekly_summary'];
const COLOR_NAMES = { cloud: 'Cloud', peach: 'Peach', mint: 'Mint', sky: 'Sky', lilac: 'Lilac', butter: 'Butter' };

// Lumi's colour: a swatch per preset, with a small live preview of Lumi on the island's black
function renderSwatches(colors, current) {
    $('swatches').innerHTML = Object.entries(colors).map(([key, hex]) =>
        `<label class="swatch" title="${COLOR_NAMES[key] || key}"><input type="radio" name="lumi_color" value="${key}" aria-label="${COLOR_NAMES[key] || key}" ${key === current ? 'checked' : ''}><span style="background:${hex}"></span></label>`).join('');
    $('preview-blob').style.background = colors[current] || colors.cloud;
    document.querySelectorAll('input[name=lumi_color]').forEach(r => r.addEventListener('change', () => {
        $('preview-blob').style.background = colors[r.value];
        save('lumi_color', r.value);
    }));
}

// The rows below the provider follow the chosen provider: its key, its model, and (for "Other") its server
function syncProvider() {
    const name = $('ai_provider').value, p = providers[name], key = keys[name];
    $('row-url').classList.toggle('gone', name !== 'custom');
    $('row-backup').classList.toggle('gone', name !== 'gemini');
    $('gemini_backup_model').value = values.gemini_backup_model || '';
    $('key-title').textContent = name === 'custom' ? 'API key (optional)' : p.label + ' API key';
    $('key-help').textContent = key.from_env ? `The ${key.env} environment variable is set and is used first.`
        : name === 'custom' ? 'Only if your server asks for one. Stored in Windows Credential Manager.'
        : 'Needed for Lumi to answer. Stored in Windows Credential Manager, not in a file.';
    $('api_key').placeholder = key.set ? 'Saved (type to replace)' : 'Paste your key';
    $('remove-key').hidden = !key.set;
    $('chat_model').value = values[p.model_key] || '';
    $('model-list').innerHTML = p.models.map(m => `<option value="${m}">`).join('');
    $('model-help').textContent = name === 'custom' ? 'The model name your server uses, for example llama3.2. Small local models may not use tools well.'
        : `Used for typed chat and standard voice. Check it's available on your ${p.label} account.`;
    syncVoiceRow();
}

function syncVoiceRow() {
    const liveOk = !!(providers[$('ai_provider').value] || {}).live;
    $('voice_mode').querySelector('option[value=live]').disabled = !liveOk;
    $('row-live-model').classList.toggle('disabled', $('voice_mode').value !== 'live' || !liveOk);
    const m = $('msg-voice');
    if (!liveOk && $('voice_mode').value === 'live') { m.textContent = 'Live voice needs Gemini, so the mic uses standard voice for now.'; m.className = 'message'; }
    else if (m.textContent.startsWith('Live voice needs')) m.textContent = '';
}

// The key is written to Windows Credential Manager and never read back into this page
function saveKey(value) {
    return api().set_api_key(value, $('ai_provider').value).then(res => {
        const m = $('msg-ai');
        m.textContent = res.ok ? (value ? 'Key saved' : 'Key removed') : res.error;
        m.className = 'message ' + (res.ok ? 'ok' : 'error');
        if (res.ok) { $('api_key').value = ''; load(); }
    });
}

// Toggles and selects save as soon as they change
for (const key of TOGGLES) {
    $(key).addEventListener('change', () => save(key, $(key).checked));
}
document.querySelectorAll('input[name=anchor]').forEach(r => r.addEventListener('change', () => { save('anchor', r.value); syncPositionRow(); }));
$('monitor').addEventListener('change', () => save('monitor', parseInt($('monitor').value, 10)));
$('motion').addEventListener('change', () => save('motion', $('motion').value));
$('lumi_idle').addEventListener('change', () => save('lumi_idle', $('lumi_idle').value));
$('lumi_visible').addEventListener('change', () => $('row-lumi-idle').classList.toggle('disabled', !$('lumi_visible').checked));

// Text fields save on their Save button (or Enter)
$('form-hotkey').addEventListener('submit', e => { e.preventDefault(); save('hotkey', $('hotkey').value, $('msg-hotkey')).then(r => { if (r.ok) load(); }); });
$('ai_provider').addEventListener('change', () => {
    const name = $('ai_provider').value;
    save('ai_provider', name, $('msg-ai')).then(r => { if (r.ok) values.ai_provider = name; });
    syncProvider();
});
$('form-model').addEventListener('submit', e => {
    e.preventDefault();
    const key = providers[$('ai_provider').value].model_key, value = $('chat_model').value.trim();
    save(key, value, $('msg-ai')).then(r => { if (r.ok) values[key] = value; });
});
$('form-backup').addEventListener('submit', e => {
    e.preventDefault();
    const value = $('gemini_backup_model').value.trim();
    save('gemini_backup_model', value, $('msg-ai')).then(r => { if (r.ok) values.gemini_backup_model = value; });
});
$('form-url').addEventListener('submit', e => {
    e.preventDefault();
    const value = $('custom_url').value.trim();
    save('custom_url', value, $('msg-ai')).then(r => { if (r.ok) values.custom_url = value; });
});
$('form-key').addEventListener('submit', e => {
    e.preventDefault();
    const value = $('api_key').value.trim();
    if (value) saveKey(value);
});
$('remove-key').addEventListener('click', () => saveKey(''));
$('voice_mode').addEventListener('change', () => { save('voice_mode', $('voice_mode').value, $('msg-voice')).then(syncVoiceRow); syncVoiceRow(); });
$('form-live-model').addEventListener('submit', e => { e.preventDefault(); save('live_model', $('live_model').value.trim(), $('msg-voice')); });
$('replay').addEventListener('click', () => api().replay_tour());
document.querySelectorAll('[data-preview]').forEach(b => b.addEventListener('click', () => api().preview(b.dataset.preview)));

if (api() && api().get) load();
else window.addEventListener('pywebviewready', load);
