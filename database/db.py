import asyncpg

class DatabaseManager:
    def __init__(self):
        self.pool = None
    
    async def connect(self, db_url: str):
        self.pool = await asyncpg.create_pool(db_url)

    async def create_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS reading_logs (
            telegram_id BIGINT,
            user_name VARCHAR(255),
            log_date DATE DEFAULT CURRENT_DATE,
            pages_read INTEGER,
            PRIMARY KEY (telegram_id, log_date)
        );
            """
        async with self.pool.acquire() as connection:
            await connection.execute(query)

    async def add_log(self, telegram_id: int, user_name : str, pages_read : int):
        query = """
        INSERT INTO reading_logs(telegram_id, user_name, pages_read)
        VALUES ($1, $2, $3)
        ON CONFLICT (telegram_id, log_date)
        DO UPDATE SET pages_read = reading_logs.pages_read + EXCLUDED.pages_read"""
        
        async with self.pool.acquire() as connection:
            await connection.execute(query, telegram_id, user_name, pages_read)
