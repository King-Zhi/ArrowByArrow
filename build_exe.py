#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
《一箭又一箭》自动化打包脚本
使用 PyInstaller 将项目打包为免安装的单文件 Windows 可执行程序 (.exe)
"""

import os
import sys
import subprocess


def main():
    print("=" * 60)
    print("  《一箭又一箭 - 赛博合成波街机版》 一键打包工具")
    print("=" * 60)

    # 1. 检查 PyInstaller 是否已安装
    try:
        import PyInstaller
        print(f"[OK] 检测到 PyInstaller 版本: {PyInstaller.__version__}")
    except ImportError:
        print("[!] 未检测到 PyInstaller，正在安装 pyinstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # 2. 准备打包参数
    sep = ";" if sys.platform.startswith("win") else ":"
    data_arg = f"assets{sep}assets"

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "ArrowByArrow",
        "--onefile",
        "--windowed",
        "--icon", "assets/icon.ico",
        "--add-data", data_arg,
        "--clean",
        "--noconfirm",
        "main.py"
    ]

    print(f"\n[EXEC] 执行打包命令: {' '.join(cmd)}")
    result = subprocess.run(cmd)

    if result.returncode == 0:
        exe_ext = ".exe" if sys.platform.startswith("win") else ""
        out_path = os.path.join("dist", f"ArrowByArrow{exe_ext}")
        if os.path.exists(out_path):
            size_mb = os.path.getsize(out_path) / (1024 * 1024)
            print("\n" + "=" * 60)
            print("  [SUCCESS] 打包圆满完成！")
            print(f"  生成可执行文件: {os.path.abspath(out_path)}")
            print(f"  文件体积: {size_mb:.2f} MB")
            print("  您可以直接双击该 EXE 文件进行免安装即开即玩，无需配置任何 Python 环境。")
            print("=" * 60)
        else:
            print("\n[!] 打包完成，但未找到预期的输出文件，请检查 dist/ 目录。")
    else:
        print(f"\n[FAIL] 打包失败，退出码: {result.returncode}")


if __name__ == "__main__":
    main()
