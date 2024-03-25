import socket

def main():
    host = 'localhost'
    port = 8888

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((host, port))

    try:
        while True:
            command = input('Enter your command: ')
            client_socket.send(command.encode('ascii'))

            response = client_socket.recv(1024).decode('ascii')
            print(response)
    except KeyboardInterrupt:
        print('Client stopped working')
        client_socket.close()

if __name__ == '__main__':
    main()
