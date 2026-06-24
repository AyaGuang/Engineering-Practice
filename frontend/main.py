"""
* 前端入口 - PyQt5 应用启动点，委托 app_bootstrap.run_app() 完成登录与按角色开窗
* 启动方式: python main.py（在 frontend 目录下执行）
* create by 林嘉晨
* copyright USTC
* 2026.03.13
"""
import sys

from app_bootstrap import run_app


def main():
    sys.exit(run_app())


if __name__ == '__main__':
    main()
