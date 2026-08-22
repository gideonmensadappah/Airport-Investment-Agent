import sqlite3
from pathlib import Path
from urllib.parse import quote

DATABASE_FILE = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "airport_data.db"
)


def get_connection(database_file: Path = DATABASE_FILE) -> sqlite3.Connection:
    resolved_path = database_file.resolve().as_posix()
    database_uri = f"file:{quote(resolved_path, safe='/:')}?mode=ro&immutable=1"
    connection = sqlite3.connect(database_uri, uri=True)
    connection.row_factory = sqlite3.Row
    return connection
