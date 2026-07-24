import logging
import sys
import os
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from handlers.start import router
from database.db import DatabaseManager
from dotenv import load_dotenv
import pandas as pd
import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from services.sheets import GoogleSheetManager
from handlers.inline import router as inline_router
from handlers.manage_books import router as manage_books_router


logging.basicConfig(level=logging.INFO, stream=sys.stdout)

load_dotenv()
db_url = os.getenv("DB_URL")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Attach the router here
dp.include_router(router)
dp.include_router(inline_router)
dp.include_router(manage_books_router)

async def health_check(request):
    return web.Response(text="Bot is alive!")


# ---- THE ETL BRIDGE PIPELINE ----
async def run_midnight_export(db: DatabaseManager):
    """Executes the scheduled ETL pipeline to Google Sheets, once per group.
    Each group has its own spreadsheet (configured via /setsheet), so this
    loops over every active group that has one set and exports that group's
    data only — no more dumping every group's logs into one shared sheet."""
    logging.info("Initiating scheduled Google Sheets export...")

    groups = await db.groups.get_all_with_sheet()
    if not groups:
        logging.info("Export aborted: no groups have a spreadsheet configured yet.")
        return

    # One authenticated client is reused across every group's export.
    try:
        sheet_manager = GoogleSheetManager()
    except Exception as e:
        logging.error(f"❌ FATAL ERROR setting up Google Sheets client: {e}")
        return

    for group in groups:
        group_id = group['group_id']
        try:
            # 1. EXTRACT (From db.py), scoped to this group
            raw_records = await db.migration.get_for_group(group_id)
            data = [dict(record) for record in raw_records]

            if not data:
                logging.info(f"Skipping group {group_id} ({group['title']}): no reading logs yet.")
                continue

            # TRANSFORM
            df = pd.DataFrame(data)
            df['log_date'] = pd.to_datetime(df['log_date'])

            # LOAD
            sheet_manager.upload_both_tabs(df, group['spreadsheet_id'])

            logging.info(f"✅ Export completed for group {group_id} ({group['title']}).")

        except Exception as e:
            # One group's failure (bad sheet ID, revoked sharing, etc.) shouldn't
            # block the rest of the groups from exporting.
            logging.error(f"❌ Export failed for group {group_id} ({group['title']}): {e}")

    logging.info("Scheduled Google Sheets export run finished.")

#--- WEB SERVER ---
async def start_dummy_server():
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8000)
    await site.start()

async def main():
    db = DatabaseManager()
    logging.info("1. Connecting to Database...")
    await db.connect(db_url)
    await db.create_table()
    # Start the fake web server to satisfy Koyeb
    logging.info("2. Starting dummy web server on port 8000...")
    await start_dummy_server()
    
    # --- ORCHESTRATE THE BACKGROUND CLOCK ---
    logging.info("3. Igniting APScheduler background clock...")
    scheduler = AsyncIOScheduler(timezone="Asia/Bishkek")
    
    # TODO: CHANGE THESE NUMBERS FOR YOUR TEST RUN
    test_hour = 0
    test_minute = 0 # Set this to 2 minutes from your current local time
    
    scheduler.add_job(
        run_midnight_export, 
        trigger='cron', 
        hour=test_hour,      
        minute=test_minute,   
        args=[db]
    )
    scheduler.start()
    # Start the actual Telegram bot
    logging.info("4. Starting Telegram polling. Bot is live.")
    await dp.start_polling(bot, database=db)



if __name__ == "__main__":
    asyncio.run(main())