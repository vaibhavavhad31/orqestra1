import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def _flag(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    return default if raw is None or raw.strip() == "" else raw.strip().lower() in ("1", "true", "yes", "on")


MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
JWT_SECRET = os.environ["JWT_SECRET"]
DEMO_PASSWORD = os.environ["DEMO_PASSWORD"]
CORS_ORIGINS = [o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()]

# Cookies: Secure + SameSite=None is required for HTTPS hosting; plain-HTTP local runs need COOKIE_SECURE=false.
COOKIE_SECURE = _flag("COOKIE_SECURE", True)

# Optional: Google sign-in only worked through Emergent's managed auth. Off unless explicitly enabled.
ENABLE_EMERGENT_GOOGLE_AUTH = _flag("ENABLE_EMERGENT_GOOGLE_AUTH", False)
EMERGENT_SESSION_URL = "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"

# Optional LLM for task decomposition. Without a key Orqestra uses its free built-in rules.
LLM_API_KEY = os.environ.get("LLM_API_KEY", "").strip()
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1").strip().rstrip("/")
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-4o-mini").strip()

# Built React app served by FastAPI (single service, same origin). Empty = API only.
FRONTEND_BUILD_DIR = os.environ.get("FRONTEND_BUILD_DIR", "").strip()

JWT_ALGORITHM = "HS256"
ACCESS_TTL_MINUTES = 60
REFRESH_TTL_DAYS = 7
DEFAULT_ORG_BUDGET = 10000
DEFAULT_PERSONAL_CREDITS = 1000
