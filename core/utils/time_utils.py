# -*- coding: utf-8 -*-
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime


def to_iso_datetime(entry) -> str:
    for key in ("published", "updated"):
        raw_value = entry.get(key)
        if not raw_value:
            continue
        try:
            dt = parsedate_to_datetime(raw_value)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat()
        except (TypeError, ValueError, IndexError, OverflowError):
            continue
    for key in ("published_parsed", "updated_parsed"):
        parsed_value = entry.get(key)
        if not parsed_value:
            continue
        try:
            return datetime(*parsed_value[:6], tzinfo=timezone.utc).isoformat()
        except (TypeError, ValueError):
            continue
    return datetime.now(timezone.utc).isoformat()
