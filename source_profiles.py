# -*- coding: utf-8 -*-
"""
source_profiles.py — 保留的兼容入口。
所有新代码应使用 configs/source_profiles.py。
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from configs.source_profiles import (
    SOURCE_CATEGORIES,
    CATEGORY_VALUES,
    get_source_category,
    attach_source_category,
)

__all__ = [
    "SOURCE_CATEGORIES",
    "CATEGORY_VALUES",
    "get_source_category",
    "attach_source_category",
]
