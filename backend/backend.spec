# backend.spec — PyInstaller spec for the packet capture backend
# Uses collect_all('scapy') to bundle EVERY Scapy submodule.
# This is required for AsyncSniffer / packet capture to work on other machines.

from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None

# Collect ALL of scapy (data files, binaries, hidden imports)
datas_scapy, binaries_scapy, hiddenimports_scapy = collect_all('scapy')

# Collect ALL of pywebview
datas_webview, binaries_webview, hiddenimports_webview = collect_all('webview')

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=binaries_scapy + binaries_webview,
    datas=datas_scapy + datas_webview,
    hiddenimports=hiddenimports_scapy + hiddenimports_webview + [
        # Scapy capture-critical modules
        'scapy.sendrecv',
        'scapy.supersocket',
        'scapy.arch.windows',
        'scapy.arch.windows.native',
        'scapy.arch.windows.structures',
        'scapy.arch.winpcap',
        'scapy.layers.all',
        'scapy.layers.l2',
        'scapy.layers.inet',
        'scapy.layers.inet6',
        'scapy.layers.dns',
        # WebSockets
        'websockets',
        'websockets.server',
        'websockets.legacy',
        'websockets.legacy.server',
        # PyWebView and dependencies
        'webview',
        'webview.platforms',
        'webview.platforms.winforms',
        'webview.platforms.edgechromium',
        'webview.platforms.cef',
        'webview.window',
        'webview.menu',
        'webview.event',
        'webview.localization',
        'webview.http',
        'clr_loader',
        'bottle',
        'proxy_tools',
        'win32api',
        'win32con',
        'win32gui',
        'pywintypes',
        # Stdlib
        'asyncio',
        'threading',
        'queue',
        'logging',
        'json',
        'argparse',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'pandas', 'PIL'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    icon='../assets/icon.ico',
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
