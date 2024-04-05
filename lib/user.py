from enum import Enum
from dataclasses import dataclass

class Role(Enum):
    ADMIN = 1
    USER = 2


@dataclass
class User:
 id: int
 login: str
 password_hash: str
 balance: int
 role: Role
 connections: list = []