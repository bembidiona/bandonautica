# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

extra_data = [
("chromedriver.exe", "."),
("dummy.mp3", "."),
("icon.ico", "."),
("libmpg123.dll", "."),
("main.png", "."),
("README.txt", ".")
]

a = Analysis(['bandonautica.py'],
             pathex=['D:\\JERE\\PROJECTS\\randomcamp'],
             binaries=[],
             datas=extra_data,
             hiddenimports=[],
             hookspath=["hooks"],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='bandonautica',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          icon="icon.ico",
          console=False)
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='bandonautica')
