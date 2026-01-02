import json
import threading
import time
import webview
import ctypes
import os
import shutil
import random
import string
import tempfile
import subprocess
import math
from ctypes import wintypes
from pathlib import Path

# --- AI LIBRARIES ---
# Using the NEW Google GenAI SDK
try:
    from google import genai
except ImportError:
    print("CRITICAL: Please run 'pip install google-genai'")
    genai = None

import speech_recognition as sr
import pyttsx3

# --- CONFIGURATION ---
# !!! PASTE YOUR API KEY HERE !!!
GEMINI_API_KEY = '# !!! PASTE YOUR API KEY HERE !!!' 

CONFIG_PATH = Path('config.json')
NOTES_PATH = Path('notes.txt')

DEFAULT_CONFIG = {
    "geometry": {"width": 600, "height": 350, "x": None, "y": 0},
    "auto_start": False
}

# --- EMBEDDED UI ---
HTML_CODE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <style>
        /* --- CORE --- */
        html, body {
            background: transparent !important;
            background-color: rgba(0,0,0,0) !important;
            margin: 0; padding: 0; 
            width: 100vw; height: 100vh;
            overflow: hidden !important; 
            font-family: "SF Pro Display", -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
            user-select: none;
        }

        /* --- THE ISLAND --- */
        /* 'pywebview-drag-region' enables native, smooth dragging without Python code */
        #island {
            position: absolute; 
            top: 10px; left: 50%; transform: translateX(-50%);
            background: rgba(12, 12, 12, 0.96);
            backdrop-filter: blur(40px) saturate(180%);
            -webkit-backdrop-filter: blur(40px) saturate(180%);
            color: white; border-radius: 40px;
            border: 1px solid rgba(255, 255, 255, 0.12);
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.7), inset 0 1px 1px rgba(255, 255, 255, 0.15);
            width: 120px; height: 35px;
            display: flex; align-items: center; justify-content: center;
            transition: all 0.6s cubic-bezier(0.19, 1, 0.22, 1);
            cursor: grab; z-index: 100;
        }
        #island:active { cursor: grabbing; transform: translateX(-50%) scale(0.98); }

        /* --- LUMI (THE AI PET) --- */
        #lumi-container {
            position: absolute;
            top: 55px; left: 50%; transform: translateX(-50%);
            width: 60px; height: 50px;
            z-index: 90; pointer-events: auto; cursor: pointer;
            transition: top 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
        }

        #lumi-body {
            width: 100%; height: 100%;
            background: #f2f2f7;
            border-radius: 50%;
            position: relative;
            box-shadow: inset -2px -5px 10px rgba(0,0,0,0.1), 0 10px 20px rgba(0,0,0,0.3);
            animation: organic 6s ease-in-out infinite;
            transition: background 0.3s, transform 0.2s;
            transform-origin: top center;
        }

        #lumi-face {
            position: absolute; top: 45%; left: 50%;
            transform: translate(-50%, -50%);
            display: flex; gap: 14px;
            align-items: center; justify-content: center;
        }

        .eye {
            width: 8px; height: 12px;
            background: #1c1c1e;
            border-radius: 10px;
            position: relative; overflow: hidden;
            transition: height 0.1s, transform 0.1s;
        }
        .eye::after {
            content: ''; position: absolute; top: 2px; right: 2px;
            width: 3px; height: 3px; background: white; border-radius: 50%; opacity: 0.8;
        }

        /* MIC OVERLAY */
        #mic-btn {
            position: absolute; bottom: -25px; left: 50%; transform: translateX(-50%);
            width: 28px; height: 28px; border-radius: 50%;
            background: rgba(255,255,255,0.15); backdrop-filter: blur(5px);
            display: flex; align-items: center; justify-content: center;
            opacity: 0; transition: 0.3s; color: white; font-size: 14px;
            border: 1px solid rgba(255,255,255,0.2);
            cursor: pointer;
        }
        #lumi-container:hover #mic-btn { opacity: 1; bottom: -35px; }
        #mic-btn:hover { background: #0A84FF; transform: translateX(-50%) scale(1.1); }

        /* SPEECH BUBBLE */
        #speech-bubble {
            position: absolute; top: 115px; left: 50%; transform: translateX(-50%) scale(0.8);
            background: rgba(30, 30, 30, 0.95); border: 1px solid rgba(255,255,255,0.1);
            color: #eee; padding: 10px 16px; border-radius: 16px;
            font-size: 13px; font-weight: 500; text-align: center;
            pointer-events: none; opacity: 0; max-width: 250px;
            transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            box-shadow: 0 5px 15px rgba(0,0,0,0.4); z-index: 85;
        }
        #speech-bubble.visible { transform: translateX(-50%) scale(1); opacity: 1; }

        /* --- ANIMATIONS & STATES --- */
        @keyframes organic { 0%, 100% { border-radius: 60% 40% 30% 70% / 60% 30% 70% 40%; } 50% { border-radius: 30% 60% 70% 40% / 50% 60% 30% 60%; } }
        @keyframes pulse-listen { 0% { box-shadow: 0 0 0 0 rgba(10, 132, 255, 0.7); } 70% { box-shadow: 0 0 0 15px rgba(10, 132, 255, 0); } 100% { box-shadow: 0 0 0 0 rgba(10, 132, 255, 0); } }
        @keyframes bounce-speak { 0%, 100% { transform: scaleY(1); } 50% { transform: scaleY(1.1); } }

        /* AI States */
        .mood-listening #lumi-body { background: #0A84FF; animation: pulse-listen 1.5s infinite; }
        .mood-speaking #lumi-body { background: #32D74B; animation: bounce-speak 0.2s infinite; }
        
        .mood-speaking .eye { height: 2px; width: 10px; } /* Squint when talking */

        /* Normal States */
        .mood-stress #lumi-body { background: #ff453a; animation: organic 0.2s infinite; }

        /* --- ISLAND STATES --- */
        #island.idle { width: 120px; height: 35px; }
        #island.dashboard { width: 460px; height: 110px; border-radius: 55px; }
        #island.music { width: 340px; height: 130px; border-radius: 55px; }
        #island.launcher { width: 360px; height: 90px; border-radius: 45px; }
        #island.focus { width: 260px; height: 70px; border-radius: 35px; background: #2a0000; border-color: #ff453a; }
        #island.notes { width: 300px; height: 180px; border-radius: 35px; background: rgba(20, 20, 20, 0.98); flex-direction: column; justify-content: flex-start; }

        /* --- CONTENT --- */
        .content { display: flex; width: 100%; height: 100%; align-items: center; justify-content: center; opacity: 0; pointer-events: none; position: absolute; transition: opacity 0.3s ease; }
        #island.dashboard #dashboard-ui, #island.music #music-ui, #island.launcher #launcher-ui, #island.focus #focus-ui, #island.notes #notes-ui { opacity: 1; pointer-events: auto; }

        /* --- WIDGETS --- */
        .stats-container { display: flex; gap: 30px; }
        .stat-item { display: flex; align-items: center; gap: 10px; cursor: pointer; transition: 0.3s; }
        .stat-item:hover { transform: scale(1.1); }
        .ring { width: 48px; height: 48px; border-radius: 50%; background: conic-gradient(var(--color) var(--pct), rgba(255,255,255,0.05) 0deg); display: flex; align-items: center; justify-content: center; position: relative; }
        .ring::after { content: ''; position: absolute; width: 38px; height: 38px; background: #0c0c0c; border-radius: 50%; }
        .ring i { position: relative; z-index: 2; font-size: 16px; color: var(--color); }
        .stat-text { display: flex; flex-direction: column; }
        .stat-val { font-size: 17px; font-weight: 700; letter-spacing: -0.5px; }
        .stat-label { font-size: 9px; color: #888; font-weight: 700; letter-spacing: 0.5px; margin-top: 2px;}

        /* --- NOTES --- */
        #notes-ui { width: 100%; height: 100%; padding: 20px; box-sizing: border-box; flex-direction: column; }
        .notes-header { font-size: 11px; color: #666; font-weight: 700; text-transform: uppercase; width: 100%; margin-bottom: 5px; display: flex; justify-content: space-between; }
        #notes-area { width: 100%; height: 100%; background: transparent; border: none; color: #eee; font-size: 15px; line-height: 1.4; resize: none; outline: none; font-family: inherit; }
        #notes-area::-webkit-scrollbar { width: 0; }
        .save-indicator { color: #32d74b; opacity: 0; transition: 0.3s; font-size: 10px; }

        /* --- LAUNCHER --- */
        #launcher-ui { gap: 30px; }
        .app-icon { width: 50px; height: 50px; border-radius: 14px; background: rgba(255,255,255,0.08); backdrop-filter: blur(10px); display: flex; align-items: center; justify-content: center; font-size: 22px; cursor: pointer; transition: 0.2s; }
        .app-icon:hover { background: rgba(255,255,255,0.2); transform: translateY(-5px) scale(1.05); }

        /* --- MISC --- */
        #focus-ui { gap: 15px; color: #ff453a; font-family: monospace; font-size: 26px; font-weight: 700; }
        .btn-stop { width: 35px; height: 35px; border-radius: 50%; background: rgba(255,69,58,0.2); display: flex; align-items: center; justify-content: center; cursor: pointer; font-size: 18px; }
        #music-ui { flex-direction: column; padding: 20px; }
        .music-top { display: flex; width: 100%; align-items: center; gap: 15px; margin-bottom: 15px; }
        .album-art { width: 45px; height: 45px; border-radius: 12px; background: linear-gradient(135deg, #a18cd1, #fbc2eb); display: flex; align-items: center; justify-content: center; }
        .track-info { flex: 1; display: flex; flex-direction: column; }
        .track-title { font-size: 14px; font-weight: 600; white-space: nowrap; }
        .controls { display: flex; width: 100%; justify-content: space-evenly; }
        .btn-media { color: white; font-size: 24px; cursor: pointer; opacity: 0.7; transition: 0.2s; }

    </style>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
</head>
<body>
    
    <div id="lumi-container" class="mood-idle">
        <div id="lumi-body">
            <div id="lumi-face">
                <div class="eye" id="eye-l"></div>
                <div class="eye" id="eye-r"></div>
            </div>
        </div>
        <div id="mic-btn" onclick="pywebview.api.start_listening()"><i class="fa-solid fa-microphone"></i></div>
    </div>

    <div id="speech-bubble">Hi! Click the mic to chat.</div>

    <div id="island" class="idle pywebview-drag-region">
        <div class="content" id="dashboard-ui">
            <div class="stats-container">
                <div class="stat-item" id="btn-focus">
                    <div class="ring" id="ram-ring" style="--color:#0A84FF; --pct:0%"><i class="fa-solid fa-microchip"></i></div>
                    <div class="stat-text"><span class="stat-val" id="ram-val">0%</span><span class="stat-label">MEMORY</span></div>
                </div>
                <div class="stat-item">
                    <div class="ring" id="bat-ring" style="--color:#32D74B; --pct:0%"><i class="fa-solid fa-bolt"></i></div>
                    <div class="stat-text"><span class="stat-val" id="bat-val">100%</span><span class="stat-label">POWER</span></div>
                </div>
                <div class="stat-item" style="pointer-events:none">
                   <div class="stat-text" style="align-items:center"><span class="stat-val" id="ping-val">--</span><span class="stat-label">PING</span></div>
                </div>
                <div class="stat-item" onclick="pywebview.api.open_notes()">
                    <div class="ring" style="background:rgba(255,255,255,0.1)"><i class="fa-solid fa-pen"></i></div>
                </div>
            </div>
        </div>
        <div class="content" id="notes-ui">
            <div class="notes-header"><span>Quick Note</span><span class="save-indicator" id="save-msg">Saved ✓</span></div>
            <textarea id="notes-area" placeholder="Type something..." oninput="autoSave()"></textarea>
        </div>
        <div class="content" id="launcher-ui">
            <div class="app-icon" onclick="pywebview.api.launch('browser')"><i class="fa-brands fa-chrome"></i></div>
            <div class="app-icon" onclick="pywebview.api.launch('code')"><i class="fa-solid fa-terminal"></i></div>
            <div class="app-icon" onclick="pywebview.api.launch('files')"><i class="fa-solid fa-folder-open"></i></div>
            <div class="app-icon" onclick="pywebview.api.launch('calc')"><i class="fa-solid fa-calculator"></i></div>
        </div>
        <div class="content" id="focus-ui">
            <i class="fa-solid fa-hourglass-half"></i><span id="focus-timer">25:00</span>
            <div class="btn-stop" id="stop-focus"><i class="fa-solid fa-stop"></i></div>
        </div>
        <div class="content" id="music-ui">
            <div class="music-top"><div class="album-art"><i class="fa-solid fa-music"></i></div><div class="track-info"><span class="track-title">System Audio</span></div></div>
            <div class="controls">
                <div class="btn-media" onclick="pywebview.api.media('prev')"><i class="fa-solid fa-backward-step"></i></div>
                <div class="btn-media" onclick="pywebview.api.media('play')"><i class="fa-solid fa-circle-play" style="font-size:32px"></i></div>
                <div class="btn-media" onclick="pywebview.api.media('next')"><i class="fa-solid fa-forward-step"></i></div>
            </div>
        </div>
    </div>

    <script>
        const dom = {
            island: document.getElementById('island'),
            lumi: document.getElementById('lumi-container'),
            bubble: document.getElementById('speech-bubble'),
            eyeL: document.getElementById('eye-l'), eyeR: document.getElementById('eye-r'),
            ramRing: document.getElementById('ram-ring'), batRing: document.getElementById('bat-ring'),
            ramVal: document.getElementById('ram-val'), batVal: document.getElementById('bat-val'),
            pingVal: document.getElementById('ping-val'), focusTime: document.getElementById('focus-timer'),
            btnFocus: document.getElementById('btn-focus'), btnStopFocus: document.getElementById('stop-focus'),
            notesArea: document.getElementById('notes-area'), saveMsg: document.getElementById('save-msg')
        };
        
        let timer = null; let saveTimeout;

        function showBubble(text, time=4000) {
            dom.bubble.textContent = text;
            dom.bubble.classList.add('visible');
            setTimeout(() => dom.bubble.classList.remove('visible'), time);
        }

        // --- EYE TRACKING ---
        document.addEventListener('mousemove', (e) => {
            if(dom.lumi.classList.contains('mood-idle')) {
                const rect = dom.lumi.getBoundingClientRect();
                const anchorX = rect.left + rect.width / 2; const anchorY = rect.top + rect.height / 2;
                const angleRad = Math.atan2(e.clientY - anchorY, e.clientX - anchorX);
                const dist = Math.min(3, Math.hypot(e.clientX - anchorX, e.clientY - anchorY) / 50);
                const moveX = Math.cos(angleRad) * dist; const moveY = Math.sin(angleRad) * dist;
                dom.eyeL.style.transform = `translate(${moveX}px, ${moveY}px)`;
                dom.eyeR.style.transform = `translate(${moveX}px, ${moveY}px)`;
            }
        });

        // --- STATE ENGINE ---
        window.updateState = function(msg) {
            const { state, data } = msg;
            dom.island.className = state + " pywebview-drag-region"; // Ensure drag class stays
            dom.lumi.style.opacity = '1';
            
            // Positioning
            if(state === 'idle') { dom.lumi.className = 'mood-idle'; dom.lumi.style.top = '60px'; dom.bubble.style.top = '115px'; }
            else if(state === 'music') { dom.lumi.className = 'mood-music'; dom.lumi.style.top = '150px'; dom.bubble.style.top = '200px'; }
            else if(state === 'focus') { dom.lumi.className = 'mood-charge'; dom.lumi.style.top = '90px'; dom.bubble.style.top = '140px'; }
            else if(state === 'notes') { dom.lumi.className = 'mood-idle'; dom.lumi.style.top = '200px'; dom.bubble.style.top = '250px'; }
            else if(state === 'dashboard') { 
                dom.lumi.className = 'mood-idle'; dom.lumi.style.top = '130px'; dom.bubble.style.top = '180px';
                if(data) {
                    dom.ramRing.style.setProperty('--pct', data.ram + '%');
                    dom.batRing.style.setProperty('--pct', data.bat + '%');
                    dom.ramVal.textContent = data.ram + '%';
                    dom.batVal.textContent = data.bat + '%';
                    dom.pingVal.textContent = data.ping;
                    if(data.ram > 80) dom.lumi.className = 'mood-stress';
                }
            }

            // AI Interactions
            if (data && data.status === 'listening') {
                dom.lumi.className = 'mood-listening';
                showBubble("Listening...", 10000);
            } else if (data && data.status === 'speaking') {
                dom.lumi.className = 'mood-speaking';
                showBubble(data.text, 6000);
            } else if (state === 'idle' && !data.status) {
                dom.lumi.className = 'mood-idle';
            }

            if(state === 'notes' && data && data.note && document.activeElement !== dom.notesArea) dom.notesArea.value = data.note;
            if(state === 'focus' && data && data.timer) dom.focusTime.textContent = data.timer;

            clearTimeout(timer);
            if(state !== 'idle' && state !== 'focus') {
                const dur = (state === 'notes' || state === 'music') ? 10000 : 5000;
                timer = setTimeout(() => window.updateState({state:'idle'}), dur);
            }
        };

        window.autoSave = function() {
            clearTimeout(saveTimeout);
            saveTimeout = setTimeout(() => {
                if(window.pywebview) window.pywebview.api.save_note(dom.notesArea.value);
                dom.saveMsg.style.opacity = '1';
                setTimeout(() => dom.saveMsg.style.opacity = '0', 1000);
            }, 800);
        };

        dom.btnFocus.addEventListener('click', (e) => { e.stopPropagation(); clearTimeout(timer); if(window.pywebview) window.pywebview.api.toggle_focus(); });
        dom.btnStopFocus.addEventListener('click', (e) => { e.stopPropagation(); if(window.pywebview) window.pywebview.api.toggle_focus(); });
        
        // Removed manual drag logic to use Native Dragging
        window.addEventListener('contextmenu', e => { e.preventDefault(); if(window.pywebview) window.pywebview.api.open_launcher(); });
        document.addEventListener('wheel', e => { if(window.pywebview) window.pywebview.api.volume(e.deltaY); });
    </script>
</body>
</html>
"""

# --- AI CONTROLLER (Using NEW google.genai Library) ---
class ChatController:
    def __init__(self, api):
        self.api = api
        try:
            if not GEMINI_API_KEY or "PASTE" in GEMINI_API_KEY:
                print("API Key missing")
                return
            
            # This is the usage for the new google-genai library
            self.client = genai.Client(api_key=GEMINI_API_KEY)
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', 160)
        except Exception as e:
            print(f"AI Init Error: {e}")

    def listen_and_respond(self):
        r = sr.Recognizer()
        with sr.Microphone() as source:
            self.api.ctrl.push('idle', {'status': 'listening'})
            try:
                audio = r.listen(source, timeout=5, phrase_time_limit=10)
                text = r.recognize_google(audio)
                self.process_response(text)
            except Exception:
                self.api.ctrl.push('idle', {'status': 'idle'})

    def process_response(self, user_text):
        try:
            # Using the new SDK call structure
            response = self.client.models.generate_content(
                model="gemini-1.5-flash", # Standard stable model
                contents=f"You are Lumi, a helpful and cute AI assistant. Keep response short (1 sentence). User said: {user_text}",
            )
            ai_text = response.text
            
            self.api.ctrl.push('idle', {'status': 'speaking', 'text': ai_text})
            
            self.engine.say(ai_text)
            self.engine.runAndWait()
            
            self.api.ctrl.push('idle', {'status': 'idle'})
        except Exception as e:
            print(f"Response Error: {e}")
            self.api.ctrl.push('idle', {'status': 'idle'})

# --- BACKEND ---
class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [("dwLength", wintypes.DWORD), ("dwMemoryLoad", wintypes.DWORD), ("ullTotalPhys", ctypes.c_uint64),
                ("ullAvailPhys", ctypes.c_uint64), ("ullTotalPageFile", ctypes.c_uint64), ("ullAvailPageFile", ctypes.c_uint64),
                ("ullTotalVirtual", ctypes.c_uint64), ("ullAvailVirtual", ctypes.c_uint64), ("ullAvailExtendedVirtual", ctypes.c_uint64)]

class SystemHelpers:
    _ping_cache = "--"
    _last_ping = 0

    @staticmethod
    def get_ping():
        if time.time() - SystemHelpers._last_ping > 10:
            def ping_thread():
                try:
                    output = subprocess.check_output("ping -n 1 -w 1000 8.8.8.8", shell=True).decode()
                    if "time=" in output:
                        ms = output.split("time=")[1].split("ms")[0].strip()
                        SystemHelpers._ping_cache = ms + "ms"
                    else: SystemHelpers._ping_cache = "999ms"
                except: SystemHelpers._ping_cache = "Err"
            threading.Thread(target=ping_thread, daemon=True).start()
            SystemHelpers._last_ping = time.time()
        return SystemHelpers._ping_cache

    @staticmethod
    def get_stats():
        try:
            mem = MEMORYSTATUSEX()
            mem.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem))
            ram = mem.dwMemoryLoad
        except: ram = 0
        try:
            class POWER(ctypes.Structure):
                _fields_ = [('AC', ctypes.c_byte), ('Flag', ctypes.c_byte), ('Percent', ctypes.c_byte), ('R1', ctypes.c_byte), ('L', ctypes.c_ulong), ('F', ctypes.c_ulong)]
            p = POWER()
            ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(p))
            bat = p.Percent
        except: bat = 100
        return {'ram': ram, 'bat': bat, 'ping': SystemHelpers.get_ping()}

    @staticmethod
    def send_key(vk):
        ctypes.windll.user32.keybd_event(vk, 0, 0, 0); ctypes.windll.user32.keybd_event(vk, 0, 2, 0)

class IslandAPI:
    def __init__(self, controller): 
        self.ctrl = controller
        self.ai = None

    def start_listening(self):
        if not self.ai: self.ai = ChatController(self)
        threading.Thread(target=self.ai.listen_and_respond, daemon=True).start()

    # REMOVED: drag_window method (using native easy_drag instead)
    
    def save_position(self, x, y): self.ctrl.update_geometry(int(x), int(y))
    def open_dashboard(self): self.ctrl.push('dashboard', SystemHelpers.get_stats())
    def open_launcher(self): self.ctrl.push('launcher', {})
    def open_notes(self):
        content = ""
        if NOTES_PATH.exists(): content = NOTES_PATH.read_text(encoding='utf-8')
        self.ctrl.push('notes', {'note': content})
    def save_note(self, text):
        try: NOTES_PATH.write_text(text, encoding='utf-8')
        except: pass
    def volume(self, delta): SystemHelpers.send_key(0xAE if delta > 0 else 0xAF)
    def media(self, action):
        keys = {'play': 0xB3, 'next': 0xB0, 'prev': 0xB1}
        if action in keys: SystemHelpers.send_key(keys[action])
    def launch(self, app):
        try:
            if app == 'calc': os.system('calc')
            elif app == 'code': os.system('start cmd')
            elif app == 'files': os.system('explorer')
            elif app == 'browser': os.system('start https://google.com')
        except: pass
    def toggle_focus(self): self.ctrl.toggle_focus_timer()

class IslandController:
    def __init__(self):
        self.config = self._load_config()
        self.window = None
        self.focus_active = False

    def _load_config(self):
        if CONFIG_PATH.exists():
            try: return json.loads(CONFIG_PATH.read_text())
            except: pass
        return DEFAULT_CONFIG

    def update_geometry(self, x, y):
        self.config['geometry'].update({'x': x, 'y': y})
        try: CONFIG_PATH.write_text(json.dumps(self.config, indent=2))
        except: pass

    def push(self, state, data=None):
        if self.window: 
            safe_json = json.dumps({'state': state, 'data': data or {}})
            self.window.evaluate_js(f"window.updateState({safe_json})")

    def toggle_focus_timer(self):
        if self.focus_active:
            self.focus_active = False
            self.push('idle')
        else:
            self.focus_active = True
            threading.Thread(target=self._focus_loop, daemon=True).start()

    def _focus_loop(self):
        seconds = 25 * 60
        while self.focus_active and seconds > 0:
            if not self.window: break
            m, s = divmod(seconds, 60)
            self.push('focus', {'timer': f'{m:02d}:{s:02d}'})
            time.sleep(1)
            seconds -= 1
        if self.focus_active:
            self.focus_active = False
            self.push('idle')

    def start(self):
        temp_dir = Path(tempfile.gettempdir())
        unique_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        safe_storage = temp_dir / f"island_lumi_{unique_id}"
        
        geo = self.config.get('geometry', {})
        api = IslandAPI(self)
        
        # ENABLED easy_drag=True for crash-proof moving
        self.window = webview.create_window(
            'DynamicIsland', 
            html=HTML_CODE,
            frameless=True, easy_drag=True, on_top=True, 
            transparent=True, background_color='#000000',
            width=600, height=350, 
            x=geo.get('x'), y=geo.get('y'), 
            js_api=api
        )
        webview.start(debug=False, storage_path=str(safe_storage))

if __name__ == '__main__':

    IslandController().start()
