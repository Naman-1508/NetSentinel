# ml_engine.spec — PyInstaller spec for the FastAPI ML backend (Optimized)
# Switched from collect_all() to targeted imports — removes test suites, docs,
# matplotlib, scipy, Qt etc. Cuts installed size from ~1GB to ~400MB.

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs
import os

block_cipher = None

# ── Only collect DATA files (not entire packages with tests/docs) ──────────
datas = []
datas += collect_data_files('sklearn')
datas += collect_data_files('xgboost')
datas += collect_data_files('pandas')
datas += collect_data_files('numpy')
datas += collect_data_files('fastapi')
datas += collect_data_files('uvicorn')
datas += collect_data_files('starlette')

# Add trained models
models_path = os.path.abspath('models/saved')
if os.path.exists(models_path):
    datas.append((models_path, 'models/saved'))

# ── Only the native binaries we actually need ───────────────────────────────
binaries = []
binaries += collect_dynamic_libs('numpy')
binaries += collect_dynamic_libs('pandas')
binaries += collect_dynamic_libs('xgboost')

a = Analysis(
    ['api/server.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=[
        # scikit-learn
        'sklearn', 'sklearn.ensemble', 'sklearn.ensemble._forest',
        'sklearn.ensemble._gb', 'sklearn.tree', 'sklearn.tree._classes',
        'sklearn.preprocessing', 'sklearn.preprocessing._data',
        'sklearn.preprocessing._label', 'sklearn.pipeline',
        'sklearn.utils._bunch', 'sklearn.utils.validation', 'sklearn.metrics',
        # xgboost
        'xgboost', 'xgboost.sklearn', 'xgboost.core',
        # joblib
        'joblib', 'joblib.externals.loky', 'joblib.externals.loky.process_executor',
        # data libs
        'pandas', 'numpy',
        # FastAPI / Uvicorn
        'fastapi', 'uvicorn', 'uvicorn.loops', 'uvicorn.loops.asyncio',
        'uvicorn.protocols', 'uvicorn.protocols.http',
        'uvicorn.protocols.http.h11_impl', 'uvicorn.lifespan',
        'uvicorn.lifespan.off', 'starlette', 'starlette.routing',
        'starlette.responses', 'anyio', 'anyio._backends._asyncio', 'h11',
        # websockets
        'websockets', 'websockets.server', 'websockets.legacy',
        # stdlib
        'asyncio', 'logging', 'json',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        # ── Heavy unused packages — these are the big size offenders ──
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
        'setuptools', 'pkg_resources',
        'doctest', 'pydoc',
        'test', 'tests', 'testing',
        'curses', 'idlelib', 'lib2to3', 'unittest',
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
    strip=True,    # strip debug symbols
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
    strip=True,
    upx=True,
    upx_exclude=['xgboost.dll', 'libxgboost.dll'],  # xgboost binaries can break with UPX
    name='ml_engine',
)
