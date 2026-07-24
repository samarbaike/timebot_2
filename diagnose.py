"""
Diagnose why the midnight Sheets export isn't picking up rows that clearly
exist in reading_logs.

Checks, in order:
1. Which active groups actually have a spreadsheet configured (/setsheet).
2. For each of those groups, how many reading_logs rows get_for_group()
   would actually return.
3. Whether there are users with logged pages but group_id = NULL — these
   rows exist in reading_logs but are invisible to the export's
   `WHERE u.group_id = $1` filter.

Usage:
    python3 diagnose_export.py
"""
import asyncio
import os
from dotenv import load_dotenv
import asyncpg

load_dotenv()
DB_URL = os.getenv("DB_URL")


async def main():
    pool = await asyncpg.create_pool(DB_URL)
    async with pool.acquire() as conn:

        print("=== Active groups with a spreadsheet configured ===")
        groups = await conn.fetch("""
            SELECT group_id, title, spreadsheet_id
            FROM groups
            WHERE is_active = TRUE AND spreadsheet_id IS NOT NULL
        """)
        if not groups:
            print("!! No active group has a spreadsheet set — run /setsheet first.")
            print("!! (this alone would explain zero export activity)")
        for g in groups:
            print(f"   group_id={g['group_id']}  title={g['title']!r}  spreadsheet_id={g['spreadsheet_id']}")

        total_logs = await conn.fetchval("SELECT COUNT(*) FROM reading_logs")
        print(f"\nTotal rows in reading_logs: {total_logs}")

        print("\n=== Rows get_for_group() would actually export, per group ===")
        for g in groups:
            gid = g['group_id']
            picked_up = await conn.fetchval("""
                SELECT COUNT(*)
                FROM users u
                JOIN reading_logs r ON u.telegram_id = r.user_id
                WHERE u.group_id = $1
            """, gid)
            flag = "" if picked_up else "   !! zero rows, but group has a sheet set"
            print(f"   group_id={gid} ({g['title']}): {picked_up} rows{flag}")

        print("\n=== Users who logged pages but have group_id = NULL ===")
        orphaned = await conn.fetch("""
            SELECT u.telegram_id, u.user_name, u.user_surname, COUNT(r.log_id) AS log_count
            FROM users u
            JOIN reading_logs r ON u.telegram_id = r.user_id
            WHERE u.group_id IS NULL
            GROUP BY u.telegram_id, u.user_name, u.user_surname
        """)
        if orphaned:
            print(f"!! Found {len(orphaned)} user(s) with logged pages but no group_id:")
            for row in orphaned:
                print(f"   {row['user_name']} {row['user_surname']} (id={row['telegram_id']}): {row['log_count']} log(s)")
            print("\n!! These rows exist in reading_logs but get_for_group() will never")
            print("!! return them (INNER JOIN on u.group_id = $1 excludes NULLs).")
            print("!! Fix: have these users send /start again to trigger the backfill")
            print("!! in handlers/start.py, or backfill directly, e.g.:")
            print("!!   UPDATE users SET group_id = <group_id> WHERE telegram_id = <id>;")
        else:
            print("OK: every user with logged pages already has a group_id set.")

    await pool.close()


if __name__ == "__main__":
    asyncio.run(main())