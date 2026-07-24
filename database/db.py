import datetime
from zoneinfo import ZoneInfo
from abc import ABC, abstractmethod
import asyncpg

class BaseRepository(ABC):
    """
    This is Abstract Class. You cannot instantiate it directly.
    It serves as a blueprint for other classes
    """
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    @abstractmethod
    async def add(self, *args, **kwargs):
        """Must be implemented by child classes to insert records"""
        pass

    @abstractmethod
    async def get(self, *args, **kwargs):
        """Must implemented by child classes to retrieve records"""
        pass

class UserRepository(BaseRepository):
    """
    Inherits from BaseRepository, managin users table
    """
    async def add(self, telegram_id: int, user_name: str, user_surname: str, group_id: int | None = None):
        query="""
        INSERT INTO users (telegram_id, user_name, user_surname, group_id) VALUES ($1, $2, $3, $4)
        """
        async with self._pool.acquire() as connection:
            await connection.execute(query, telegram_id, user_name, user_surname, group_id)
    async def get(self, telegram_id:int):
        query = """
        SELECT telegram_id FROM users WHERE telegram_id=$1"""
        async with self._pool.acquire() as connection:
            fetchedval = await connection.fetchval(query, telegram_id)

        return fetchedval
    async def get_full(self, telegram_id: int):
        async with self._pool.acquire() as conn:
            return await conn.fetchrow(
                "SELECT telegram_id, user_name, user_surname, group_id FROM users WHERE telegram_id = $1",
                telegram_id
            )
    async def set_group(self, telegram_id: int, group_id: int):
        """Links (or re-links) a user to the group they were matched against.
        Used both at registration time and to backfill legacy users who
        registered before group-matching existed."""
        async with self._pool.acquire() as connection:
            await connection.execute(
                "UPDATE users SET group_id = $2 WHERE telegram_id = $1",
                telegram_id, group_id
            )

class GroupRepository(BaseRepository):
    """
    Inherits from BaseRepository, managing the groups table.
    A "group" here is a Telegram group chat the bot has been added to.
    Each group can optionally have its own Google Sheet configured for
    the midnight export.
    """
    async def add(self, group_id: int, title: str):
        """Registers a group the bot was just added to. If the bot had
        previously been kicked/left and is now re-added, this reactivates
        the existing row (and its spreadsheet link) instead of losing it."""
        async with self._pool.acquire() as connection:
            await connection.execute("""
                INSERT INTO groups (group_id, title, is_active)
                VALUES ($1, $2, TRUE)
                ON CONFLICT (group_id) DO UPDATE
                    SET title = EXCLUDED.title, is_active = TRUE
                """, group_id, title)

    async def get(self, group_id: int):
        async with self._pool.acquire() as connection:
            return await connection.fetchrow(
                "SELECT group_id, title, spreadsheet_id, sheet_url, is_active FROM groups WHERE group_id = $1",
                group_id
            )

    async def get_all_active(self):
        """All groups the bot currently believes it's still a member of.
        Used to check a user's membership against each one."""
        async with self._pool.acquire() as connection:
            return await connection.fetch(
                "SELECT group_id, title, spreadsheet_id, sheet_url FROM groups WHERE is_active = TRUE"
            )

    async def get_all_with_sheet(self):
        """Active groups that have a spreadsheet configured — the only ones
        the midnight export job needs to touch."""
        async with self._pool.acquire() as connection:
            return await connection.fetch("""
                SELECT group_id, title, spreadsheet_id, sheet_url
                FROM groups
                WHERE is_active = TRUE AND spreadsheet_id IS NOT NULL
                """)

    async def get_by_user(self, telegram_id: int):
        """The group a specific user is currently linked to, if any."""
        async with self._pool.acquire() as connection:
            return await connection.fetchrow("""
                SELECT g.group_id, g.title, g.spreadsheet_id, g.sheet_url
                FROM groups g
                JOIN users u ON u.group_id = g.group_id
                WHERE u.telegram_id = $1
                """, telegram_id)

    async def set_spreadsheet(self, group_id: int, spreadsheet_id: str, sheet_url: str):
        async with self._pool.acquire() as connection:
            await connection.execute(
                "UPDATE groups SET spreadsheet_id = $2, sheet_url = $3 WHERE group_id = $1",
                group_id, spreadsheet_id, sheet_url
            )

    async def deactivate(self, group_id: int):
        """Called when the bot is kicked or leaves the group — keeps the row
        (and its spreadsheet link) around in case it's re-added later, but
        stops it from being offered as a match or exported to."""
        async with self._pool.acquire() as connection:
            await connection.execute(
                "UPDATE groups SET is_active = FALSE WHERE group_id = $1",
                group_id
            )


class BookRepository(BaseRepository):
    async def add(self, title: str) -> int:
        """Inserts the book globally if it doesn't exist, returns its book_id either way."""
        async with self._pool.acquire() as connection:
            await connection.execute(
                "INSERT INTO books(title) VALUES ($1) ON CONFLICT (LOWER(title)) DO NOTHING",
                title
            )
            return await connection.fetchval(
                "SELECT book_id FROM books WHERE LOWER(title) = LOWER($1)",
                title
            )

    async def get(self):
        async with self._pool.acquire() as connection:
            return await connection.fetch("SELECT book_id, title FROM books ORDER BY title")

class UserBooksRepository(BaseRepository):
    async def add(self, user_id: int, book_id: int):
        """Links a user to a book. Safe to call even if already linked."""
        async with self._pool.acquire() as connection:
            await connection.execute(
                "INSERT INTO user_books(user_id, book_id) VALUES ($1, $2) ON CONFLICT (user_id, book_id) DO NOTHING",
                user_id, book_id
            )

    async def get(self, user_id: int):
        """Returns this user's currently active books."""
        async with self._pool.acquire() as connection:
            return await connection.fetch("""
                SELECT b.book_id, b.title
                FROM user_books ub
                JOIN books b ON ub.book_id = b.book_id
                WHERE ub.user_id = $1 AND ub.is_active = TRUE
                ORDER BY ub.added_at DESC
            """, user_id)

    async def finish(self, user_id: int, book_id: int):
        """Hides a book from the menu without deleting reading history."""
        async with self._pool.acquire() as connection:
            await connection.execute(
                "UPDATE user_books SET is_active = FALSE, finished_at = NOW() WHERE user_id = $1 AND book_id = $2",
                user_id, book_id
            )
    async def delete(self, user_id: int, book_id: int):
        """Removes the book from this user's list entirely.
        reading_logs has no FK back to user_books, so past history
        (and the Sheets export built from it) stays intact."""
        async with self._pool.acquire() as connection:
            await connection.execute(
                "DELETE FROM user_books WHERE user_id = $1 AND book_id = $2",
                user_id, book_id
            )

class LogRepository(BaseRepository):
    """
    Inherits from BaseRepository, managing reading_logs table
    """
    async def add(self, telegram_id: int, book_id: int, pages_read: int):
        local_date = datetime.datetime.now(ZoneInfo('Asia/Bishkek')).date()
        async with self._pool.acquire() as connection:
            await connection.execute("""
                INSERT INTO reading_logs(user_id, book_id, log_date, pages_read)
                VALUES ($1, $2, $3, $4)
                """, telegram_id, book_id, local_date, pages_read)

    async def get(self, telegram_id: int):
        async with self._pool.acquire() as connection:
            return await connection.fetch("""
                SELECT b.title, r.log_date, r.pages_read
                FROM reading_logs r
                JOIN books b ON r.book_id = b.book_id
                WHERE r.user_id = $1
                ORDER BY r.log_date DESC, r.logged_at DESC
                """, telegram_id)

class ReportRepository(BaseRepository):
    """
    This class takes all tables in ...
    """
    async def add(self):
        raise NotImplementedError("ReportRepository is read-only")
    async def get(self):
        async with self._pool.acquire() as connection:
            return await connection.fetch("""
                SELECT 
                    u.group_id,
                    CONCAT(u.user_name, ' ', u.user_surname) AS full_name,
                    b.title,
                    r.log_date,
                    SUM(r.pages_read) AS pages_read
                FROM users u
                INNER JOIN reading_logs r ON u.telegram_id = r.user_id
                INNER JOIN books b ON r.book_id = b.book_id
                GROUP BY u.group_id, CONCAT(u.user_name, ' ', u.user_surname), b.title, r.log_date
                ORDER BY r.log_date
                """)

    async def get_for_group(self, group_id: int):
        """Same shape as get(), scoped to a single group's users. Used by the
        midnight export so each group's spreadsheet only shows its own data."""
        async with self._pool.acquire() as connection:
            return await connection.fetch("""
                SELECT
                    u.group_id,
                    CONCAT(u.user_name, ' ', u.user_surname) AS full_name,
                    b.title,
                    r.log_date,
                    SUM(r.pages_read) AS pages_read
                FROM users u
                INNER JOIN reading_logs r ON u.telegram_id = r.user_id
                INNER JOIN books b ON r.book_id = b.book_id
                WHERE u.group_id = $1
                GROUP BY u.group_id, CONCAT(u.user_name, ' ', u.user_surname), b.title, r.log_date
                ORDER BY r.log_date
                """, group_id)

class DatabaseManager:
    def __init__(self):
        self.pool = None

        #Initializing repositories
        self.users: UserRepository | None = None
        self.logs: LogRepository | None = None
        self.migration: ReportRepository | None = None
        self.books: BookRepository | None = None
        self.user_books: UserBooksRepository | None = None
        self.groups: GroupRepository | None = None

    async def connect(self, db_url: str):
        self.pool = await asyncpg.create_pool(db_url)

        self.users = UserRepository(self.pool)
        self.logs = LogRepository(self.pool)
        self.migration = ReportRepository(self.pool)
        self.books = BookRepository(self.pool)
        self.user_books = UserBooksRepository(self.pool)
        self.groups = GroupRepository(self.pool)

    
    async def create_table(self):
        async with self.pool.acquire() as connection:
            # groups must exist before users, since users.group_id references it
            await connection.execute("""
                CREATE TABLE IF NOT EXISTS groups (
                    group_id BIGINT PRIMARY KEY,
                    title TEXT,
                    spreadsheet_id TEXT,
                    sheet_url TEXT,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    added_at TIMESTAMP DEFAULT NOW()
                )
            """)
            await connection.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    telegram_id BIGINT PRIMARY KEY,
                    user_name TEXT NOT NULL,
                    user_surname TEXT NOT NULL,
                    group_id BIGINT REFERENCES groups(group_id),
                    joined_at TIMESTAMP DEFAULT NOW()
                ) 
            """)
            # Backfill for deployments where users already existed before
            # group_id was introduced.
            await connection.execute(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS group_id BIGINT REFERENCES groups(group_id)"
            )
            await connection.execute("""
                CREATE TABLE IF NOT EXISTS books (
                    book_id SERIAL PRIMARY KEY,
                    title TEXT NOT NULL
                )
            """)
            await connection.execute("""
                CREATE TABLE IF NOT EXISTS user_books (
                    user_id BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
                    book_id INTEGER NOT NULL REFERENCES books(book_id) ON DELETE CASCADE,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    added_at TIMESTAMP DEFAULT NOW(),
                    finished_at TIMESTAMP,
                    PRIMARY KEY(user_id, book_id)
                )
            """)
            await connection.execute("""
                CREATE TABLE IF NOT EXISTS reading_logs (
                    log_id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
                    book_id INTEGER NOT NULL REFERENCES books(book_id) ON DELETE CASCADE,
                    pages_read INTEGER NOT NULL CHECK (pages_read > 0),
                    log_date DATE NOT NULL DEFAULT CURRENT_DATE,
                    logged_at TIMESTAMP DEFAULT NOW()
                )
            """)
            await connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_books_title_lower ON books(LOWER(title))")
            await connection.execute("CREATE INDEX IF NOT EXISTS idx_logs_user_date ON reading_logs(user_id, log_date)")
            await connection.execute("CREATE INDEX IF NOT EXISTS idx_logs_date ON reading_logs(log_date)")
            await connection.execute("CREATE INDEX IF NOT EXISTS idx_logs_book_date ON reading_logs(book_id, log_date)")