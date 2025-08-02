# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
	['flask_app.py'],
	pathex=[],
	binaries=[],
	datas=[
		('templates', 'templates'),
		('src', 'src'),
		('static', 'static'),
	],
	hiddenimports=[
		'sklearn.utils._weight_vector',
		'sklearn.neighbors.typedefs',
		'sklearn.neighbors.quad_tree',
		'sklearn.tree._utils',
		'pandas._libs.tslibs.timedeltas',
		'openpyxl.cell._writer'
	],
	hookspath=[],
	hooksconfig={},
	runtime_hooks=[],
	excludes=[],
	win_no_prefer_redirects=False,
	win_private_assemblies=False,
	cipher=block_cipher,
	noarchive=False,
)
pdb = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
	pdb,
	a.scripts,
	a.binaries,
	a.zipfiles,
	a.datas,
	[],
	name='StringZ',
	debug=False,
	bootloader_ignore_signals=False,
	strip=False,
	upx=True,
	upx_exclude=[],
	runtime_tmpdir=None,
	console=False, # Note to myself: Set to True to show the console window
	disable_windowed_traceback=False,
	argv_emulation=False,
	target_arch=None,
	codesign_identity=None,
	entitlements_file=None,
	icon='favicon.ico'
)
