import asyncpg

class Database:
    def __init__(self, config):
        self.config = config
        self.pool = None

    async def createPool(self):
        self.pool = await asyncpg.create_pool(**self.config['DATABASE'])

    async def execute(self, query, *args):
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def fetch(self, query, *args):
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query, *args):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)
