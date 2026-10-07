"""Validate the actual windowed EXE, including frozen multiprocessing."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / 'dist' / 'MD5Toolkit' / 'MD5Toolkit.exe'


if __name__ == '__main__':
    env = os.environ.copy()
    env['PATH'] = str(Path(env.get('SystemRoot', r'C:\Windows')) / 'System32')
    env.pop('PYTHONPATH', None)
    env.pop('PYTHONHOME', None)
    # Enumerate hidden windows too: Process.MainWindowTitle omits those.
    import ctypes
    from ctypes import wintypes
    user = ctypes.WinDLL('user32', use_last_error=True)
    user.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    startup = subprocess.STARTUPINFO()
    startup.dwFlags = subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    gui = subprocess.Popen([str(EXE)], env=env, startupinfo=startup)
    handles = []
    titles = []

    @callback_type
    def inspect_window(handle, extra):
        pid = wintypes.DWORD()
        user.GetWindowThreadProcessId(handle, ctypes.byref(pid))
        if pid.value == gui.pid:
            title = ctypes.create_unicode_buffer(4096)
            user.GetWindowTextW(handle, title, len(title))
            titles.append(title.value)
            if title.value == 'MD5 工具箱':
                handles.append(handle)
        return True

    try:
        deadline = time.monotonic() + 15
        while not handles and time.monotonic() < deadline and gui.poll() is None:
            user.EnumWindows(inspect_window, 0)
            time.sleep(0.1)
        assert handles, ('EXE window did not start', titles)
        user.PostMessageW(handles[0], 0x0010, 0, 0)  # WM_CLOSE
        assert gui.wait(timeout=10) == 0
    finally:
        if gui.poll() is None:
            gui.kill()
            gui.wait()
    with tempfile.TemporaryDirectory(prefix='md5-frozen-check-') as temporary:
        work = Path(temporary)

        def run(args, expected=0):
            log = work / 'output.log'
            log.unlink(missing_ok=True)
            request = work / 'request.json'
            request.write_text(json.dumps({'args': [*args, '--json'], 'log': str(log)}), encoding='utf-8')
            process = subprocess.run([str(EXE), '--task', str(request)], cwd=work,
                env=env, timeout=150)
            assert process.returncode == expected, process.returncode
            return json.loads(log.read_text(encoding='utf-8'))

        result = run(['-m', 'inspect', '--text', '你好 MD5'])
        assert result['md5'] == hashlib.md5('你好 MD5'.encode()).hexdigest()
        result = run(['-m', 'inspect', '--text=--help'])
        assert result['md5'] == hashlib.md5(b'--help').hexdigest()
        result = run(['-m', 'single', '-s', '0', '-w', '2', '--max-attempts', '10000', '--timeout', '20'])
        assert result['status'] == 'found', result
        first = hashlib.md5(b'a').hexdigest()
        second = hashlib.md5(first.encode()).hexdigest()
        pos = next(i for i in range(32) if first[i] == second[i])
        result = run(['-m', 'double', '-s', first[pos], '-p', str(pos), '--charset', 'a',
            '-l', '1', '--max-attempts', '1', '--timeout', '20'])
        assert result['result']['md5_second'] == second
        result = run(['-m', 'suffix', '-s', hashlib.md5(b'a--tail').hexdigest()[:2],
            '--suffix=--tail', '--charset', 'a', '-l', '1', '--max-attempts', '1'])
        assert result['result']['message'] == 'a--tail'
        for mode, expected in [('magic', 0), ('magic-double', 1)]:
            result = run(['-m', mode, '-c', 'QNKCDZ', '--charset', 'O', '-l', '1',
                '--max-attempts', '1', '--timeout', '20'], expected=expected)
            assert result['status'] == ('found' if mode == 'magic' else 'exhausted')
        result = run(['-m', 'strong', '--fastcoll', str(ROOT / 'bin' / 'fastcoll.exe'),
            '--output-dir', str(work / '碰撞结果'), '--timeout', '120'])
        assert result['collision'], result
        pair = result['files']
        result = run(['-m', 'verify', '--file1', result['files'][0], '--file2', result['files'][1]])
        assert result['collision'], result
        result = run(['-m', 'trace', '--file1', pair[0], '--file2', pair[1]])
        assert result['collision'] and result['blocks']
        original = b'secret:hello'
        result = run(['-m', 'extend', '--known-hash', hashlib.md5(original).hexdigest(),
            '--known-length', str(len(original)), '--append=--help'])
        assert result['final_hash'] == hashlib.md5(original + bytes.fromhex(result['extension']['hex'])).hexdigest()
        result = run(['-m', 'extend', '--known-hash', 'bad', '--known-length', '0', '--append', ''], expected=2)
        assert 'error' in result
    print('PASS: frozen EXE window, all 10 modes and errors (without Python PATH)')
