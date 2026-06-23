"""
* 应用启动引导 - 统一 QApplication/样式/登录/按角色开窗
* main.py 与 launcher.py 均调用 run_app()，避免重复逻辑
* create by 林文光
* copyright USTC
* 2026.06.22
"""
import os
import sys

from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt


def run_app() -> int:
    """启动应用：构建 QApplication → 登录 → 按角色打开主窗口。返回退出码。"""
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("手写作业OCR批改系统")

    # 加载全局样式
    style_path = os.path.join(os.path.dirname(__file__), 'ui', 'resources',
                              'style.qss')
    if os.path.exists(style_path):
        with open(style_path, 'r', encoding='utf-8') as f:
            app.setStyleSheet(f.read())

    from api_client import ApiClient
    from ui.login_dialog import LoginDialog

    api = ApiClient()

    # 后端不可用时给出提示但仍弹登录框（登录会失败并显示连接错误）
    health = api.health_check()
    if health.get('status') != 'ok':
        QMessageBox.warning(None, "后端未连接",
                            "无法连接后端服务，请先启动 backend/app.py。\n"
                            "登录功能将不可用。")

    login = LoginDialog(api)
    if login.exec_() != LoginDialog.Accepted:
        return 0

    api.set_current_user(login.user_id)

    if login.role == 'teacher':
        from ui.main_window import MainWindow
        window = MainWindow(api, user_id=login.user_id)
    else:
        from ui.student_main_window import StudentMainWindow
        window = StudentMainWindow(api, user_id=login.user_id,
                                   display_name=login.display_name)

    # 修复"登入后窗口不显示但进程还在"：窗口其实已创建，只是被挡在后面或
    # 因旧的几何位置跑到屏外看不见。三道保险：持久引用防回收 + 强制置顶激活 + 离屏拽回主屏。
    app._main_window = window
    _ensure_on_screen(window)
    window.show()
    window.raise_()
    window.activateWindow()
    return app.exec_()


def _ensure_on_screen(window):
    """窗口左上角若不在主屏可用区域内，移回主屏左上，避免因旧几何位置看不见。"""
    screen = QApplication.primaryScreen()
    if screen is None:
        return
    avail = screen.availableGeometry()
    if not avail.contains(window.frameGeometry().topLeft()):
        window.move(avail.topLeft())


if __name__ == '__main__':
    sys.exit(run_app())
