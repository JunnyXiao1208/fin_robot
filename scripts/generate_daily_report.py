# -*- coding: utf-8 -*-
import asyncio
import json

from core.database.repositories import signal_repo


async def main():
    items = signal_repo.query_ingested(limit=20)
    print(json.dumps(items, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
