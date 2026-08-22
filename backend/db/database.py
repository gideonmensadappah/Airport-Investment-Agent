import sqlite3
from pathlib import Path

DATABASE_FILE = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "airport_data.db"
)


def get_connection(database_file: Path = DATABASE_FILE) -> sqlite3.Connection:
    connection = sqlite3.connect(database_file)
    connection.row_factory = sqlite3.Row
    return connection
