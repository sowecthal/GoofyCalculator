import socket
import re
import threading
import json

class User:
    def __init__(self, username, password_hash, balance):
        self.username = username
        self.password_hash = password_hash
        self.balance = balance

class CommandException(Exception):
    pass

class CommandHandler:
    def __init__(self):
        self.users = {}
        self.logged_in_users = {}  

        #временная заглушка, типа юзеры, типа хэш их паролей и баланс
        self.users['Polina'] = User('Polina', '888', 500)
        self.users['sowecthal'] = User('sowecthal', 'qwerty12345', 100)

        self.command_functions = {
            'login': self.handleLogin,
            'logout': self.handleLogout,
            'password': self.handlePassword,
            'calc': self.handleCalc
        }

    def handleCommand(self, command):
        action, args = self.parseCommand(command)
        if not action:
            return 'Error: Invalid command syntax'

        func = self.command_functions.get(action)
        if not func:
            return 'Error: Invalid command'

        return func(args)

    def parseCommand(self, command):
        match = re.match(r'([a-zA-Z]+)\s*(\S+)?', command)
        if match:
            return match.groups()
        return None, None

    def handleLogin(self, args):
        if not args:
            return 'Error: Missing username'
        
        username = args.strip()
        if username in self.users:
            self.logged_in_users[username] = True
            return f'Enter password for user "{username}"'
        else:
            return 'Error: User not found'

    def handleLogout(self, args):
        if not self.logged_in_users:
            return 'Error: No active login session'
        
        username = next(iter(self.logged_in_users))
        del self.logged_in_users[username]
        return f'User "{username}" logged out successfully'

    def handlePassword(self, args):
        if not args:
            return 'Error: Missing password'
        if not self.logged_in_users:
            return 'Error: No active login session'
        
        username = next(iter(self.logged_in_users))
        password = args.strip()
        if self.users[username].password_hash == password:
            return f'User "{username}" successfully authenticated'
        else:
            return 'Error: Incorrect password'

    def handleCalc(self, args):
        if not self.logged_in_users:
            return 'Error: No active login session'

        username = next(iter(self.logged_in_users))
        user = self.users[username]
        if user.balance <= 0:
            return 'Error: Insufficient balance'

        try:
            result = eval(args)
        except Exception as e:
            return f'Error: Invalid expression: {str(e)}'
        user.balance -= 1

        return (str(result) + str(user.balance))

def handleClient(client_socket, command_handler):
    while True:
        try:
            request = client_socket.recv(1024).decode('ascii')
            response = command_handler.handleCommand(request)
            client_socket.send(response.encode('ascii'))
        except CommandException as e:
            client_socket.close()
            break
        except Exception as e:

            client_socket.close()
            break

def main():
    command_handler = CommandHandler()

    #временно, потом уйдет в конфиг
    host = 'localhost'
    port = 8888

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # AF_INET = ipv4 & SOCK_STREAM = TCP
    server.bind((host, port)) 
    server.listen()
    print(f'Server started. Listening on port {port}...')

    try:
        while True:
            client_socket, client_address = server.accept()
            print(f'Client connected with {str(client_address)}')

            client_thread = threading.Thread(target=handleClient, args=(client_socket, command_handler))
            client_thread.start()
    except KeyboardInterrupt:
        print('Server stopped.')

if __name__ == '__main__':
    main()
