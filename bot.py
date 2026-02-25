import os
import asyncio
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

async def main():
    db = DatabaseManager()
    await db.connect(db_url)
    await db.create_table()
    await dp.start_polling(bot, database=db)

if __name__ == "__main__":
    asyncio.run(main())