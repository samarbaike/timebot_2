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


async def _resolve_setsheet_target(message: Message, database: DatabaseManager):
    """Figures out which group a /setsheet call targets, and confirms the
    caller is an admin of it. In a group chat the target is just the chat
    itself; in a DM there's no group to point at, so it falls back to the
    admin's own linked group (the same group_id set at registration /
    resolve_user_group time — each user is tied to exactly one group).
    Returns (group_id, title) on success, or None after already sending
    the appropriate error reply."""
    if message.chat.type in ("group", "supergroup"):
        group_id, title = message.chat.id, message.chat.title
    else:
        group = await database.groups.get_by_user(message.from_user.id)
        if group is None:
            await message.reply(
                "❌ Sizdin qaisy gruppaga taandyq ekeniŋizdi tabalbadym.\n\n"
                "Bul buiruqtu tiiştüü gruppanyn ichinde jazyŋyz, je aldy menen /start basyp qattaluŋuz."
            )
            return None
        group_id, title = group['group_id'], group['title']

    member = await message.bot.get_chat_member(group_id, message.from_user.id)
    if member.status not in ("administrator", "creator"):
        await message.reply("⛔ Bul buiruqtu tek gana gruppanyn admini qoldono alat.")
        return None

    return group_id, title


@router.message(Command("setsheet"), F.chat.type.in_({"group", "supergroup", "private"}))
async def set_group_sheet(message: Message, database: DatabaseManager, command: CommandObject):
    """Lets a group admin attach a group's Google Sheet, e.g.:
    /setsheet 1jpV8B5rMd5FfNqMmrfxxShMfaZvLd1aDG-HdGIEtzoM
    The spreadsheet_id is the long id in the sheet's URL between /d/ and /edit.
    Works either as a message inside the group itself, or as a DM to the
    bot — in the DM case the target group is inferred from the admin's own
    registered group_id. Either way the caller must be a Telegram admin of
    that group; there's no separate bot-admin allowlist to maintain."""
    target = await _resolve_setsheet_target(message, database)
    if target is None:
        return
    group_id, group_title = target

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

    await database.groups.set_spreadsheet(group_id, spreadsheet_id, sheet_url)
    await message.reply(f"✅ '{group_title}' gruppasynyn sheet-i ornotuldu:\n{sheet_url}")