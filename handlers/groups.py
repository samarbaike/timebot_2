from aiogram import F, Router
from aiogram.types import ChatMemberUpdated, Message
from aiogram.filters import ChatMemberUpdatedFilter, JOIN_TRANSITION, LEAVE_TRANSITION, Command, CommandObject
import gspread

from database.db import DatabaseManager
from services.sheets import GoogleSheetManager

router = Router()


@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=JOIN_TRANSITION))
async def bot_joined_group(event: ChatMemberUpdated, database: DatabaseManager):
    """Fires whenever the bot's own membership in a chat flips to
    member/administrator. Only group/supergroup chats are registered —
    this same event also fires for private chats when a user hits /start,
    which we don't want landing in the groups table."""
    if event.chat.type in ("group", "supergroup"):
        await database.groups.add(event.chat.id, event.chat.title)


@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=LEAVE_TRANSITION))
async def bot_left_group(event: ChatMemberUpdated, database: DatabaseManager):
    """Fires when the bot is kicked or leaves. We deactivate rather than
    delete so the spreadsheet link survives if the bot is re-added later."""
    if event.chat.type in ("group", "supergroup"):
        await database.groups.deactivate(event.chat.id)


@router.message(Command("setsheet"), F.chat.type.in_({"group", "supergroup"}))
async def set_group_sheet(message: Message, database: DatabaseManager, command: CommandObject):
    """Lets a group admin attach this group's Google Sheet, e.g.:
    /setsheet 1jpV8B5rMd5FfNqMmrfxxShMfaZvLd1aDG-HdGIEtzoM
    The spreadsheet_id is the long id in the sheet's URL between /d/ and /edit.
    Must be run as a message inside the group itself, by a Telegram admin
    of that group — there's no separate bot-admin allowlist to maintain."""
    member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
    if member.status not in ("administrator", "creator"):
        await message.reply("⛔ Bul buiruqtu tek gana gruppanyn admini qoldono alat.")
        return

    if not command.args:
        await message.reply(
            "Colondonuu: /setsheet <spreadsheet_id>\n\n"
            "spreadsheet_id — sheet shiltemesindegi /d/ menen /edit ortosundagy uzun kod."
        )
        return

    spreadsheet_id = command.args.split()[0].strip()
    sheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"

    try:
        sheet_manager = GoogleSheetManager()
    except Exception:
        await message.reply(
            "⚠️ Bot azyrynca Google Sheets menen ishtei albait — kiyinirek qaira araket qylyŋyz."
        )
        return

    try:
        sheet_manager.check_access(spreadsheet_id)
    except gspread.exceptions.SpreadsheetNotFound:
        await message.reply(
            "❌ Bot bul sheet-ke qire albait.\n\n"
            f"Sheet-ti myna email menen bölüshüŋüz (Editor qukugu menen):\n`{sheet_manager.client_email}`\n\n"
            "Andan kiyin kaira /setsheet buirugun colondonuŋuz.",
            parse_mode="Markdown"
        )
        return
    except gspread.exceptions.APIError:
        await message.reply(
            "❌ Bot bul sheet-ke kire albait — uqugu zhetishsiz bolushu mumkun.\n\n"
            f"Sheet-ti myna email menen bölüshüŋüz (Editor qukugu menen):\n`{sheet_manager.client_email}`\n\n"
            "Andan kiyin kaira /setsheet buirugun colondonuŋuz.",
            parse_mode="Markdown"
        )
        return

    await database.groups.set_spreadsheet(message.chat.id, spreadsheet_id, sheet_url)
    await message.reply(f"✅ Bul gruppanyn sheet-i ornotuldu:\n{sheet_url}")