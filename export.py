"""
Runs run_midnight_export() a single time, immediately, so you don't have to
wait for the cron trigger (or edit bot.py's test_hour/test_minute) to test
the Sheets export.

Usage:
    python3 run_export_once.py
"""
import asyncio
import os
import logging
import sys
from dotenv import load_dotenv

from database.db import DatabaseManager
from bot import run_midnight_export

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
load_dotenv()
db_url = os.getenv("DB_URL")


async def main():
    db = DatabaseManager()
    await db.connect(db_url)
    await run_midnight_export(db)


if __name__ == "__main__":
    asyncio.run(main())