import os
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from handlers.start import router
from database.db import DatabaseManager
from dotenv import load_dotenv


load_dotenv()
db_url = os.getenv("DB_URL")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Attach the router here
dp.include_router(router)

async def health_check(request):
    return web.Response(text="Bot is alive!")

async def start_dummy_server():
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8000)
    await site.start()

async def main():
    db = DatabaseManager()
    await db.connect(db_url)
    await db.create_table()
    await dp.start_polling(bot, database=db)
    # Start the fake web server to satisfy Koyeb
    await start_dummy_server()
    
    # Start the actual Telegram bot
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())