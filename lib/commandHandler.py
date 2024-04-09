import re
import hashlib
import logging

from .database import Database
from .connection import ConnectionState
from .user import User, Role

class CommandException(Exception):
    pass


class CommandHandler:
    def __init__(self, db: Database, processed_users):
        self.db = db
        self.processed_users = processed_users

    async def handleCommand(self, command, client_connection):
        action, args_str = await self.parseCommand(command)
        args = args_str.split() if args_str else []
        
        if not action:
            raise CommandException('Error: Invalid command syntax')
        func = getattr(self, f'handle{action.capitalize()}', None)
        if not func:
            raise CommandException('Error: Invalid command')
        return await func(args, client_connection)

    async def parseCommand(self, command):
        match = re.match(r'([a-zA-Z]+)\s*(.*)', command)

        if match:
            return match.groups()
        return None, None

    async def handleRegister(self, args, client_connection):
        if client_connection.user.role != Role.ADMIN.name:
            raise CommandException("Error: You don't have permission to register users")
        if len(args) != 2:
            raise CommandException("Error: Invalid number of arguments. Usage: register <USERNAME> <PASSWORD>")

        username, password = args
        password_hash = hashlib.md5(password.encode()).hexdigest()

        if await self.db.fetchUserByLogin(username):
            raise CommandException("Error: Username already exists")

        await self.db.insertNewUser(username, password_hash)

        return f'User "{username}" registered successfully.'

    async def handleLogin(self, args, client_connection):
        if client_connection.state != ConnectionState.AWAITING_LOGIN:
            raise CommandException('Error: Not currently awaiting for login')
        if len(args) != 1:
            raise CommandException('Error: Invalid number of arguments. Usage: login <USERNAME>')

        username = args[0]
        
        if not self.processed_users.get(username):
            logging.debug(f'User \'{username}\' was taken from database')
            user_data = await self.db.fetchUserByLogin(username)
            if user_data:
                process_user = User(user_data[0], user_data[1], user_data[2], user_data[3], user_data[4], [client_connection,])
                client_connection.user = process_user
                self.processed_users[username] = process_user
                client_connection.state = ConnectionState.AWAITING_PASSWORD
                return f'You may proceed. Enter the password for {username}'
            else:
                raise CommandException('Error: No such login')
        else:
            logging.debug(f'User \'{username}\' was taken from cache')
            client_connection.user = self.processed_users[username]

            self.processed_users[username].connections.append(client_connection)

            client_connection.state = ConnectionState.AWAITING_PASSWORD
            return f'You may proceed. Enter the password for {username}'

    async def handlePassword(self, args, client_connection):
        if client_connection.state != ConnectionState.AWAITING_PASSWORD:
            raise CommandException('Error: Not currently awaiting for password')
        if len(args) != 1:
            raise CommandException('Error: Invalid number of arguments. Usage: password <PASSWORD>')

        password = args[0]
        username = client_connection.user.login

        password_hash = hashlib.md5(password.encode()).hexdigest()
        correct_password_hash = client_connection.user.password_hash

        if correct_password_hash == password_hash:
            client_connection.state = ConnectionState.AUTHENTICATED
            return f'User "{username}" successfully authenticated'
        else:
            raise CommandException('Error: Incorrect password')

    async def handleCalc(self, args, client_connection):
        if client_connection.state != ConnectionState.AUTHENTICATED:
            raise CommandException('Error: No active login session')
        if len(args) != 1:
            raise CommandException('Error: Invalid number of arguments. Usage: calc <EXPRESSION>')
        
        user = client_connection.user
        expression = args[0]

        if client_connection.user.balance <= 0:
            raise CommandException('Error: Insufficient balance')
        try:
            client_connection.user.balance -= 1
            result = eval(expression)
        except Exception as e:
            client_connection.user.balance += 1
            raise CommandException(f'Error: Invalid expression: {str(e)}')
    
        await self.db.updateUserBalance(user.id, user.balance)
        await self.db.insertCalculationHistory(user.id, expression, result)

        return str(result)
    
    async def handleBalance(self, args, client_connection):
        if client_connection.state != ConnectionState.AUTHENTICATED:
            raise CommandException('Error: No active login session')
        if args and client_connection.user.role != Role.ADMIN.name:
            raise CommandException('Error: You only have permission to check your own balance. Usage: balance')

        if args:
            if len(args) == 1:
                username = args[0]
                user_data = await self.db.fetchUserByLogin(username)
                if not user_data:
                    raise CommandException('Error: User not found')
                return str(user_data['balance'])
            elif len(args) == 3:
                username, mode, value = args
                user_data = await self.db.fetchUserByLogin(username)
                if not user_data:
                    raise CommandException('Error: User not found')
                if mode != 'set' and mode != 'add':
                    raise CommandException("Error: Invalid mode. Mode should be 'set' or 'add'")
                
                try:
                    value = int(value)
                except ValueError:
                    raise CommandException('Error: Value must be an integer')
                
                user_balance = user_data['balance']
                
                if mode == 'set':
                    user_balance = value
                elif mode == 'add':
                    user_balance += value

                await self.db.updateUserBalance(user_data['id'], user_balance)
                return f"Balance updated successfully for user '{username}'"

            else:
                raise CommandException('Error: Invalid number of arguments. Usage: balance <MODE> <VALUE>')
        return str(client_connection.user.balance)
       
    async def handleLogout(self, _, client_connection):
        if client_connection.state != ConnectionState.AUTHENTICATED:
            raise CommandException('Error: No active login session to log out off')
        
        username = client_connection.user.login
        client_connection.user.connections.remove(client_connection)
        client_connection.user = None

        client_connection.state = ConnectionState.AWAITING_LOGIN
        return f'User "{username}" logged out successfully'

    async def handleExit(self, _, client_connection):
        client_connection.user.connections.remove(client_connection)
        client_connection.user = None
        client_connection.state = ConnectionState.AWAITING_LOGIN

        if client_connection.state == ConnectionState.AUTHENTICATED:
            if client_connection.user and client_connection in client_connection.user.connections:
                client_connection.user.connections.remove(client_connection)
            if len(client_connection.user.connections) == 0:
                del self.processed_users[client_connection.user.login]
            logging.info(f'Client {client_connection.address} disconnected')
            del client_connection

        return f'Exited succesfully'