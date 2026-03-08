# ml_engine.spec — PyInstaller spec for the FastAPI ML backend
# Strategy: collect_all() for runtime (uvicorn/fastapi/websockets) — they NEED all submodules.
# For ML libs, only collect data files + dynamic libs, then explicitly exclude big unused extras.
# This keeps the app working while still trimming ~300-400MB of unused junk.

from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_dynamic_libs
import os

block_cipher = None

# ── Runtime: use collect_all (they need every submodule to work correctly) ──
d_uv,  b_uv,  h_uv  = collect_all('uvicorn')
d_fa,  b_fa,  h_fa  = collect_all('fastapi')
d_ws,  b_ws,  h_ws  = collect_all('websockets')
d_st,  b_st,  h_st  = collect_all('starlette')
d_ai,  b_ai,  h_ai  = collect_all('anyio')

# ── ML libs: data files + native binaries only (no test suites or docs) ────
d_sk = collect_data_files('sklearn')
d_xg = collect_data_files('xgboost')
d_pd = collect_data_files('pandas')
d_np = collect_data_files('numpy')
d_jl = collect_data_files('joblib')

b_np = collect_dynamic_libs('numpy')
b_pd = collect_dynamic_libs('pandas')
b_xg = collect_dynamic_libs('xgboost')

# ── Combine ─────────────────────────────────────────────────────────────────
all_datas    = d_uv + d_fa + d_ws + d_st + d_ai + d_sk + d_xg + d_pd + d_np + d_jl
all_binaries = b_uv + b_fa + b_ws + b_st + b_ai + b_np + b_pd + b_xg
all_hidden   = h_uv + h_fa + h_ws + h_st + h_ai + [
    # scikit-learn estimators
    'sklearn', 'sklearn.ensemble', 'sklearn.ensemble._forest',
    'sklearn.ensemble._gb', 'sklearn.tree', 'sklearn.tree._classes',
    'sklearn.preprocessing', 'sklearn.preprocessing._data',
    'sklearn.preprocessing._label', 'sklearn.pipeline',
    'sklearn.utils._bunch', 'sklearn.utils.validation', 'sklearn.metrics',
    # xgboost
    'xgboost', 'xgboost.sklearn', 'xgboost.core',
    # data
    'joblib', 'joblib.externals.loky', 'joblib.externals.loky.process_executor',
    'pandas', 'numpy',
    # stdlib
    'asyncio', 'logging', 'json', 'multiprocessing', 'multiprocessing.freeze_support',
]

# ── Add trained models ───────────────────────────────────────────────────────
models_path = os.path.abspath('models/saved')
if os.path.exists(models_path):
    all_datas.append((models_path, 'models/saved'))

a = Analysis(
    ['api/server.py'],
    pathex=['.'],
    binaries=all_binaries,
    datas=all_datas,
    hiddenimports=all_hidden,
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        # ── These are the big ones not used by NetSentinel ──
        'matplotlib', 'matplotlib.pyplot',
        'scipy',
        'PIL', 'Pillow',
        'IPython', 'jupyter', 'notebook',
        'sympy',
        'tkinter', '_tkinter',
        'PyQt5', 'PyQt6', 'PySide2', 'PySide6',
        'wx', 'gi', 'gtk',
        'cv2', 'tensorflow', 'keras', 'torch',
        'boto3', 'botocore',
        'curses', 'idlelib', 'lib2to3',
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
    [],
    exclude_binaries=True,
    name='ml_engine',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,   # Don't strip — can cause issues with .pyd files on Windows
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=['xgboost.dll', 'libxgboost.dll', 'python313.dll'],
    name='ml_engine',
)
