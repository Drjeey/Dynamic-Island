# PyInstaller spec. Build from the project root:  pyinstaller installer/LumiIsland.spec --noconfirm
from PyInstaller.utils.hooks import collect_all, collect_submodules

datas = [('../ui', 'ui')]
binaries = []
hiddenimports = []

# Packages that load parts of themselves at run time
for pkg in ('webview', 'edge_tts', 'speech_recognition', 'pyttsx3', 'keyring', 'sounddevice', 'google.genai', 'anthropic', 'openai'):
    try:
        d, b, h = collect_all(pkg)
        datas += d; binaries += b; hiddenimports += h
    except Exception as e:
        print(f'collect_all({pkg}) skipped: {e}')
hiddenimports += collect_submodules('winrt') + collect_submodules('keyring.backends') + ['win32timezone', 'comtypes']

a = Analysis(['../island7.py'], pathex=['..'], datas=datas, binaries=binaries, hiddenimports=hiddenimports,
             excludes=['tkinter', 'matplotlib', 'numpy.tests'])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='LumiIsland', console=False, upx=False, icon='lumi.ico')
coll = COLLECT(exe, a.binaries, a.datas, name='LumiIsland', upx=False)
