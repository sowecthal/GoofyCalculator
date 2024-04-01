import re
import toml
import asyncio
import asyncpg
import logging

from enum import Enum
from dataclasses import dataclass

class CommandException(Exception):
    pass

class ConnectionState(Enum):
    AWAITING_LOGIN = 1
    AWAITING_PASSWORD = 2
    AUTHENTICATED = 3

@dataclass
class User:
 id: int
 login: str
 password_hash: str
 balance: int

class ClientConnection:
    def __init__(self, address):
        self.address = f'{address[0]}:{address[1]}'
        logging.info(f'New connection from {self.address}')
        self.user = None
        self.state = ConnectionState.AWAITING_LOGIN

class CommandHandler:
    def __init__(self, config):
        self.config = config
        self.pool = None

    async def handleCommand(self, command, client_connection):
        action, args = await self.parseCommand(command)
        if not action:
            raise CommandException('Error: Invalid command syntax')
        func = getattr(self, f'handle{action.capitalize()}')
        if not func:
            raise CommandException('Error: Invalid command')
        return await func(args, client_connection)

    async def parseCommand(self, command):
        match = re.match(r'([a-zA-Z]+)\s*(\S+)?', command)
        if match:
            return match.groups()
        return None, None
    
    async def handleLogin(self, args, client_connection):
        if not args:
            raise CommandException('Error: Missing username')

        if client_connection.state != ConnectionState.AWAITING_LOGIN:
            raise CommandException('Error: Not currently awaiting for login')
        
        username = args.strip()
        if not processed_users.get(username):
            async with self.pool.acquire() as conn:
                user_data = await conn.fetchrow('SELECT id, login, pass_hash, balance FROM users WHERE login = $1', username)
            if user_data:
                process_user = User(user_data[0], user_data[1], user_data[2], user_data[3])
                client_connection.user = process_user
                processed_users[username] = process_user
                client_connection.state = ConnectionState.AWAITING_PASSWORD
                return f'You may proceed. Enter the password for {username}'
            else:
                raise CommandException('Error: No such login')
        else:
            client_connection.user = processed_users[username]
            client_connection.state = ConnectionState.AWAITING_PASSWORD
            return f'You may proceed. Enter the password for {username}. You have another session'

    async def handlePassword(self, args, client_connection):
        if not args:
            raise CommandException('Error: Missing password')
        
        if client_connection.state != ConnectionState.AWAITING_PASSWORD:
            raise CommandException('Error: Not currently awaiting for password')
        
        password = args.strip()
        username = client_connection.user.login
        correct_password_hash = client_connection.user.password_hash
        if correct_password_hash == password:
            client_connection.state = ConnectionState.AUTHENTICATED
            return f'User "{username}" successfully authenticated'
        else:
            raise CommandException('Error: Incorrect password')
    
    async def handleCalc(self, args, client_connection):
        if client_connection.state != ConnectionState.AUTHENTICATED:
            raise CommandException('Error: No active login session')

        user = client_connection.user

        if client_connection.user.balance <= 0:
            raise CommandException('Error: Insufficient balance')
        try:
            client_connection.user.balance -= 1
            result = eval(args)
        except Exception as e:
            client_connection.user.balance += 1
            raise CommandException(f'Error: Invalid expression: {str(e)}')
    
        async with self.pool.acquire() as conn:
            await conn.execute(f"UPDATE users SET balance = {user.balance} WHERE id = {user.id}")
            await conn.execute(f"INSERT INTO calc_history (user_id, expression, result) VALUES ({user.id}, '{args}', {result})")

        return str(result)
    
    async def handleBalance(self, _, client_connection):
        if client_connection.state != ConnectionState.AUTHENTICATED:
            raise CommandException('Error: No active login session')
        return str(client_connection.user.balance)
    
    async def handleLogout(self, _, client_connection):
        if client_connection.state != ConnectionState.AUTHENTICATED:
            raise CommandException('Error: No active login session to log out off')
        username = client_connection.user.login
        client_connection.user = None
        client_connection.state = ConnectionState.AWAITING_LOGIN
        return f'User "{username}" logged out successfully'

        
async def handleClient(reader, writer, command_handler):
    client_connection = ClientConnection(reader._transport.get_extra_info('peername'))
    try:
        while True:
            try:
                request = (await reader.read(1024)).decode('ascii')
                response = await command_handler.handleCommand(request, client_connection)

                writer.write(response.encode('ascii'))
                await writer.drain()
            except CommandException as e:
                logging.error(str(e))
                writer.write(str(e).encode('ascii'))
                await writer.drain()
            except Exception as e:
                logging.error(f'An error occurred: {str(e)}')  
                writer.write('An error occurred. Please try again'.encode('ascii'))
                await writer.drain()
    except ConnectionAbortedError as e:
            logging.info(f'Client {client_connection.address} disconnected')

async def main():
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(name)s] [%(levelname)s] > %(message)s')
    config = toml.load('ConfigServerCalculator.toml')
    command_handler = CommandHandler(config)
    command_handler.pool = await asyncpg.create_pool(**config['DATABASE'])
    logging.info(f'Server started. Listening on port {config["SERVER"]["port"]}...')
    
    try:
        server = await asyncio.start_server(lambda r, w: handleClient(r, w, command_handler), config['SERVER']['host'], config['SERVER']['port'])
        await server.serve_forever()
    except KeyboardInterrupt:
        logging.info('Server shutting down...')
        server.close()
        await server.wait_closed()

if __name__ == '__main__':
    processed_users = {}
    asyncio.run(main())