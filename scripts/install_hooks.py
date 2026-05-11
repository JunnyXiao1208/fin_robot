#!/usr/bin/env python
"""安装 Git pre-commit 钩子到本地 .git/hooks/"""
import os
import shutil
import sys

HOOK_SOURCE = os.path.join(os.path.dirname(__file__), "pre_commit_hook.py")
HOOK_TARGET = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".git", "hooks", "pre-commit")


def main():
    if not os.path.exists(HOOK_SOURCE):
        print(f"源文件不存在: {HOOK_SOURCE}")
        sys.exit(1)

    os.makedirs(os.path.dirname(HOOK_TARGET), exist_ok=True)
    shutil.copy2(HOOK_SOURCE, HOOK_TARGET)
    print(f"pre-commit 钩子已安装: {HOOK_TARGET}")
    print("以后每次 git commit 前会自动扫描硬编码密钥")


if __name__ == "__main__":
    main()
