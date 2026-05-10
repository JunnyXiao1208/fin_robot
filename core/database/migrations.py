# -*- coding: utf-8 -*-
from core.database.db import init_database, _migrate

__all__ = ["init_database", "migrate"]


def migrate():
    import sqlite3
    conn = sqlite3.connect("")
    try:
        _migrate(conn)
        conn.commit()
    finally:
        conn.close()
