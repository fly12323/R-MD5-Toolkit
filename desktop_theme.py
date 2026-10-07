"""Visual tokens and Qt styling for the R desktop workbench."""

STYLE = '''
QWidget { font-family: "Microsoft YaHei UI", "Segoe UI"; font-size: 13px; color: #253650; }
QMainWindow, QWidget#workspace { background: #EDF1F6; }
QWidget#sidebar { background: #192C49; }
QLabel#brandName { color: #FFFFFF; font-size: 20px; font-weight: 600; }
QLabel#brandCaption, QLabel#sidebarNote { color: #AFBED5; font-size: 12px; }
QLabel#brandMark { color: #FFFFFF; font-size: 36px; font-weight: 700; }
QLabel#navHeading { color: #8CA1C1; font-size: 12px; padding-top: 20px; padding-bottom: 8px; }
QListWidget#navigation { background: transparent; border: none; outline: none; color: #CBD6E6; }
QListWidget#navigation::item { min-height: 38px; padding-left: 14px; margin-bottom: 4px; border-radius: 6px; }
QListWidget#navigation::item:hover { background: #253E60; }
QListWidget#navigation::item:selected { background: #355981; color: #FFFFFF; border-left: 3px solid #9FBEFF; }
QLabel#pageTitle { font-size: 25px; font-weight: 600; color: #192C49; }
QLabel#pageCaption { color: #728199; font-size: 12px; }
QLabel#sectionTitle { font-size: 16px; font-weight: 600; color: #253650; }
QLabel#hint { color: #748198; font-size: 12px; }
QScrollArea#parameterScroll, QWidget#parameterForm, QWidget#resultPanel { background: #FFFFFF; border: none; }
QScrollArea#parameterScroll, QWidget#resultPanel { border: 1px solid #DBE3EE; border-radius: 10px; }
QLineEdit, QComboBox { background: #F7F9FC; border: 1px solid #D9E1ED; border-radius: 5px; padding: 8px 10px; selection-background-color: #4169E1; }
QLineEdit:focus, QComboBox:focus { border: 1px solid #4169E1; background: #FFFFFF; }
QLineEdit:disabled { color: #99A6B9; background: #F2F4F7; }
QPushButton { background: #FFFFFF; border: 1px solid #D6DFEB; border-radius: 5px; padding: 8px 12px; color: #354963; }
QPushButton:hover { background: #F0F5FC; border-color: #99AFCE; }
QPushButton:pressed { background: #E1EAF7; }
QPushButton:focus { border: 1px solid #4169E1; }
QPushButton:disabled { color: #A9B3C3; background: #F4F6F9; border-color: #E4E9F0; }
QPushButton#runButton { background: #4169E1; color: #FFFFFF; border: 1px solid #4169E1; font-weight: 600; padding: 10px 22px; }
QPushButton#runButton:hover { background: #3156C9; }
QPushButton#runButton:disabled { background: #CDD7ED; border-color: #CDD7ED; color: #F5F7FD; }
QPushButton#stopButton { color: #975248; }
QPushButton#stopButton:disabled { color: #A9B3C3; }
QWidget#fingerprint { background: #EEF3FF; border: 1px solid #D9E4FF; border-radius: 7px; }
QLabel#digestHeading { color: #7184A6; font-size: 11px; }
QLabel#digest { color: #3155A0; font-family: "Cascadia Mono", Consolas; font-size: 17px; font-weight: 600; }
QLabel#summary { background: #F4F7FB; border-radius: 5px; padding: 10px; color: #64758D; }
QLabel#summary[state="running"] { background: #EEF3FF; color: #3155A0; }
QLabel#summary[state="success"] { background: #EDF6F2; color: #287254; }
QLabel#summary[state="error"] { background: #FBF0ED; color: #A34B38; }
QTabWidget::pane { border: 1px solid #DFE5EF; border-radius: 5px; background: #FFFFFF; }
QTabBar::tab { padding: 9px 16px; color: #8290A5; border-bottom: 2px solid transparent; }
QTabBar::tab:selected { color: #3155A0; border-bottom: 2px solid #4169E1; }
QPlainTextEdit { background: #FBFCFE; border: none; padding: 10px; font-family: "Cascadia Mono", Consolas, "Microsoft YaHei UI"; font-size: 12px; color: #3C506B; selection-background-color: #D5E2FF; }
QWidget#taskBar { background: #FFFFFF; border: 1px solid #DBE3EE; border-radius: 8px; }
QLabel#taskStatus { color: #748198; font-size: 12px; }
QProgressBar { background: #E9EEF6; border: none; border-radius: 3px; min-height: 6px; max-height: 6px; }
QProgressBar::chunk { background: #6B8AE8; border-radius: 3px; }
QSplitter::handle { background: transparent; width: 14px; }
QScrollBar:vertical { width: 7px; background: transparent; margin: 3px; }
QScrollBar::handle:vertical { background: #CDD7E5; min-height: 25px; border-radius: 3px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
'''
