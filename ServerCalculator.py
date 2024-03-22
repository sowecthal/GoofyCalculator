import socket
import re
import threading
import toml
import psycopg2

class CommandHandler:
    def __init__(self, config):
        self.config = config
        self.connection = psycopg2.connect(
            dbname=self.config['DATABASE']['postgres_db'],
            user=self.config['DATABASE']['postgres_user'],
            password=self.config['DATABASE']['postgres_password'],
            host=self.config['SERVER']['host'],
            port=self.config['SERVER']['port']
        )
        self.cursor = self.connection.cursor()
        self.active_sessions = {} 

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
        query = 'SELECT * FROM users WHERE login = %s'
        self.cursor.execute(query, (username,))
        user = self.cursor.fetchone()
        if user:
            self.active_sessions[username] = True  
            return f'Enter password for user "{username}"'
        else:
            return 'Error: User not found'

    def handleLogout(self, _):
        if not self.active_sessions:
            return 'Error: No active login session'
        
        username = next(iter(self.active_sessions))
        del self.active_sessions[username]
        return f'User "{username}" logged out successfully'

    def handlePassword(self, args):
        if not args:
            return 'Error: Missing password'
        if not self.active_sessions:
            return 'Error: No active login session'
        
        username = next(iter(self.active_sessions))
        password = args.strip()
        query = 'SELECT pass_hash FROM users WHERE login = %s'
        self.cursor.execute(query, (username,))
        correct_password_hash = self.cursor.fetchone()[0]
        if correct_password_hash == password:
            return f'User "{username}" successfully authenticated'
        else:
            return 'Error: Incorrect password'

    def handleCalc(self, args):
        if not self.active_sessions:
            return 'Error: No active login session'

        username = next(iter(self.active_sessions))
        query = "SELECT balance FROM users WHERE login = %s"
        self.cursor.execute(query, (username,))
        user_balance = self.cursor.fetchone()[0]

        if user_balance <= 0:
            return 'Error: Insufficient balance'

        try:
            result = eval(args)
        except Exception as e:
            return f'Error: Invalid expression: {str(e)}'

        new_balance = user_balance - 1
        update_query = "UPDATE users SET balance = %s WHERE login = %s"
        self.cursor.execute(update_query, (new_balance, username))
        
        user_id_query = "SELECT id FROM users WHERE login = %s"
        self.cursor.execute(user_id_query, (username,))
        user_id = self.cursor.fetchone()[0]

        log_query = 'INSERT INTO calc_history (user_id, expression, result) VALUES (%s, %s, %s)'
        self.cursor.execute(log_query, (user_id, args, result))

        self.connection.commit()
        return str(result)

def handleClient(client_socket, command_handler):
    while True:
        try:
            request = client_socket.recv(1024).decode('ascii')
            response = command_handler.handleCommand(request)
            client_socket.send(response.encode('ascii'))
        except Exception as e:
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

            client_thread = threading.Thread(target=handleClient, args=(client_socket, command_handler))
            client_thread.start()
    except KeyboardInterrupt:
        print('Server stopped.')

if __name__ == '__main__':
    main()
