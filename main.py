#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
《一箭又一箭》益智解谜小游戏
软件工程课程个人作业（第二次）

运行方法：
    python main.py
"""

import sys
import os

# 确保将当前目录加入模块搜索路径
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from src.game_app import GameApp


def main():
    try:
        app = GameApp(width=960, height=720)
        app.run()
    except Exception as e:
        print(f"游戏运行出现异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
