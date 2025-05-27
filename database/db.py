# Работа с PostgreSQL через asyncpg
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")

class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME
        )

    async def disconnect(self):
        if self.pool:
            await self.pool.close()

    async def execute(self, query, *args, fetch=False, fetchval=False, fetchrow=False, execute=False):
        async with self.pool.acquire() as connection:
            if fetch:
                return await connection.fetch(query, *args)
            elif fetchval:
                return await connection.fetchval(query, *args)
            elif fetchrow:
                return await connection.fetchrow(query, *args)
            elif execute:
                return await connection.execute(query, *args)

# Глобальный объект базы данных
db = Database()
