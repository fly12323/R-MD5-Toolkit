"""Exercise real Qt UI and subprocesses: python tests/desktop_smoke.py."""
import hashlib
import os
from pathlib import Path
import sys
import tempfile
import time

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
if os.name == 'nt':
    os.environ.setdefault('QT_QPA_FONTDIR', str(Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'Fonts'))
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
import md5_desktop


if __name__ == '__main__':
    application = QApplication(sys.argv)
    temporary = tempfile.TemporaryDirectory()
    stage = [0]
    failures = []
    began = time.monotonic()
    outputs = []

    def poll():
        try:
            app = QApplication.instance()
            windows = [w for w in app.topLevelWidgets() if hasattr(w, 'start_task')]
            if not windows:
                return
            window = windows[0]
            if time.monotonic() - began > 45:
                raise AssertionError('UI smoke test timed out')
            if stage[0] == 0:
                assert not window.windowIcon().isNull()
                window.resize(1040, 700)
                minimum_preview = ROOT / 'build' / 'desktop-compact-preview.png'
                minimum_preview.parent.mkdir(parents=True, exist_ok=True)
                assert window.grab().save(str(minimum_preview))
                window.resize(1240, 840)
                window.navigation.setCurrentRow(window.mode.findData('inspect'))
                assert window.mode.currentData() == 'inspect'
                window.fields['text'].setText('你好 MD5')
                window.start_task()
                stage[0] = 1
            elif stage[0] == 1 and window.start.isEnabled():
                assert window.result['md5'] == hashlib.md5('你好 MD5'.encode()).hexdigest()
                assert window.copy.isEnabled()
                assert window.digest.text() == window.result['md5']
                assert window.summary.property('state') == 'success'
                assert window.navigation.isEnabled()
                preview = ROOT / 'build' / 'desktop-preview.png'
                preview.parent.mkdir(parents=True, exist_ok=True)
                assert window.grab().save(str(preview))
                window.mode.setCurrentIndex(window.mode.findData('single'))
                window.fields['substr'].setText('0')
                window.fields['workers'].setText('2')
                window.fields['max-attempts'].setText('10000')
                window.start_task()
                stage[0] = 2
            elif stage[0] == 2 and window.start.isEnabled():
                assert window.result['status'] == 'found', window.result
                window.mode.setCurrentIndex(window.mode.findData('strong'))
                window.fields['fastcoll'].setText(str(ROOT / 'bin' / 'fastcoll.exe'))
                window.fields['output-dir'].setText(temporary.name)
                window.start_task()
                assert not window.navigation.isEnabled()
                stage[0] = 3
            elif stage[0] == 3 and window.start.isEnabled():
                assert window.result['collision'], window.result
                outputs.extend(window.result['files'])
                assert window.open.isEnabled()
                window.mode.setCurrentIndex(window.mode.findData('verify'))
                for key, path in zip(('file1', 'file2'), outputs):
                    window.fields[key].setText(path)
                window.start_task()
                stage[0] = 4
            elif stage[0] == 4 and window.start.isEnabled():
                assert window.result['collision']
                window.mode.setCurrentIndex(window.mode.findData('extend'))
                window.fields['known-hash'].setText('invalid')
                window.start_task()
                stage[0] = 5
            elif stage[0] == 5 and window.start.isEnabled():
                assert 'error' in window.result
                assert window.summary.property('state') == 'error'
                window.mode.setCurrentIndex(window.mode.findData('single'))
                window.fields['substr'].setText('f' * 32)
                window.fields['max-attempts'].clear()
                window.start_task()
                stage[0] = 6
                QTimer.singleShot(1200, window.stop_task)
            elif stage[0] == 6 and window.start.isEnabled():
                assert window.stopping
                assert window.summary.text() == '任务已停止。'
                window.close()
                app.quit()
                stage[0] = 7
        except Exception as exc:
            failures.append(repr(exc))
            timer.stop()
            if windows and not window.start.isEnabled():
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
    if failures or stage[0] != 7:
        raise SystemExit('FAILED: ' + str(failures) + ' stage=' + str(stage[0]))
    print('PASS: Unicode inspect, multiprocessing search, native collision, verification, errors, stop')
