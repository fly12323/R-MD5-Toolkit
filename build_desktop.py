"""Build a windowed Windows executable without redistributing native fastcoll."""
from pathlib import Path
import subprocess
import shutil
import os
import sys

ROOT = Path(__file__).resolve().parent

if __name__ == '__main__':
    extra = []
    # Conda's ctypes depends on a DLL outside the usual Python DLL directory.
    for name in ('ffi.dll', 'liblzma.dll', 'bzip2.dll', 'libbz2.dll', 'libexpat.dll'):
        dependency = Path(sys.prefix) / 'Library' / 'bin' / name
        if dependency.is_file():
            extra += ['--add-binary', str(dependency) + ';.']
    # Unrelated tools on PATH may expose same-name DLLs (notably Poppler's
    # versioned ICU). Qt on Windows uses the operating system's ICU API.
    env = os.environ.copy()
    system = Path(env.get('SystemRoot', r'C:\Windows'))
    env['PATH'] = os.pathsep.join([str(system / 'System32'), str(system),
                                 str(Path(sys.executable).parent)])
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
        '--windowed', '--onedir', '--name', 'MD5Toolkit',
        '--icon', str(ROOT / 'assets' / 'r-icon.ico'),
        '--add-data', str(ROOT / 'assets') + ';assets',
        '--hidden-import', 'md5_collision', '--hidden-import', 'fastcoll_backend',
        '--add-data', str(ROOT / 'THIRD_PARTY.md') + ';.',
        *extra, str(ROOT / 'md5_desktop.py')], cwd=ROOT, env=env, check=True)
    target = ROOT / 'dist' / 'MD5Toolkit'
    if (ROOT / 'licenses').is_dir():
        shutil.copytree(ROOT / 'licenses', target / 'licenses', dirs_exist_ok=True)
    if (ROOT / 'THIRD_PARTY_UI.md').is_file():
        shutil.copyfile(ROOT / 'THIRD_PARTY_UI.md', target / 'THIRD_PARTY_UI.md')
    # Python loads its runtime before Qt: use Qt's newer, compatible runtime
    # at the bundle root too, rather than Conda's older same-name DLLs.
    import PySide6
    qt_directory = Path(PySide6.__file__).resolve().parent
    for name in ('msvcp140.dll', 'msvcp140_1.dll', 'msvcp140_2.dll',
                 'vcruntime140.dll', 'vcruntime140_1.dll'):
        source = qt_directory / name
        if source.is_file():
            shutil.copyfile(source, target / '_internal' / name)
    (target / '使用说明.txt').write_text(
        '双击 MD5Toolkit.exe 启动。请保留整个目录，不能只移动 exe。\n'
        '碰撞生成需在界面选择本机 fastcoll.exe；程序不捆绑第三方 fastcoll。\n'
        '其他功能不需要 fastcoll。碰撞结果默认保存到用户 Documents/MD5-Collisions。\n',
        encoding='utf-8')
    print('Built:', target / 'MD5Toolkit.exe')
