import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

API_KEY = os.environ.get("GEMINI_API_KEY")
MODELO = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite")
MAX_CV_CHARS = int(os.environ.get("MAX_CV_CHARS", "4000"))
MAX_PDF_PAGES = int(os.environ.get("MAX_PDF_PAGES", "3"))
PORT = int(os.environ.get("BACKEND_PORT", "8080"))
