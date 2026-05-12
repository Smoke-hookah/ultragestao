import os
import sys
from pathlib import Path

from dotenv import load_dotenv


IS_FROZEN = getattr(sys, "frozen", False)

if IS_FROZEN:
    BASE_DIR = Path(sys._MEIPASS)
    RUNTIME_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).resolve().parent
    RUNTIME_DIR = BASE_DIR

CONFIG_DIR = Path(os.getenv("ULTRADANFE_CONFIG_DIR") or (RUNTIME_DIR / "config"))
OUTPUT_DIR = Path(os.getenv("ULTRADANFE_OUTPUT_DIR") or (RUNTIME_DIR / "output"))
LOGS_DIR = Path(os.getenv("ULTRADANFE_LOGS_DIR") or (RUNTIME_DIR / "logs"))


def _default_playwright_browsers_dir(runtime_dir: Path) -> Path:
    root_candidate = runtime_dir / "playwright-browsers"
    internal_candidate = runtime_dir / "_internal" / "playwright-browsers"
    if root_candidate.exists() or not internal_candidate.exists():
        return root_candidate
    return internal_candidate


PLAYWRIGHT_BROWSERS_DIR = Path(
    os.getenv("ULTRADANFE_PLAYWRIGHT_BROWSERS_DIR") or _default_playwright_browsers_dir(RUNTIME_DIR)
)


def _load_env_file() -> None:
    """Load .env from the runtime directory first."""
    candidates: list[Path] = [RUNTIME_DIR / ".env"]

    if not IS_FROZEN:
        project_env = BASE_DIR / ".env"
        if project_env != candidates[0]:
            candidates.append(project_env)

    for candidate in candidates:
        if candidate.exists():
            load_dotenv(candidate)
            break


def _parse_api_keys(value: str) -> list[str]:
    if not value:
        return []
    parts = [p.strip() for p in value.replace(";", ",").split(",")]
    return [p for p in parts if p]


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "f", "no", "n", "off"}:
        return False
    return default


_load_env_file()

CONFIG_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

if PLAYWRIGHT_BROWSERS_DIR.exists():
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(PLAYWRIGHT_BROWSERS_DIR))


API_URL = os.getenv("API_URL", "https://api.meudanfe.com.br/v2")
API_KEY = os.getenv("API_KEY", "")

API_KEYS = _parse_api_keys(os.getenv("API_KEYS", ""))
if not API_KEYS and API_KEY:
    API_KEYS = [API_KEY]


DELAY_BETWEEN_REQUESTS = float(os.getenv("DELAY_BETWEEN_REQUESTS", "1.5"))
MAX_REQUESTS_PER_SECOND = float(os.getenv("MAX_REQUESTS_PER_SECOND", "1"))
REQUEST_TIMEOUT = 30

PUT_DELAY_BETWEEN_REQUESTS = float(
    os.getenv("PUT_DELAY_BETWEEN_REQUESTS", str(DELAY_BETWEEN_REQUESTS))
)
PUT_MAX_REQUESTS_PER_SECOND = float(
    os.getenv("PUT_MAX_REQUESTS_PER_SECOND", str(MAX_REQUESTS_PER_SECOND))
)

GET_DELAY_BETWEEN_REQUESTS = float(
    os.getenv("GET_DELAY_BETWEEN_REQUESTS", str(DELAY_BETWEEN_REQUESTS))
)
GET_MAX_REQUESTS_PER_SECOND = float(
    os.getenv("GET_MAX_REQUESTS_PER_SECOND", str(MAX_REQUESTS_PER_SECOND))
)

POST_PUT_WAIT_SECONDS = float(os.getenv("POST_PUT_WAIT_SECONDS", "5"))
GET_RETRY_ROUNDS = int(os.getenv("GET_RETRY_ROUNDS", "6"))
GET_RETRY_BASE_DELAY_SECONDS = float(os.getenv("GET_RETRY_BASE_DELAY_SECONDS", "1"))
GET_RETRY_MAX_DELAY_SECONDS = float(os.getenv("GET_RETRY_MAX_DELAY_SECONDS", "15"))

_migrate_env = os.getenv("MIGRATE_HISTORY_API_KEY")
MIGRATE_HISTORY_API_KEY = _parse_bool(_migrate_env, default=(len(API_KEYS) > 1))


LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = LOGS_DIR / "app.log"

MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "2048"))
MAX_FORM_PARTS = int(os.getenv("MAX_FORM_PARTS", "20000"))

ALLOW_NO_API_KEYS = _parse_bool(os.getenv("ALLOW_NO_API_KEYS"), default=IS_FROZEN)

if not API_KEYS and not ALLOW_NO_API_KEYS:
    raise ValueError("API_KEY/API_KEYS nao configurada(s)! Verifique o arquivo .env")


SEPARACAO_TIPOS = {
    "placa": "Placa",
    "rota": "Identificador da rota",
}
