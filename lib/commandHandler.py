import re

from enum import Enum
from dataclasses import dataclass
from .database import Database

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


class CommandHandler:
    def __init__(self, db: Database, processed_users):
        self.db = db
        self.processed_users = processed_users

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
        if not self.processed_users.get(username):
            user_data = await self.db.fetchUserByLogin(username)
            if user_data:
                process_user = User(user_data[0], user_data[1], user_data[2], user_data[3])
                client_connection.user = process_user
                self.processed_users[username] = process_user
                client_connection.state = ConnectionState.AWAITING_PASSWORD
                return f'You may proceed. Enter the password for {username}'
            else:
                raise CommandException('Error: No such login')
        else:
            client_connection.user = self.processed_users[username]
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
    
        await self.db.updateUserBalance(user.balance, user.id)
        await self.db.insertCalculationHistory(user.id, args, result)

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
