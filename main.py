# -*- coding: utf-8 -*-
"""
保留的旧版入口，保持兼容。
所有新代码应使用 services/ingestion_service.py。
"""

import asyncio
import json
import logging
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        return False

logger = logging.getLogger(__name__)

# 新的导入路径
os.environ.setdefault("FIN_ROBOT_ROOT", str(Path(__file__).resolve().parent))

from scripts.run_rss import main as run_rss

__all__ = ["run_rss"]
