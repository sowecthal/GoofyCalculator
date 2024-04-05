import logging

from enum import Enum

class ConnectionState(Enum):
    AWAITING_LOGIN = 1
    AWAITING_PASSWORD = 2
    AUTHENTICATED = 3


class ClientConnection:
    def __init__(self, address):
        self.address = f'{address[0]}:{address[1]}'
        logging.info(f'New connection from {self.address}')
        self.user = None
        self.state = ConnectionState.AWAITING_LOGIN
