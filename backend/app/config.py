import os
from pathlib import Path

from dotenv import load_dotenv

# Carrega o .env da raiz do projeto (onde está o backend)
env_path = Path(__file__).resolve().parents[1] / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    # Fallback: tenta na raiz do projeto
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if env_path.exists():
        load_dotenv(env_path)

print(f"📁 Carregando .env de: {env_path}")  # Debug

API_KEY = os.environ.get("GEMINI_API_KEY")
MODELO = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite")
MAX_CV_CHARS = int(os.environ.get("MAX_CV_CHARS", "4000"))
MAX_PDF_PAGES = int(os.environ.get("MAX_PDF_PAGES", "3"))
PORT = int(os.environ.get("BACKEND_PORT", "8080"))

MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.environ.get("MYSQL_PORT", "3306"))
MYSQL_USER = os.environ.get("MYSQL_USER", "root")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE", "triagem_db")

DATABASE_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
