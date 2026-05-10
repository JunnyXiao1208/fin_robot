# -*- coding: utf-8 -*-
import json
import re
from typing import Any


def safe_json_loads(text: str, default: Any = None) -> Any:
    if not text or not text.strip():
        return default if default is not None else {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return default if default is not None else {}
        return default if default is not None else {}
