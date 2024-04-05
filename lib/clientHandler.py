import logging
import asyncio

from .commandHandler import CommandException, CommandHandler
from . connection import ClientConnection

async def handleClient(reader, writer, command_handler: CommandHandler):
    client_connection = ClientConnection(reader._transport.get_extra_info('peername'))
    try:
        while not reader.at_eof():
            try:
                request = (await reader.read(1024)).decode('ascii')
                logging.debug(f'Requested "{request}" from {client_connection.address}')

                response = await command_handler.handleCommand(request, client_connection)
                await asyncio.sleep(10)
                writer.write(response.encode('ascii'))
                await writer.drain()
            except CommandException as e:
                logging.error(f'CommandException: {str(e)}. ConnectionState: {client_connection.state}. User info: {client_connection.user}')  
                writer.write(str(e).encode('ascii'))
                await writer.drain()
                #raise e
            except Exception as e:
                logging.error(f'An error occurred: {str(e)}')  
                writer.write('An error occurred. Please try again'.encode('ascii'))
                await writer.drain()
                #raise e
        else:
            raise ConnectionAbortedError()
    except ConnectionAbortedError as e:
            logging.info(f'Client {client_connection.address} disconnected')
