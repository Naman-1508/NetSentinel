# ml_engine.spec — PyInstaller spec for the FastAPI ML backend

from PyInstaller.utils.hooks import collect_all

block_cipher = None

# Collect all necessary data/hidden imports for ML libraries
datas_ml, binaries_ml, hiddenimports_ml = collect_all('xgboost')
d_sl, b_sl, h_sl = collect_all('sklearn')
d_pd, b_pd, h_pd = collect_all('pandas')
d_np, b_np, h_np = collect_all('numpy')
d_jl, b_jl, h_jl = collect_all('joblib')

# Collect FastAPI/Uvicorn
d_fa, b_fa, h_fa = collect_all('fastapi')
d_uv, b_uv, h_uv = collect_all('uvicorn')

# Combine them
all_datas = datas_ml + d_sl + d_pd + d_np + d_jl + d_fa + d_uv
all_binaries = binaries_ml + b_sl + b_pd + b_np + b_jl + b_fa + b_uv
all_hidden = hiddenimports_ml + h_sl + h_pd + h_np + h_jl + h_fa + h_uv

# Add standard lib hidden imports
all_hidden.extend([
    'asyncio',
    'logging',
    'json',
    'websockets',
    'websockets.server',
    'websockets.legacy',
])

import os
# Ensure we include the trained models
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
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter'],
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
    strip=False,
    upx=True,
    console=True, # Needs to run as background process
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
    upx_exclude=[],
    name='ml_engine',
)
