"""
* 手写作业OCR识别与批改系统 - 统一启动器
* 双击即用：自动启动后端服务 + 前端GUI
* create by 林文光
* copyright USTC
* 2026.03.07
"""
import sys
import os
import subprocess
import time
import signal
import atexit
import requests

# 确定项目根目录（兼容pyinstaller打包后的路径）
if getattr(sys, 'frozen', False):
    # pyinstaller打包后的运行路径
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

BACKEND_DIR = os.path.join(BASE_DIR, 'backend')
FRONTEND_DIR = os.path.join(BASE_DIR, 'frontend')

BACKEND_HOST = '127.0.0.1'
BACKEND_PORT = 5000
HEALTH_URL = f'http://{BACKEND_HOST}:{BACKEND_PORT}/api/health'

# 后端子进程句柄
_backend_process = None


def start_backend():
    """启动后端Flask服务作为子进程"""
    global _backend_process

    python_exe = sys.executable
    backend_script = os.path.join(BACKEND_DIR, 'app.py')

    if not os.path.exists(backend_script):
        print(f"[错误] 找不到后端脚本: {backend_script}")
        return False

    # 用当前python解释器启动后端，隐藏控制台窗口(Windows)
    creation_flags = 0
    if sys.platform == 'win32':
        creation_flags = subprocess.CREATE_NO_WINDOW

    _backend_process = subprocess.Popen(
        [python_exe, backend_script],
        cwd=BACKEND_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=creation_flags,
    )

    # 等待后端就绪（最多等15秒）
    for i in range(30):
        time.sleep(0.5)
        try:
            resp = requests.get(HEALTH_URL, timeout=2)
            if resp.status_code == 200:
                print(f"[启动器] 后端服务已就绪 (PID: {_backend_process.pid})")
                return True
        except requests.ConnectionError:
            pass

        # 检查进程是否已意外退出
        if _backend_process.poll() is not None:
            stderr = _backend_process.stderr.read().decode('utf-8', errors='replace')
            print(f"[错误] 后端启动失败:\n{stderr}")
            return False

    print("[错误] 后端服务启动超时")
    return False


def stop_backend():
    """停止后端子进程"""
    global _backend_process
    if _backend_process and _backend_process.poll() is None:
        print("[启动器] 正在关闭后端服务...")
        if sys.platform == 'win32':
            _backend_process.terminate()
        else:
            _backend_process.send_signal(signal.SIGTERM)
        try:
            _backend_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _backend_process.kill()
        print("[启动器] 后端服务已关闭")


def check_backend_already_running():
    """检查后端是否已经在运行"""
    try:
        resp = requests.get(HEALTH_URL, timeout=2)
        return resp.status_code == 200
    except Exception:
        return False


def start_frontend():
    """启动前端GUI"""
    # 将frontend目录加入path，使其import能正常工作
    sys.path.insert(0, FRONTEND_DIR)
    os.chdir(FRONTEND_DIR)

    from PyQt5.QtWidgets import QApplication, QMessageBox, QSplashScreen
    from PyQt5.QtGui import QPixmap, QFont
    from PyQt5.QtCore import Qt

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("手写作业OCR批改系统")

    # 加载样式表
    style_path = os.path.join(FRONTEND_DIR, 'ui', 'resources', 'style.qss')
    if os.path.exists(style_path):
        with open(style_path, 'r', encoding='utf-8') as f:
            app.setStyleSheet(f.read())

    from ui.main_window import MainWindow
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


def main():
    print("=" * 50)
    print("  手写作业OCR识别与批改系统")
    print("=" * 50)

    # 注册退出时清理后端进程
    atexit.register(stop_backend)

    # 检查后端是否已在运行
    if check_backend_already_running():
        print("[启动器] 检测到后端服务已在运行，直接启动前端")
    else:
        print("[启动器] 正在启动后端服务...")
        if not start_backend():
            # 后端启动失败，弹窗提示但仍尝试启动前端
            print("[警告] 后端启动失败，前端将以离线模式启动")

    # 启动前端GUI
    print("[启动器] 正在启动前端界面...")
    start_frontend()


if __name__ == '__main__':
    main()
