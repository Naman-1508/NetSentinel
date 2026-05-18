# backend.spec — PyInstaller spec for the integrated NetSentinel backend
# Bundles the packet capture host and the ML risk engine into one executable.

from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_dynamic_libs
import os

spec_dir = os.getcwd()
repo_root = os.path.dirname(spec_dir)
ml_root = os.path.join(repo_root, 'ml_risk_engine')
frontend_out = os.path.join(repo_root, 'frontend', 'out')
offline_artifacts = os.path.join(repo_root, 'Offline2', 'artifacts')
ml_models = os.path.join(ml_root, 'models', 'saved')
ml_logs = os.path.join(ml_root, 'logs')

block_cipher = None

# Collect ALL of nfstream and psutil (data files, binaries, hidden imports)
datas_nfstream, binaries_nfstream, hiddenimports_nfstream = collect_all('nfstream')
datas_psutil, binaries_psutil, hiddenimports_psutil = collect_all('psutil')

# Collect ALL of pywebview
datas_webview, binaries_webview, hiddenimports_webview = collect_all('webview')

# Collect the ML stack used by the embedded FastAPI service
datas_fastapi, binaries_fastapi, hiddenimports_fastapi = collect_all('fastapi')
datas_uvicorn, binaries_uvicorn, hiddenimports_uvicorn = collect_all('uvicorn')
datas_starlette, binaries_starlette, hiddenimports_starlette = collect_all('starlette')
datas_anyio, binaries_anyio, hiddenimports_anyio = collect_all('anyio')
datas_websockets, binaries_websockets, hiddenimports_websockets = collect_all('websockets')

datas_sklearn = collect_data_files('sklearn')
datas_xgboost = collect_data_files('xgboost')
datas_pandas = collect_data_files('pandas')
datas_numpy = collect_data_files('numpy')
datas_joblib = collect_data_files('joblib')
datas_scipy = collect_data_files('scipy')

binaries_numpy = collect_dynamic_libs('numpy')
binaries_pandas = collect_dynamic_libs('pandas')
binaries_xgboost = collect_dynamic_libs('xgboost')
binaries_scipy = collect_dynamic_libs('scipy')

ml_datas = []
if os.path.exists(frontend_out):
    ml_datas.append((frontend_out, 'frontend/out'))
if os.path.exists(offline_artifacts):
    # Add the Offline2/artifacts directory as individual file entries so PyInstaller
    # reliably includes them in both onefile and onedir bundles.
    for root, _, files in os.walk(offline_artifacts):
        for fname in files:
            src = os.path.join(root, fname)
            # preserve relative path under Offline2/artifacts
            rel_dir = os.path.relpath(root, offline_artifacts)
            dest_dir = os.path.join('Offline2', 'artifacts', rel_dir) if rel_dir != '.' else os.path.join('Offline2', 'artifacts')
            ml_datas.append((src, dest_dir))
if os.path.exists(ml_models):
    # Include individual model files too (models/saved)
    for root, _, files in os.walk(ml_models):
        for fname in files:
            src = os.path.join(root, fname)
            rel_dir = os.path.relpath(root, ml_models)
            dest_dir = os.path.join('models', 'saved', rel_dir) if rel_dir != '.' else os.path.join('models', 'saved')
            ml_datas.append((src, dest_dir))
if os.path.exists(ml_logs):
    ml_datas.append((ml_logs, 'logs'))

a = Analysis(
    ['main.py'],
    pathex=[spec_dir, ml_root],
    binaries=(
        binaries_nfstream + binaries_psutil + binaries_webview +
        binaries_fastapi + binaries_uvicorn + binaries_starlette + binaries_anyio + binaries_websockets +
        binaries_numpy + binaries_pandas + binaries_xgboost + binaries_scipy
    ),
    datas=(
        datas_nfstream + datas_psutil + datas_webview +
        datas_fastapi + datas_uvicorn + datas_starlette + datas_anyio + datas_websockets +
        datas_sklearn + datas_xgboost + datas_pandas + datas_numpy + datas_joblib + datas_scipy +
        ml_datas
    ),
    hiddenimports=hiddenimports_nfstream + hiddenimports_psutil + hiddenimports_webview + hiddenimports_fastapi + hiddenimports_uvicorn + hiddenimports_starlette + hiddenimports_anyio + hiddenimports_websockets + [
        # nfstream
        'nfstream',
        'psutil',
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
        # ML engine package paths
        'api.server',
        'realtime_monitor.monitor',
        'realtime_monitor.correlation',
        'predictor.predictor',
        'feature_extractor.extractor',
        'data_pipeline.preprocessor',
        'fastapi',
        'uvicorn',
        'starlette',
        'anyio',
        'pandas',
        'numpy',
        'sklearn',
        'xgboost',
        'joblib',
        'scipy',
        # cffi — required by nfstream native bridge at runtime
        'cffi',
        '_cffi_backend',
        # Stdlib
        'asyncio',
        'threading',
        'queue',
        'logging',
        'json',
        'argparse',
        'multiprocessing',
        'multiprocessing.freeze_support',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # ── Heavy AI/ML frameworks not used by NetSentinel ──────────────
        'tensorflow', 'tensorflow_core', 'tensorboard', 'tensorflow_estimator',
        'keras', 'keras.src',
        'torch', 'torchvision', 'torchaudio',
        'numba', 'llvmlite',
        'cv2', 'PIL', 'Pillow',
        'h5py',
        # ── Scientific extras not needed ─────────────────────────────────
        'matplotlib', 'matplotlib.pyplot',
        'IPython', 'jupyter', 'notebook', 'nbformat', 'nbconvert',
        'sympy',
        # ── GUI toolkits not needed ───────────────────────────────────────
        'tkinter', '_tkinter',
        'PyQt5', 'PyQt6', 'PySide2', 'PySide6',
        'wx', 'gi', 'gtk',
        # ── Cloud / distributed not needed ───────────────────────────────
        'boto3', 'botocore', 'google.cloud',
        'dask', 'distributed',
        'curses', 'idlelib', 'lib2to3',
        # ── Testing / dev tools ────────────────────────────────────────────
        'black', 'pytest',
    ],
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
    name='NetSentinel',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,       # Windowed app: do not spawn a terminal when launched from the installer or shortcut
    icon='../assets/icon.ico',
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=True,      # Auto-request admin so Npcap/nfstream can open the capture device
)
