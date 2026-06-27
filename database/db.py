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
    async def add(self, telegram_id: int, user_name: str, user_surname: str):
        query="""
        INSERT INTO users (telegram_id, user_name, user_surname) VALUES ($1, $2, $3)
        """
        async with self._pool.acquire() as connection:
            await connection.execute(query, telegram_id, user_name, user_surname)
    async def get(self, telegram_id:int):
        query = """
        SELECT telegram_id FROM users WHERE telegram_id=$1"""
        async with self._pool.acquire() as connection:
            fetchedval = await connection.fetchval(query, telegram_id)

        return fetchedval

class BookRepository(BaseRepository):
    async def add(self, title: str) -> int:
        """Inserts the book globally if it doesn't exist, returns its book_id either way."""
        async with self._pool.acquire() as connection:
            await connection.execute(
                "INSERT INTO books(title) VALUES ($1) ON CONFLICT ((LOWER(title))) DO NOTHING",
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
                                            CONCAT(u.user_name, ' ', u.user_surname) AS full_name,
                                            b.title,
                                            r.log_date,
                                            SUM(r.pages_read) AS pages_read
                                          FROM users u
                                          INNER JOIN reading_logs r ON u.telegram_id = r.user_id
                                          INNER JOIN books b ON r.book_id = b.book_id
                                          GROUP BY full_name, b.title, r.log_date
                                          ORDER BY r.log_date
                                          """)

class DatabaseManager:
    def __init__(self):
        self.pool = None

        #Initializing repositories
        self.users: UserRepository | None = None
        self.logs: LogRepository | None = None
        self.migration: ReportRepository | None = None
        self.books: BookRepository | None = None
        self.user_books: UserBooksRepository | None = None

    async def connect(self, db_url: str):
        self.pool = await asyncpg.create_pool(db_url)

        self.users = UserRepository(self.pool)
        self.logs = LogRepository(self.pool)
        self.migration = ReportRepository(self.pool)
        self.books = BookRepository(self.pool)
        self.user_books = UserBooksRepository(self.pool)

    
    async def create_table(self):
        async with self.pool.acquire() as connection:
            await connection.execute("""
                CREATE TABLE IF NOT EXISTS users (
                               telegram_id BIGINT PRIMARY KEY,
                               user_name TEXT NOT NULL,
                               user_surname TEXT NOT NULL,
                               joined_at TIMESTAMP DEFAULT NOW()
                               ) 
                               """)
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
            await connection.execute("CREATE INDEX IF NOT EXISTS idx_logs_user_date ON reading_logs(user_id, log_date)")
            await connection.execute("CREATE INDEX IF NOT EXISTS idx_logs_date ON reading_logs(log_date)")
            await connection.execute("CREATE INDEX IF NOT EXISTS idx_logs_book_date ON reading_logs(book_id, log_date)")
