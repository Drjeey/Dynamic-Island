// Lumi's guides: a short walk through each feature. The island plays them (island.js), and Settings lists them.
// Each step can open a panel first (`panel`), ring one control (`spot`, a CSS selector) and light up the island or
// the mic (`body`). Text is plain: [[...]] becomes a key cap, and {hotkey} your shortcut.
// `opens` is the panel whose first visit offers the guide once. The ids are also listed in lumi/api.py (GUIDES).
window.LUMI_GUIDES = [
    {
        id: 'start', title: 'Getting started', blurb: 'The island, Lumi and your shortcut, in four steps',
        steps: [
            { panel: 'idle', body: 'highlight-island', text: "Hi, I'm Lumi. Click the island any time to see your PC at a glance." },
            { panel: 'idle', body: 'show-mic', text: 'Hover over me and press the mic to talk to me, or click me to type.' },
            { panel: 'idle', text: 'Press [[{hotkey}]] anywhere to open apps, start focus, or ask me something.' },
            { panel: 'idle', text: "Right-click the island for Settings. Forgot something? Every guide is under Guides in that menu, or type \"guide\" after [[{hotkey}]]." }
        ]
    },
    {
        id: 'ask', title: 'Asking Lumi', blurb: 'Typing, talking, and what Lumi can do for you', opens: 'chat',
        steps: [
            { panel: 'chat', spot: '#chat-input', text: 'Type a question here and press [[Enter]]. I answer here, and I remember the last few things we talked about.' },
            { panel: 'chat', spot: '#chat-input', text: 'I can also do things: "start a 25 minute focus", "add milk to my note", "open Spotify", "turn the volume down".' },
            { panel: 'idle', body: 'show-mic', text: 'Rather talk? Hover over me and press the mic, then just speak. Settings has my voice under "Lumi and voice".' },
            { panel: 'idle', text: 'Press [[Esc]] to stop me in the middle of an answer.' }
        ]
    },
    {
        id: 'command', title: 'The command bar', blurb: 'One shortcut for apps, focus, notes, agents and questions', opens: 'command',
        steps: [
            { panel: 'command', spot: '#cmd-input', text: 'This is the command bar. It opens with [[{hotkey}]] from anywhere. Type an app\'s name and press [[Enter]] to open it.' },
            { panel: 'command', spot: '#cmd-input', text: 'Shortcuts: "focus 45" starts a timer, "note call mum" adds to your note, "talk" starts listening, "next" skips the song.' },
            { panel: 'command', spot: '#cmd-input', text: '"claude fix the login bug" or "codex ..." hands a task to a coding agent. A question goes to me, and anything else can be searched on the web.' },
            { panel: 'command', spot: '#cmd-input', text: 'Type "guide" here whenever you want one of these tours again.' }
        ]
    },
    {
        id: 'dashboard', title: 'Your PC at a glance', blurb: 'Memory, battery, network and quick buttons', opens: 'dashboard',
        steps: [
            { panel: 'dashboard', spot: '#ram-ring', text: 'Click the island to see this: how much memory is in use...' },
            { panel: 'dashboard', spot: '#bat-ring', text: '...your battery (or that you\'re plugged in), and whether you\'re online.' },
            { panel: 'dashboard', spot: '#btn-notes', text: 'These buttons open your note, a focus session and the coding agents.' }
        ]
    },
    {
        id: 'focus', title: 'Focus sessions', blurb: 'Timers, breaks and your weekly summary', opens: 'focus',
        steps: [
            { panel: 'focus', spot: '#fp-chips', text: 'Pick how long you want to focus...' },
            { panel: 'focus', spot: '#fp-start', text: '...and start. The countdown stays on the island while you work, and I keep quiet.' },
            { panel: 'focus', spot: '#fp-break', text: 'When it ends I suggest a short break. You can take one any time here too.' },
            { panel: 'focus', spot: '#fp-today', text: 'Your focus time adds up here. Type "summary" in the command bar for your week.' }
        ]
    },
    {
        id: 'notes', title: 'Your quick note', blurb: 'A scratch pad that saves as you type', opens: 'notes',
        steps: [
            { panel: 'notes', spot: '#notes-area', text: 'Your quick note. It saves as you type, and it stays on this PC.' },
            { panel: 'notes', spot: '#notes-area', text: 'Add to it from anywhere: "note buy bread" in the command bar, or ask me "add bread to my note".' }
        ]
    },
    {
        id: 'music', title: 'Music', blurb: 'What\'s playing, and controlling it', opens: 'music',
        steps: [
            { panel: 'music', spot: '#btn-play', text: 'Whatever is playing (Spotify, a browser tab, any player) shows here. Play, pause and skip from the island.' },
            { panel: 'idle', body: 'highlight-island', text: 'Scroll over the island to change the volume. Ask me "what\'s playing?" or say "next song".' }
        ]
    },
    {
        id: 'agents', title: 'Coding agents', blurb: 'Run Claude Code or Codex, follow them, and reply', opens: 'agents',
        steps: [
            { panel: 'agents', spot: '#ag-pick', text: 'Pick Claude Code or Codex ([[Ctrl+1]] / [[Ctrl+2]]). The panel shows that agent\'s sessions, and a blue dot means one is working.' },
            { panel: 'agents', spot: '#ag-edits', text: 'Enter (or the blue arrow) runs it read only: the agent may only look. "Run with edits" lets it change files, and the first time in a folder I ask you to confirm.' },
            { panel: 'agents', spot: '#ag-folder', text: 'Choose the folder it works in, then type a task below and press [[Enter]].' },
            { panel: 'agents', spot: '#ag-nodes', text: 'Each step it takes appears here. Click an answer to read all of it.' },
            { panel: 'agents', spot: '#ag-input', text: 'When it finishes, type to reply in the same chat, or press "New chat" to start fresh. "Show where it\'s saved" finds the chat on your PC.' },
            { panel: 'agents', text: 'Sessions you run yourself in Claude Code or the Codex app show up here too, so you can follow them from the island.' }
        ]
    },
    {
        id: 'looks', title: 'Lumi\'s looks and sounds', blurb: 'Skins, colours, seasonal looks and sound effects',
        steps: [
            { panel: 'idle', text: 'I come in different skins and colours. They live in Settings, under "Lumi and voice".' },
            { panel: 'idle', settings: true, text: 'I\'ve opened Settings for you. Turn on seasonal looks for a new Christmas outfit each day, and sounds if you\'d like little effects.' }
        ]
    },
    {
        id: 'menu', title: 'The menu', blurb: 'Settings, hiding the island, and these guides',
        steps: [
            { panel: 'menu', spot: '#menu-settings', text: 'Right-click the island for this menu. Settings has everything you can change.' },
            { panel: 'menu', spot: '#menu-hide', text: 'Hide 1 hour tucks the island away. It also hides by itself in full-screen apps.' },
            { panel: 'menu', spot: '#menu-guides', text: 'And Guides brings back any of these tours.' }
        ]
    }
];
