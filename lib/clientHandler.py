import logging

from .commandHandler import CommandException, CommandHandler, ConnectionState

class ClientConnection:
    def __init__(self, address):
        self.address = f'{address[0]}:{address[1]}'
        logging.info(f'New connection from {self.address}')
        self.user = None
        self.state = ConnectionState.AWAITING_LOGIN

async def handleClient(reader, writer, command_handler: CommandHandler):
    client_connection = ClientConnection(reader._transport.get_extra_info('peername'))
    try:
        while True:
            try:
                request = (await reader.read(1024)).decode('ascii')
                response = await command_handler.handleCommand(request, client_connection)

                writer.write(response.encode('ascii'))
                await writer.drain()
            except CommandException as e:
                writer.write(str(e).encode('ascii'))
                await writer.drain()
            except Exception as e:
                logging.error(f'An error occurred: {str(e)}')  
                writer.write('An error occurred. Please try again'.encode('ascii'))
                await writer.drain()
    except ConnectionAbortedError as e:
            logging.info(f'Client {client_connection.address} disconnected')
