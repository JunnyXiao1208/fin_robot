# -*- coding: utf-8 -*-
import asyncio
import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

from core.database.db import init_database
from services.ingestion_service import ingest_rss_items


async def main():
    init_database()
    result = await ingest_rss_items(limit_per_feed=1, keyword_filter=False)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
