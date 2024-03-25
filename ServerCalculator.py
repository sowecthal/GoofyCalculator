import socket
import re
import threading
import toml
import psycopg2

from enum import Enum
from dataclasses import dataclass

class ConnectionState(Enum):
    AWAITING_LOGIN = 1
    AWAITING_PASSWORD = 2
    AUTHENTICATED = 3

@dataclass
class User:
 login: str
 password_hash: str
 balance: int

class ClientConnection:
    def __init__(self, socket):
        self.socket = socket
        self.user = None
        self.state = ConnectionState.AWAITING_LOGIN

class CommandHandler:
    def __init__(self, config):
        self.config = config
        self.connection = psycopg2.connect(**config['DATABASE'])
        self.cursor = self.connection.cursor()

        self.command_functions = {
            'login': self.handleLogin,
            'logout': self.handleLogout,
            'password': self.handlePassword,
            'calc': self.handleCalc
        }

    def handleCommand(self, command, client_connection):
        action, args = self.parseCommand(command)
        if not action:
            raise Exception('Error: Invalid command syntax')

        func = self.command_functions.get(action)
        if not func:
            raise Exception('Error: Invalid command')

        return func(args, client_connection)

    def parseCommand(self, command):
        match = re.match(r'([a-zA-Z]+)\s*(\S+)?', command)
        if match:
            return match.groups()
        return None, None
    
    def handleLogin(self, args, client_connection):
        if not args:
            raise Exception('Error: Missing username')
        
        if client_connection.state != ConnectionState.AWAITING_LOGIN:
            raise Exception('Error: Awaiting for login')
        
        username = args.strip()

        if not processed_users.get(username):
            self.cursor.execute('SELECT login, pass_hash, balance FROM users WHERE login = %s', (username,))
            user_data = self.cursor.fetchone()
            if user_data:
                process_user = User(username, user_data[1], user_data[2])
                client_connection.user = process_user
                processed_users[username] = process_user
                client_connection.state = ConnectionState.AWAITING_PASSWORD

                return f'You may proceed. Enter the password for {username}'
            else:
                raise Exception ('Error: No such login')
        else:
            client_connection.user = processed_users[username]
            client_connection.state = ConnectionState.AWAITING_PASSWORD

            return f'You may proceed. Enter the password for {username}. You have another session'

    def handlePassword(self, args, client_connection):
        if not args:
            raise Exception('Error: Missing password')
        
        if client_connection.state != ConnectionState.AWAITING_PASSWORD:
            raise Exception('Error: Awaiting for password')
        
        password = args.strip()
        username = client_connection.user.login
        correct_password_hash = client_connection.user.password_hash
        
        if correct_password_hash == password:
            client_connection.state = ConnectionState.AUTHENTICATED
            return f'User "{username}" successfully authenticated'
        else:
            raise Exception('Error: Incorrect password')

    def handleLogout(self, _, client_connection):
        if client_connection.state != ConnectionState.AUTHENTICATED:
            raise Exception('Error: No active login session to log out off')
        
        username = client_connection.user.login

        client_connection.user = None
        client_connection.state = ConnectionState.AWAITING_LOGIN

        return f'User "{username}" logged out successfully'
    
    def handleCalc(self, args, client_connection):
        if client_connection.state != ConnectionState.AUTHENTICATED:
            raise Exception('Error: No active login session')

        username = client_connection.user.login

        user_balance = client_connection.user.balance

        if user_balance <= 0:
            raise Exception('Error: Insufficient balance')
        try:
            result = eval(args)
        except Exception as e:
            raise Exception(f'Error: Invalid expression: {str(e)}')

        self.cursor.execute('UPDATE users SET balance = %s WHERE login = %s', (user_balance - 1, username))

        self.cursor.execute('SELECT id FROM users WHERE login = %s', (username,))
        user_id = self.cursor.fetchone()[0]

        self.cursor.execute('INSERT INTO calc_history (user_id, expression, result) VALUES (%s, %s, %s)', (user_id, args, result))

        self.connection.commit()
        return str(result)

def handleClient(client_socket, command_handler, client_connection):
    while True:
        try:
            request = client_socket.recv(1024).decode('ascii')
            response = command_handler.handleCommand(request, client_connection)
            client_socket.send(response.encode('ascii'))
        except Exception as e:
            client_socket.send(str(e).encode('ascii'))
            client_socket.close()
            break   

def main():
    config = toml.load('ConfigServerCalculator.toml')
    command_handler = CommandHandler(config)

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # AF_INET = ipv4 & SOCK_STREAM = TCP
    server.bind((config['SERVER']['host'], config['SERVER']['port']))
    server.listen()
    print(f'Server started. Listening on port {config["SERVER"]["port"]}...')

    try:
        while True:
            client_socket, client_address = server.accept()
            print(f'Client connected with {str(client_address)}')

            client_connection = ClientConnection(client_socket)
                
            client_thread = threading.Thread(target=handleClient, args=(client_socket, command_handler, client_connection))
            client_thread.start()
    except KeyboardInterrupt:
        print('Server stopped.')

if __name__ == '__main__':  
    processed_users = {}
    main()
