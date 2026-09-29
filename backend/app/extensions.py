import sqlite3
from typing import Any

from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from sqlalchemy.engine import Engine

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
)


@event.listens_for(Engine, "connect")
def enable_sqlite_foreign_keys(
    database_connection: Any,
    _connection_record: Any,
) -> None:
    if not isinstance(database_connection, sqlite3.Connection):
        return

    cursor = database_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
    finally:
        cursor.close()
