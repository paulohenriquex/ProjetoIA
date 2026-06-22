import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Python mínimo exigido: 3.11 (pydantic-core não tem wheel pra 3.14+)
if sys.version_info < (3, 11):
    raise RuntimeError("Python 3.11 ou superior é necessário")
if sys.version_info >= (3, 14):
    print("⚠️  Python 3.14 detectado. Use Python 3.11-3.13 para evitar erros de compilação.")

env_path = Path(__file__).resolve().parents[2] / ".env"
if not env_path.exists():
    raise RuntimeError(
        f"Arquivo .env não encontrado em {env_path}. "
        "Copie .env.example para .env e preencha as variáveis."
    )
load_dotenv(env_path)

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

if not MYSQL_PASSWORD:
    raise RuntimeError("MYSQL_PASSWORD não configurada no .env")

DATABASE_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
