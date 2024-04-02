import asyncpg

class Database:
    def __init__(self, config):
        self.config = config
        self.pool = None

    async def createPool(self):
        self.pool = await asyncpg.create_pool(**self.config['DATABASE'])

    async def fetchUserByLogin(self, login):
        query = "SELECT id, login, pass_hash, balance FROM users WHERE login = $1"
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, login)

    async def updateUserBalance(self, user_id, new_balance):
        query = "UPDATE users SET balance = $1 WHERE id = $2"
        async with self.pool.acquire() as conn:
            await conn.execute(query, new_balance, user_id)

    async def insertCalculationHistory(self, user_id, expression, result):
        query = "INSERT INTO calc_history (user_id, expression, result) VALUES ($1, $2, $3)"
        async with self.pool.acquire() as conn:
            await conn.execute(query, user_id, expression, result)
