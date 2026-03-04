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

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

load_dotenv()
db_url = os.getenv("DB_URL")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Attach the router here
dp.include_router(router)

async def health_check(request):
    return web.Response(text="Bot is alive!")


# ---- THE ETL BRIDGE PIPELINE ----
async def run_midnight_export(db: DatabaseManager):
    """Executes the scheduled ETL pipeline to Google Sheets."""
    logging.info("Initiating scheduled Google Sheets export...")
    try:
        # 1. EXTRACT (From db.py)
        raw_records = await db.migration.get()
        data = [dict(record) for record in raw_records]
        
        if not data:
            logging.info("Export aborted: Database is empty.")
            return

        # 2. TRANSFORM (From your blank.py experiments)
        df = pd.DataFrame(data)
        pivot_df = df.pivot_table(
            index='full_name', 
            columns='log_date', 
            values='pages_read', 
            aggfunc='sum', 
            fill_value=0
        )
        
        pivot_df.columns = [col.strftime('%Y-%m-%d') if isinstance(col, datetime.date) else col for col in pivot_df.columns]
        final_df = pivot_df.reset_index().rename(columns={'full_name': 'Name Surname'})
        
        # 3. LOAD (From sheets.py)
        sheet_manager = GoogleSheetManager()
        sheet_manager.upload_dataframe(final_df)
        
        logging.info("✅ Scheduled export successfully completed.")
        
    except Exception as e:
        logging.error(f"❌ FATAL ERROR during scheduled export: {e}")

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