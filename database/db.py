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


class LogRepository(BaseRepository):
    """
    Inherits from BaseRepository, managing reading_logs table
    """
    async def add(self, telegram_id: int, pages_read: int):
        local_date = datetime.datetime.now(ZoneInfo('Asia/Bishkek')).date()
        query = """
        INSERT INTO reading_logs(telegram_id, log_date, pages_read)
        VALUES ($1, $2, $3)
        ON CONFLICT (telegram_id, log_date)
        DO UPDATE SET pages_read = reading_logs.pages_read + EXCLUDED.pages_read"""
        
        async with self._pool.acquire() as connection:
            await connection.execute(query, telegram_id,local_date, pages_read)
    async def get(self, telegram_id: int):
        query = """
        SELECT log_date, pages_read FROM reading_logs WHERE telegram_id = $1 ORDER BY log_date DESC"""
        async with self._pool.acquire() as connection:
            records = await connection.fetch(query, telegram_id)

        return records

class ReportRepository(BaseRepository):
    """
    This class takes all tables in ...
    """
    async def add(self):
        raise NotImplementedError("ReportRepository is read-only")
    async def get(self):
        query="""
        SELECT 
            CONCAT(users.user_name, ' ', users.user_surname) AS full_name,
            reading_logs.log_date,
            reading_logs.pages_read
        FROM users
        INNER JOIN reading_logs 
            ON users.telegram_id = reading_logs.telegram_id;
        """
        
        async with self._pool.acquire() as connection:
            merged = await connection.fetch(query)
        return merged

class DatabaseManager:
    def __init__(self):
        self.pool = None

        #Initializing repositories
        self.users: UserRepository | None = None
        self.logs: LogRepository | None = None
        self.migration: ReportRepository | None = None

    async def connect(self, db_url: str):
        self.pool = await asyncpg.create_pool(db_url)

        self.users = UserRepository(self.pool)
        self.logs = LogRepository(self.pool)
        self.migration = ReportRepository(self.pool)

    async def create_table(self):
        async with self._pool.acquire() as connection:
        # Create users table first (reading_logs references it via telegram_id)
            await connection.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    telegram_id BIGINT PRIMARY KEY,
                    user_name TEXT NOT NULL,
                    user_surname TEXT NOT NULL
                )
            """)
        # Create reading_logs table
            await connection.execute("""
                CREATE TABLE IF NOT EXISTS reading_logs (
                    telegram_id BIGINT,
                    log_date DATE NOT NULL,
                    pages_read INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (telegram_id, log_date)
                )
            """)