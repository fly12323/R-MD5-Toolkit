"""All ten real UI modes and button handlers; controlled dialog selections."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
if os.name == 'nt':
    os.environ.setdefault('QT_QPA_FONTDIR', str(Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'Fonts'))
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from PySide6.QtCore import QTimer
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox
import md5_desktop


def digest(data):
    return hashlib.md5(data).hexdigest()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    temporary = tempfile.TemporaryDirectory(prefix='md5-full-ui-')
    work = Path(temporary.name)
    binary_file = work / '中文 文件.bin'
    binary_file.write_bytes(b'\x00\xff\x80' + '中文'.encode())
    passed = []
    failures = []
    window = None
    pending = False
    began = time.monotonic()

    def run(mode, **values):
        window.navigation.setCurrentRow(window.mode.findData(mode))
        for field in window.fields.values():
            field.clear()
        for key, value in values.items():
            window.fields[key.replace('_', '-')].setText(str(value))
        window.start.click()
        assert not window.start.isEnabled()
        assert not window.navigation.isEnabled()

    def search(mode, **values):
        config = dict(prefix='', suffix='', length=1, workers=2,
                      max_attempts=1, timeout=15, charset='a', substr='0', start_pos=0)
        config.update(values)
        run(mode, **config)

    def check(name, condition):
        assert condition, (name, window.result, window.summary.text())
        passed.append(name)
        print('PASS:', name, flush=True)

    def scenarios():
        run('inspect', text='--help')
        yield
        check('inspect: option-like text', window.result['md5'] == digest(b'--help'))
        window.copy.click()
        check('copy result button', app.clipboard().text() == window.output.toPlainText())
        saved = work / '保存结果.json'
        with patch.object(QFileDialog, 'getSaveFileName', return_value=(str(saved), 'JSON (*.json)')):
            window.save.click()
        check('save JSON button', json.loads(saved.read_text(encoding='utf-8')) == window.result)
        with patch.object(QFileDialog, 'getSaveFileName', return_value=('', '')):
            window.save.click()
        check('cancel save preserves result', json.loads(saved.read_text(encoding='utf-8')) == window.result)
        with patch.object(QFileDialog, 'getSaveFileName', return_value=(str(work), '')), \
             patch.object(QMessageBox, 'warning') as warning:
            window.save.click()
            check('save failure warning', warning.called)
        for key in ('prefix-file', 'fastcoll', 'file', 'file1', 'file2'):
            with patch.object(QFileDialog, 'getOpenFileName', return_value=(str(binary_file), '')):
                window.browse(key)
            check('file selection: ' + key, window.fields[key].text() == str(binary_file))
            with patch.object(QFileDialog, 'getOpenFileName', return_value=('', '')):
                window.browse(key)
            check('cancel selection: ' + key, window.fields[key].text() == str(binary_file))
        with patch.object(QFileDialog, 'getExistingDirectory', return_value=str(work)):
            window.browse('output-dir')
        check('directory selection', window.fields['output-dir'].text() == str(work))
        window.tabs.setCurrentIndex(1)
        check('log tab', window.tabs.currentWidget() is window.log)
        window.tabs.setCurrentIndex(0)

        run('inspect', text='ignored', file=str(binary_file))
        yield
        check('inspect: binary file takes priority', window.result['md5'] == digest(binary_file.read_bytes()))
        run('inspect', text='')
        yield
        check('inspect: empty text', window.result['md5'] == digest(b''))

        search('single')
        yield
        check('single: deterministic match', window.result['result']['message'] == 'a')
        first = digest(b'a')
        second = digest(first.encode())
        position = next(i for i in range(32) if first[i] == second[i])
        search('double', substr=first[position], start_pos=position)
        yield
        check('double: independent second hash', window.result['result']['md5_second'] == second)
        message = '--prefixa--tail'
        search('suffix', prefix='--prefix', suffix='--tail', substr=digest(message.encode())[:2])
        yield
        check('suffix: option-like prefix/suffix', window.result['result']['message'] == message)
        search('magic', prefix='QNKCDZ', charset='O')
        yield
        check('magic: known real match', window.result['result']['md5'] == digest(b'QNKCDZO'))
        search('magic-double', prefix='QNKCDZ', charset='O')
        yield
        check('magic-double: rejects nonmagic second hash', window.result['status'] == 'exhausted' and window.result['result'] is None)

        run('strong', output_dir=str(work / 'collisions'), fastcoll=str(ROOT / 'bin' / 'fastcoll.exe'), timeout=120)
        yield
        pair = window.result['files']
        check('strong: independent content/hash check', Path(pair[0]).read_bytes() != Path(pair[1]).read_bytes()
              and digest(Path(pair[0]).read_bytes()) == digest(Path(pair[1]).read_bytes()))
        with patch.object(QDesktopServices, 'openUrl', return_value=True) as open_url:
            window.open.click()
            check('open output button', Path(open_url.call_args.args[0].toLocalFile()).resolve() == Path(pair[0]).parent.resolve())
        run('verify', file1=pair[0], file2=pair[1])
        yield
        check('verify: true collision', window.result['collision'])
        run('verify', file1=pair[0], file2=pair[0])
        yield
        check('verify: identical files rejected', not window.result['collision'])
        run('trace', file1=pair[0], file2=pair[1])
        yield
        check('trace: real collision blocks', window.result['collision'] and bool(window.result['blocks']))
        prefix = work / 'prefix.bin'
        prefix.write_bytes(b'\x00\xff' + '前缀'.encode())
        run('strong', prefix_file=str(prefix), output_dir=str(work / 'collisions'),
            fastcoll=str(ROOT / 'bin' / 'fastcoll.exe'), timeout=120)
        yield
        check('strong: binary prefix preserved', window.result['collision'] and
              all(Path(p).read_bytes().startswith(prefix.read_bytes()) for p in window.result['files']))

        original = b'secret:hello'
        run('extend', known_hash=digest(original), known_length=len(original), append=' --help ')
        yield
        extension = bytes.fromhex(window.result['extension']['hex'])
        check('extend: independent full-message hash', window.result['final_hash'] == digest(original + extension)
              and extension.endswith(b' --help '))
        run('extend', known_hash=digest(original), known_length=len(original), append='ignored', append_hex='00ff')
        yield
        extension = bytes.fromhex(window.result['extension']['hex'])
        check('extend: binary append takes priority', extension.endswith(b'\x00\xff') and
              window.result['final_hash'] == digest(original + extension))

        run('extend', known_hash='bad', known_length=0, append='')
        yield
        check('invalid hash produces error', 'error' in window.result and window.summary.property('state') == 'error')
        search('single', substr='xyz')
        yield
        check('invalid search parameter produces error', 'error' in window.result)
        search('single', substr='f' * 32, max_attempts='', timeout=0.3)
        yield
        check('timeout returns control', window.result['status'] == 'timeout' and window.start.isEnabled())

        window.navigation.setCurrentRow(window.mode.findData('verify'))
        window.fields['file1'].clear()
        window.fields['file2'].clear()
        with patch.object(QMessageBox, 'warning') as warning:
            window.start.click()
            check('missing files blocked before launch', warning.called and window.start.isEnabled())
        search('single', substr='f' * 32, max_attempts='', timeout=30)
        QTimer.singleShot(800, window.stop.click)
        yield
        check('stop active multiprocess task', window.stopping and window.start.isEnabled())
        search('single', substr='f' * 32, max_attempts='', timeout=30)
        QTimer.singleShot(800, window.close)
        yield
        check('close active task cleans up before closing', window.stopping and not window.isVisible())

    iterator = None

    def poll():
        global window, iterator, pending
        try:
            if time.monotonic() - began > 180:
                raise AssertionError('UI full check exceeded 180 seconds')
            if window is None:
                windows = [w for w in app.topLevelWidgets() if hasattr(w, 'start_task')]
                if not windows:
                    return
                window = windows[0]
                iterator = scenarios()
            if pending and not window.start.isEnabled():
                return
            next(iterator)
            pending = True
        except StopIteration:
            timer.stop()
            app.quit()
        except Exception as exc:
            failures.append(repr(exc))
            timer.stop()
            if window and not window.start.isEnabled():
                window.stop_task()
                QTimer.singleShot(1000, app.quit)
            else:
                app.quit()

    timer = QTimer()
    timer.setInterval(100)
    timer.timeout.connect(poll)
    timer.start()
    md5_desktop.launch()
    temporary.cleanup()
    report = {'passed_checks': passed, 'failures': failures,
              'dialog_method': 'Controlled dialog selections; desktop open intercepted',
              'elapsed_seconds': round(time.monotonic() - began, 2)}
    (ROOT / 'build').mkdir(exist_ok=True)
    (ROOT / 'build' / 'desktop-full-check.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    if failures:
        raise SystemExit('FAILED: ' + str(failures))
    print(f'PASS: all 10 UI modes and {len(passed)} checks')
