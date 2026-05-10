# -*- coding: utf-8 -*-
"""
settings.py — 集中配置模块，从 .env 读取所有配置。
"""

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

DB_PATH = os.getenv("SQLITE_DB_PATH", "")
if not DB_PATH:
    DB_PATH = str(PROJECT_ROOT / "data" / "fin_robot.db")
elif not os.path.isabs(DB_PATH):
    DB_PATH = str(PROJECT_ROOT / DB_PATH)

ACTIVE_MODEL = os.getenv("ACTIVE_MODEL", "zhipu")
X_AUTH_TOKEN = os.getenv("X_AUTH_TOKEN", "")
PROXY = os.getenv("HTTPS_PROXY", os.getenv("HTTP_PROXY", "")).strip()

X_TRACKED_USERS = os.getenv("X_TRACKED_USERS", "[]")
