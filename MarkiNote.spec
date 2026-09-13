# -*- mode: python ; coding: utf-8 -*-
"""MarkiNote 的 PyInstaller 打包配置

用法：
    pyinstaller MarkiNote.spec --noconfirm

为什么用 onedir 而不是 onefile：
  - onefile 每次启动都要把全部内容解压到临时目录，冷启动慢数倍；
  - onefile 的自解压行为是杀毒软件误报的主要来源。

打包后的目录结构（dist/MarkiNote/）：
    MarkiNote.exe        入口
    templates/           前端模板
    static/              样式、脚本、本地化的字体与前端库
    lib/                 首次运行时的示例文档（种子）
    _internal/           Python 运行时与依赖库

资源查找依赖 app/config.py 里的 BASE_DIR。打包后模块的 __file__ 指向
解压目录，BASE_DIR 正好等于该目录，因此上面的 datas 布局能直接被找到。
"""

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('templates', 'templates'),
        ('static', 'static'),
        ('lib', 'lib'),
    ],
    hiddenimports=[
        # pywebview 的原生窗口后端是动态加载的，静态分析看不到
        'webview.platforms.edgechromium',
        'webview.platforms.winforms',
        'clr_loader',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 桌面窗口模式用不到，去掉可显著减小体积
        'tkinter',
        'unittest',
        'pydoc_data',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='MarkiNote',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,          # UPX 压缩会提高杀软误报率，关掉
    console=False,      # 窗口程序，不显示黑色控制台
    disable_windowed_traceback=False,  # 启动失败时弹窗显示错误，而不是静默退出
    icon='images/icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='MarkiNote',
)
