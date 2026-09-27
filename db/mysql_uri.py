import os
from urllib.parse import quote_plus

def build_mysql_uri(driver: str = "mysql+pymysql") -> str:
  """Builds the SQLAlchemy connection URI for the app's MySQL database from environment variables
  (loaded from .env by the caller): DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT (default "3306"),
  DB_SOCKET (default ""). If DB_SOCKET is set, connects via the socket regardless of DB_PORT."""
  host = os.environ.get("DB_HOST", "127.0.0.1")
  name = os.environ.get("DB_NAME", "")
  user = quote_plus(os.environ.get("DB_USER", ""))
  password = quote_plus(os.environ.get("DB_PASSWORD", ""))
  port = os.environ.get("DB_PORT", "3306")
  socket = os.environ.get("DB_SOCKET", "")
  if socket:
    return f"{driver}://{user}:{password}@/{name}?unix_socket={socket}&charset=utf8mb4"
  return f"{driver}://{user}:{password}@{host}:{port}/{name}?charset=utf8mb4"
