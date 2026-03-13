"""
* 打包脚本 - 将系统打包为Windows可执行文件
* 使用方法: python build_exe.py
* 不建议用户使用，仅供开发者后续为程序封包，目前仅展示部分代码，仍然在开发中
* create by 林文光
* copyright USTC
* 2026.03.09
"""
import subprocess
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def build():
    print("=" * 50)
    print("  开始打包: 手写作业OCR识别与批改系统")
    print("=" * 50)

    # 确认pyinstaller已安装
    try:
        import PyInstaller
        print(f"[OK] PyInstaller版本: {PyInstaller.__version__}")
    except ImportError:
        print("[安装] 正在安装PyInstaller...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyinstaller'])

    # PyInstaller参数
    args = [
        sys.executable, '-m', 'PyInstaller',
        '--name', 'HomeworkGrader',      # exe名称
        '--windowed',                     # 无控制台窗口
        '--noconfirm',                    # 覆盖旧的输出
        # 打包后端代码和资源
        '--add-data', f'backend{os.pathsep}backend',
        '--add-data', f'frontend{os.pathsep}frontend',
        '--add-data', f'templates{os.pathsep}templates',
        # 隐式导入（pyinstaller可能检测不到的模块）
        '--hidden-import', 'flask',
        '--hidden-import', 'flask_cors',
        '--hidden-import', 'sqlalchemy',
        '--hidden-import', 'sqlalchemy.dialects.sqlite',
        '--hidden-import', 'paddleocr',
        '--hidden-import', 'paddle',
        '--hidden-import', 'fuzzywuzzy',
        '--hidden-import', 'Levenshtein',
        '--hidden-import', 'cv2',
        '--hidden-import', 'PIL',
        '--hidden-import', 'numpy',
        '--hidden-import', 'requests',
        '--hidden-import', 'PyQt5',
        '--hidden-import', 'PyQt5.QtWidgets',
        '--hidden-import', 'PyQt5.QtCore',
        '--hidden-import', 'PyQt5.QtGui',
        # 入口文件
        'launcher.py',
    ]

    print("\n[打包] 执行PyInstaller...")
    print(f"命令: {' '.join(args)}\n")

    result = subprocess.run(args, cwd=BASE_DIR)

    if result.returncode == 0:
        dist_dir = os.path.join(BASE_DIR, 'dist', 'HomeworkGrader')
        print("\n" + "=" * 50)
        print("  打包成功!")
        print(f"  输出目录: {dist_dir}")
        print(f"  可执行文件: {os.path.join(dist_dir, 'HomeworkGrader.exe')}")
        print("=" * 50)
        print("\n注意事项:")
        print("1. 首次运行会自动下载PaddleOCR模型（需联网）")
        print("2. 确保目标机器上 backend/ 和 frontend/ 目录与exe在同一层级")
        print("3. 如果打包后体积过大，可考虑使用 --onedir 模式（默认）")
    else:
        print(f"\n[错误] 打包失败，退出码: {result.returncode}")

    return result.returncode


if __name__ == '__main__':
    sys.exit(build())
