# -*- coding: utf-8 -*-
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from configs.settings import PROJECT_ROOT
from core.database.db import init_database
from services.ingestion_service import ingest_rss_items


async def main():
    init_database()
    result = await ingest_rss_items(limit_per_feed=None, keyword_filter=True)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
