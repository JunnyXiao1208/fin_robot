#!/usr/bin/env python
"""
Git pre-commit hook — 提交前自动扫描硬编码密钥

安装方式（在项目根目录执行）：
  python scripts/install_hooks.py
"""
import os
import re
import subprocess
import sys


SECRET_PATTERNS = [
    (r"""['"]sk-[a-zA-Z0-9]{20,}['"]""", "疑似 API Key (sk-...)"),
    (r"""['"]tp-[a-zA-Z0-9]{20,}['"]""", "疑似 Token (tp-...)"),
    (r"""Bearer\s+AAAA[A-Za-z0-9%+/=]+""", "疑似 Bearer Token"),
    (r"""['"][A-Za-z0-9+/=]{50,}['"]""", "疑似长密钥串 (50+ chars)"),
    (r"""os\.environ\[['"][\w]+['"]\]\s*=\s*['"][A-Za-z0-9_-]{20,}""", "硬编码环境变量赋值"),
]


def main():
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            capture_output=True, text=True, check=True,
        )
        staged_files = [f for f in result.stdout.strip().splitlines() if f.endswith(".py")]
    except subprocess.CalledProcessError:
        staged_files = []

    if not staged_files:
        sys.exit(0)

    print("[pre-commit] 正在扫描硬编码密钥...")
    has_issue = False

    for filepath in staged_files:
        if not os.path.exists(filepath):
            continue
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for i, line in enumerate(f, 1):
                for pattern, desc in SECRET_PATTERNS:
                    if re.search(pattern, line):
                        print(f"  !  {filepath}:{i} -- {desc}")
                        print(f"      {line.strip()[:80]}")
                        has_issue = True

    if has_issue:
        print("\n[pre-commit] 检测到硬编码密钥，提交已阻止！")
        print("[pre-commit] 请将密钥抽离到 .env 文件，然后用 os.getenv() 读取")
        sys.exit(1)
    else:
        print("[pre-commit] 未检测到硬编码密钥")


if __name__ == "__main__":
    main()
