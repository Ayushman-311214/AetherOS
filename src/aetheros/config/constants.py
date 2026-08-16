from pathlib import Path

PROJECT_NAME = "AetherOS"
VERSION = "0.1.0"

ROOT_DIR = Path(__file__).resolve().parent.parent

LOG_DIR = ROOT_DIR / "logs"
CACHE_DIR = ROOT_DIR / ".cache"
DATA_DIR = ROOT_DIR / "data"

DEFAULT_PROVIDER = "ollama"
DEFAULT_MODEL = "qwen3:8b"

APP_AUTHOR = "Ayush"

LOG_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)