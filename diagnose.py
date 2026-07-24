"""
Quick diagnostic — run this once, standalone, to check:
1. What allowed_updates aiogram will actually request based on your routers
2. Whether there's a leftover webhook still registered (which SILENTLY
   blocks all polling — bot.py's dp.start_polling() would just hang/get
   nothing, with no error, if a webhook URL is still set on Telegram's side)

Usage:
    python3 diagnose.py
"""
import asyncio
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from handlers.start import router
from handlers.groups import router as groups_router
from handlers.inline import router as inline_router
from handlers.manage_books import router as manage_books_router


async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    dp.include_router(groups_router)
    dp.include_router(inline_router)
    dp.include_router(manage_books_router)

    # 1. What update types will aiogram actually ask Telegram for?
    allowed = dp.resolve_used_update_types()
    print("=== allowed_updates aiogram will request ===")
    print(allowed)
    if "my_chat_member" not in allowed:
        print("!! 'my_chat_member' is NOT in this list — that's the bug.")
    else:
        print("OK: 'my_chat_member' is included.")

    # 2. Is a webhook still set? If so, polling silently gets nothing.
    print("\n=== webhook info ===")
    info = await bot.get_webhook_info()
    print(info)
    if info.url:
        print(f"!! A webhook is still registered at: {info.url}")
        print("!! This blocks getUpdates()/polling from receiving ANYTHING.")
        print("!! Fix: await bot.delete_webhook(drop_pending_updates=True)")
    else:
        print("OK: no webhook set, polling should work.")

    await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())