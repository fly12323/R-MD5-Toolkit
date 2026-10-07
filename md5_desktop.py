"""Windows desktop frontend; the CLI remains the single computational backend."""
import contextlib
import json
import multiprocessing as mp
import os
from pathlib import Path
import sys
import tempfile
import time


def run_task(request_path):
    import md5_collision
    request = json.loads(Path(request_path).read_text(encoding='utf-8'))
    with open(request['log'], 'w', encoding='utf-8', buffering=1) as log:
        with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
            try:
                return md5_collision.main(request['args'])
            except Exception as exc:
                print(json.dumps({'error': str(exc)}, ensure_ascii=True))
                return 2


def launch():
    from PySide6.QtCore import QProcess, QTimer, QUrl, Qt
    from PySide6.QtGui import QDesktopServices, QIcon, QPixmap
    from PySide6.QtWidgets import (QApplication, QComboBox, QFileDialog,
        QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox,
        QPlainTextEdit, QProgressBar, QPushButton, QScrollArea, QSplitter,
        QVBoxLayout, QWidget, QListWidget, QTabWidget)
    from desktop_theme import STYLE
    asset_dir = Path(__file__).resolve().parent / 'assets'

    class Window(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle('MD5 工具箱')
            self.setWindowIcon(QIcon(str(asset_dir / 'r-icon.ico')))
            self.resize(1240, 840)
            self.setMinimumSize(1040, 700)
            self.temporary = None
            self.result = None
            self.stopping = False
            self.closing = False
            self.process = QProcess(self)
            self.process.finished.connect(self.finished)
            self.process.errorOccurred.connect(self.process_error)
            self.timer = QTimer(self)
            self.timer.setInterval(250)
            self.timer.timeout.connect(self.tick)
            root = QWidget()
            self.setCentralWidget(root)
            shell = QHBoxLayout(root)
            shell.setContentsMargins(0, 0, 0, 0)
            shell.setSpacing(0)
            sidebar = QWidget()
            sidebar.setObjectName('sidebar')
            sidebar.setFixedWidth(214)
            side = QVBoxLayout(sidebar)
            side.setContentsMargins(16, 26, 16, 22)
            brand = QHBoxLayout()
            mark = QLabel('R')
            mark.setObjectName('brandMark')
            mark.setFixedSize(48, 48)
            if (asset_dir / 'r-icon.png').exists():
                mark.setPixmap(QPixmap(str(asset_dir / 'r-icon.png')).scaled(
                    48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            brand.addWidget(mark)
            names = QVBoxLayout()
            brand_name = QLabel('R / MD5')
            brand_name.setObjectName('brandName')
            brand_caption = QLabel('哈希实验工作台')
            brand_caption.setObjectName('brandCaption')
            names.addWidget(brand_name)
            names.addWidget(brand_caption)
            brand.addLayout(names)
            side.addLayout(brand)
            nav_heading = QLabel('工具')
            nav_heading.setObjectName('navHeading')
            side.addWidget(nav_heading)
            self.navigation = QListWidget()
            self.navigation.setObjectName('navigation')
            side.addWidget(self.navigation, 1)
            note = QLabel('本地计算\n文件与结果保存在本机')
            note.setObjectName('sidebarNote')
            side.addWidget(note)
            shell.addWidget(sidebar)
            workspace = QWidget()
            workspace.setObjectName('workspace')
            layout = QVBoxLayout(workspace)
            layout.setContentsMargins(26, 24, 26, 22)
            layout.setSpacing(18)
            self.page_title = QLabel('生成完整碰撞')
            self.page_title.setObjectName('pageTitle')
            layout.addWidget(self.page_title)
            caption = QLabel('MD5 工具箱 / 参数配置与计算结果')
            caption.setObjectName('pageCaption')
            layout.addWidget(caption)
            shell.addWidget(workspace, 1)
            split = QSplitter()
            split.setHandleWidth(18)
            split.setChildrenCollapsible(False)
            layout.addWidget(split, 1)
            self.form_widget = QWidget()
            self.form_widget.setObjectName('parameterForm')
            form_layout = QVBoxLayout(self.form_widget)
            form_layout.setContentsMargins(20, 20, 20, 20)
            form_layout.setSpacing(16)
            settings_heading = QLabel('任务参数')
            settings_heading.setObjectName('sectionTitle')
            form_layout.addWidget(settings_heading)
            self.mode = QComboBox()
            for label, value in [('生成完整碰撞', 'strong'), ('单次哈希搜索', 'single'),
                    ('双重哈希搜索', 'double'), ('固定后缀搜索', 'suffix'),
                    ('魔术哈希搜索', 'magic'), ('双重魔术哈希', 'magic-double'),
                    ('计算文本 / 文件 MD5', 'inspect'), ('验证碰撞文件', 'verify'),
                    ('分析差分轨迹', 'trace'), ('长度扩展', 'extend')]:
                self.mode.addItem(label, value)
                self.navigation.addItem(label)
            form_layout.addWidget(self.mode)
            self.mode.hide()
            self.navigation.setCurrentRow(0)
            self.navigation.currentRowChanged.connect(self.mode.setCurrentIndex)
            self.mode.currentIndexChanged.connect(self.navigation.setCurrentRow)
            self.hint = QLabel()
            self.hint.setObjectName('hint')
            self.hint.setWordWrap(True)
            form_layout.addWidget(self.hint)
            self.form = QFormLayout()
            self.form.setRowWrapPolicy(QFormLayout.WrapAllRows)
            self.form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
            self.form.setVerticalSpacing(10)
            form_layout.addLayout(self.form)
            self.fields = {}
            self.rows = {}
            defaults = {'output-dir': str(Path.home() / 'Documents' / 'MD5-Collisions'),
                'timeout': '120', 'substr': '0e', 'start-pos': '0', 'length': '8',
                'workers': str(min(os.cpu_count() or 1, 4)), 'max-attempts': '1000000',
                'charset': 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
                'known-length': '0'}
            labels = {'prefix': '固定前缀（UTF-8）', 'prefix-file': '二进制前缀文件',
                'output-dir': '输出目录', 'fastcoll': 'fastcoll 程序（可选）',
                'timeout': '超时（秒）', 'substr': '目标十六进制片段',
                'start-pos': '摘要起始位置（0–31）', 'length': '随机候选长度',
                'workers': '并行进程数', 'max-attempts': '最大尝试次数',
                'charset': '候选字符集', 'suffix': '固定后缀（UTF-8）',
                'text': '文本（UTF-8）', 'file': '文件（填写后优先使用）',
                'file1': '第一个文件', 'file2': '第二个文件',
                'known-hash': '已知 MD5', 'known-length': '原始总字节数',
                'append': '追加文本（UTF-8）', 'append-hex': '追加十六进制（填写后优先）'}
            for key, label in labels.items():
                edit = QLineEdit(defaults.get(key, ''))
                edit.setPlaceholderText({'prefix': '可留空，例如 ctf_',
                    'prefix-file': '选择需要保留的二进制前缀',
                    'fastcoll': '自动查找，或选择本机程序',
                    'text': '输入需要计算的文本', 'file': '选择文件后将使用文件内容',
                    'file1': '选择第一个文件', 'file2': '选择第二个文件',
                    'known-hash': '32 位十六进制 MD5',
                    'append-hex': '可选，例如 616263', 'suffix': '可留空',
                    'max-attempts': '留空则仅受超时限制'}.get(key, ''))
                self.fields[key] = edit
                row = QWidget()
                line = QHBoxLayout(row)
                line.setContentsMargins(0, 0, 0, 0)
                line.addWidget(edit)
                if key in ('prefix-file', 'output-dir', 'fastcoll', 'file', 'file1', 'file2'):
                    browse = QPushButton('浏览')
                    browse.clicked.connect(lambda checked=False, k=key: self.browse(k))
                    line.addWidget(browse)
                self.form.addRow(label, row)
                edit.setAccessibleName(label)
                self.form.labelForField(row).setBuddy(edit)
                self.rows[key] = (self.form.labelForField(row), row)
            form_layout.addStretch()
            scroll = QScrollArea()
            scroll.setObjectName('parameterScroll')
            scroll.setWidgetResizable(True)
            scroll.setWidget(self.form_widget)
            split.addWidget(scroll)
            right = QWidget()
            right.setObjectName('resultPanel')
            results = QVBoxLayout(right)
            results.setContentsMargins(20, 20, 20, 20)
            results.setSpacing(14)
            result_heading = QLabel('计算结果')
            result_heading.setObjectName('sectionTitle')
            results.addWidget(result_heading)
            self.summary = QLabel('选择功能并配置参数，然后点击“开始运行”。')
            self.summary.setObjectName('summary')
            self.summary.setWordWrap(True)
            results.addWidget(self.summary)
            fingerprint = QWidget()
            fingerprint.setObjectName('fingerprint')
            digest_layout = QVBoxLayout(fingerprint)
            digest_layout.setContentsMargins(14, 12, 14, 12)
            digest_heading = QLabel('MD5 摘要')
            digest_heading.setObjectName('digestHeading')
            digest_layout.addWidget(digest_heading)
            self.digest = QLabel('等待计算结果')
            self.digest.setObjectName('digest')
            self.digest.setTextInteractionFlags(Qt.TextSelectableByMouse)
            self.digest.setWordWrap(True)
            digest_layout.addWidget(self.digest)
            results.addWidget(fingerprint)
            self.tabs = QTabWidget()
            self.output = QPlainTextEdit()
            self.output.setReadOnly(True)
            self.output.setPlaceholderText('运行任务后，完整结果将显示在这里。')
            self.tabs.addTab(self.output, '结果 JSON')
            self.log = QPlainTextEdit()
            self.log.setReadOnly(True)
            self.log.setMaximumBlockCount(3000)
            self.log.setPlaceholderText('这里显示任务启动信息和最终输出。')
            self.tabs.addTab(self.log, '运行日志')
            results.addWidget(self.tabs, 1)
            buttons = QHBoxLayout()
            self.copy = QPushButton('复制结果')
            self.copy.clicked.connect(lambda: QApplication.clipboard().setText(self.output.toPlainText()))
            self.save = QPushButton('保存结果 JSON')
            self.save.clicked.connect(self.save_result)
            self.open = QPushButton('打开输出目录')
            self.open.clicked.connect(self.open_output)
            for button in (self.copy, self.save, self.open):
                button.setEnabled(False)
                buttons.addWidget(button)
            results.addLayout(buttons)
            split.addWidget(right)
            split.setSizes([385, 560])
            task_bar = QWidget()
            task_bar.setObjectName('taskBar')
            controls = QHBoxLayout(task_bar)
            controls.setContentsMargins(14, 12, 14, 12)
            controls.setSpacing(12)
            self.start = QPushButton('开始运行')
            self.start.setObjectName('runButton')
            self.start.clicked.connect(self.start_task)
            self.stop = QPushButton('停止任务')
            self.stop.setObjectName('stopButton')
            self.stop.setEnabled(False)
            self.stop.clicked.connect(self.stop_task)
            self.progress = QProgressBar()
            self.progress.setTextVisible(False)
            self.progress.setRange(0, 1)
            self.progress.setValue(0)
            self.status = QLabel('就绪')
            self.status.setObjectName('taskStatus')
            controls.addWidget(self.start)
            controls.addWidget(self.stop)
            controls.addWidget(self.progress, 1)
            controls.addWidget(self.status)
            layout.addWidget(task_bar)
            self.mode.currentIndexChanged.connect(self.update_mode)
            self.update_mode()

        def update_mode(self):
            mode = self.mode.currentData()
            self.page_title.setText(self.mode.currentText())
            fields = {'strong': ['prefix', 'prefix-file', 'output-dir', 'fastcoll', 'timeout'],
                'inspect': ['text', 'file'], 'verify': ['file1', 'file2'],
                'trace': ['file1', 'file2'],
                'extend': ['known-hash', 'known-length', 'append', 'append-hex']}.get(mode)
            if fields is None:
                fields = ['prefix', 'suffix', 'length', 'workers', 'max-attempts', 'timeout', 'charset']
                if mode not in ('magic', 'magic-double'):
                    fields += ['substr', 'start-pos']
            self.visible_fields = fields
            for key, widgets in self.rows.items():
                for widget in widgets:
                    widget.setVisible(key in fields)
            self.hint.setText({'strong': '生成内容不同、完整 MD5 相同的两个文件。文本前缀与前缀文件只能选一种。',
                'inspect': '填写文件路径时计算文件 MD5，否则计算文本（允许空文本）。',
                'extend': '原始长度包含秘密的字节数。追加十六进制优先于追加文本。',
                'verify': '独立检查两个文件是否内容不同且完整 MD5 相同。',
                'trace': '展示两个文件在 MD5 压缩过程中的差分。'}.get(mode,
                '搜索匹配条件的候选文本；达到尝试次数或超时后结束。进度条表示正在运行。'))

        def set_summary_state(self, state):
            self.summary.setProperty('state', state)
            self.summary.style().unpolish(self.summary)
            self.summary.style().polish(self.summary)

        def browse(self, key):
            if key == 'output-dir':
                path = QFileDialog.getExistingDirectory(self, '选择输出目录', self.fields[key].text())
            else:
                path, _ = QFileDialog.getOpenFileName(self, '选择文件')
            if path:
                self.fields[key].setText(path)

        def arguments(self):
            mode = self.mode.currentData()
            args = ['--mode', mode, '--json']
            for key in self.visible_fields:
                value = self.fields[key].text()
                if mode == 'inspect' and key == 'text' and self.fields['file'].text():
                    continue
                if key == 'append' and self.fields['append-hex'].text():
                    continue
                if value or key in ('text', 'append') or (key == 'suffix' and mode == 'suffix'):
                    # Equals binds values beginning with '-' to their option.
                    args.append('--' + key + '=' + value)
            if mode in ('verify', 'trace') and any(not self.fields[k].text() for k in ('file1', 'file2')):
                raise ValueError('请选择两个文件。')
            if mode == 'extend' and any(not self.fields[k].text() for k in ('known-hash', 'known-length')):
                raise ValueError('请填写已知 MD5 和原始总字节数。')
            return args

        def start_task(self):
            try:
                args = self.arguments()
            except ValueError as exc:
                QMessageBox.warning(self, '参数不完整', str(exc))
                return
            self.temporary = tempfile.TemporaryDirectory(prefix='md5-ui-')
            request = Path(self.temporary.name) / 'request.json'
            self.log_path = Path(self.temporary.name) / 'output.log'
            request.write_text(json.dumps({'args': args, 'log': str(self.log_path)}), encoding='utf-8')
            self.result = None
            self.stopping = False
            self.output.clear()
            self.digest.setText('计算中…')
            self.tabs.setCurrentIndex(0)
            self.log.clear()
            self.log.appendPlainText('任务已提交：' + self.mode.currentText())
            self.summary.setText('正在运行，完成后显示结果。')
            self.set_summary_state('running')
            for button in (self.copy, self.save, self.open):
                button.setEnabled(False)
            self.form_widget.setEnabled(False)
            self.navigation.setEnabled(False)
            self.start.setEnabled(False)
            self.stop.setEnabled(True)
            self.progress.setRange(0, 0)
            self.began = time.monotonic()
            self.timer.start()
            arguments = ['--task', str(request)]
            if not getattr(sys, 'frozen', False):
                arguments.insert(0, str(Path(__file__).resolve()))
            self.process.start(sys.executable, arguments)

        def tick(self):
            self.status.setText(('正在停止' if self.stopping else '运行中') + f' · {time.monotonic() - self.began:.1f} 秒')

        def stop_task(self):
            if self.process.state() == QProcess.NotRunning:
                return
            self.stopping = True
            self.stop.setEnabled(False)
            # Kill the full process tree, including search workers and fastcoll.
            if os.name == 'nt':
                self.killer = QProcess(self)
                self.killer.finished.connect(self.kill_finished)
                self.killer.errorOccurred.connect(lambda error: self.process.kill())
                system = Path(os.environ.get('SystemRoot', r'C:\Windows'))
                self.killer.start(str(system / 'System32' / 'taskkill.exe'),
                    ['/PID', str(self.process.processId()), '/T', '/F'])
            else:
                self.process.kill()

        def kill_finished(self, code, status):
            if code and self.process.state() != QProcess.NotRunning:
                self.log.appendPlainText('子进程清理失败，请检查系统进程。')
                self.process.kill()

        def process_error(self, error):
            if error == QProcess.FailedToStart:
                self.log.appendPlainText('启动失败：' + self.process.errorString())
                self.finished(2, QProcess.CrashExit)

        def finished(self, code, exit_status):
            self.timer.stop()
            raw = self.log_path.read_text(encoding='utf-8', errors='replace') if self.log_path.exists() else ''
            self.log.appendPlainText(raw)
            if self.stopping:
                self.summary.setText('任务已停止。')
                self.digest.setText('任务已停止')
                self.set_summary_state('idle')
            else:
                try:
                    self.result = json.loads(raw)
                    digest = self.result.get('md5') or self.result.get('final_hash')
                    if not digest and isinstance(self.result.get('result'), dict):
                        digest = self.result['result'].get('md5')
                    if isinstance(digest, list):
                        digest = digest[0] if digest else None
                    self.digest.setText(digest or '暂无摘要结果')
                    self.set_summary_state('success' if code == 0 else 'error' if code == 2 else 'idle')
                    self.output.setPlainText(json.dumps(self.result, ensure_ascii=False, indent=2))
                    if 'error' in self.result:
                        self.summary.setText('运行失败：' + self.result['error'])
                    elif self.result.get('collision') is True:
                        self.summary.setText('验证通过：文件内容不同，完整 MD5 相同。')
                    elif 'collision' in self.result:
                        self.summary.setText('验证完成：这两个文件不构成 MD5 碰撞。')
                    elif 'status' in self.result:
                        labels = {'found': '找到匹配结果', 'timeout': '已超时', 'exhausted': '已达到尝试次数', 'interrupted': '已中断'}
                        self.summary.setText(labels.get(self.result['status'], self.result['status']))
                    else:
                        self.summary.setText('运行完成。')
                    self.copy.setEnabled(True)
                    self.save.setEnabled(True)
                    self.open.setEnabled(bool(self.result.get('files')))
                except (ValueError, TypeError):
                    self.digest.setText('暂无摘要结果')
                    self.set_summary_state('error')
                    self.summary.setText(f'任务未返回有效结果（退出码 {code}），请查看日志。')
            self.status.setText(f'耗时 {time.monotonic() - self.began:.1f} 秒')
            self.progress.setRange(0, 1)
            self.progress.setValue(0 if self.stopping or code else 1)
            self.form_widget.setEnabled(True)
            self.navigation.setEnabled(True)
            self.start.setEnabled(True)
            self.stop.setEnabled(False)
            self.temporary.cleanup()
            self.temporary = None
            if self.closing:
                self.close()

        def save_result(self):
            path, _ = QFileDialog.getSaveFileName(self, '保存结果', 'md5-result.json', 'JSON (*.json)')
            if path:
                try:
                    Path(path).write_text(self.output.toPlainText(), encoding='utf-8')
                except OSError as exc:
                    QMessageBox.warning(self, '保存失败', str(exc))

        def open_output(self):
            if self.result and self.result.get('files'):
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(self.result['files'][0]).resolve().parent)))

        def closeEvent(self, event):
            if self.process.state() != QProcess.NotRunning:
                self.closing = True
                self.stop_task()
                event.ignore()
            else:
                event.accept()

    app = QApplication.instance() or QApplication(sys.argv)
    if os.name == 'nt':
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('R.MD5Toolkit')
    app.setStyle('Fusion')
    app.setWindowIcon(QIcon(str(asset_dir / 'r-icon.ico')))
    app.setStyleSheet(STYLE)
    window = Window()
    window.show()
    return app.exec()


if __name__ == '__main__':
    mp.freeze_support()
    if len(sys.argv) == 3 and sys.argv[1] == '--task':
        sys.exit(run_task(sys.argv[2]))
    sys.exit(launch())
