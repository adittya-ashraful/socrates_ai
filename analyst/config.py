import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)

# ── LLM ───────────────────────────────────────────────────────────────────
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")

# ── Checkpointing ─────────────────────────────────────────────────────────
CHECKPOINT_BACKEND: str = os.getenv("CHECKPOINT_BACKEND", "postgres")  
CHECKPOINT_POSTGRES_URL: str = os.getenv(
    "CHECKPOINT_POSTGRES_URL"
)
# ── Charts ────────────────────────────────────────────────────────────────
CHART_DIR: str = os.getenv(
    "CHART_DIR",
    str(Path(__file__).resolve().parent.parent / "charts"),
)

# ── Guards & limits ───────────────────────────────────────────────────────
MAX_INPUT_LENGTH: int = 8_000
CONTEXT_TOKEN_LIMIT: int = 100_000
HIGH_CONFIDENCE: float = 0.80
MEDIUM_CONFIDENCE: float = 0.55
MAX_CLARIFICATION_TURNS: int = 2
MAX_PLAN_STEPS: int = 6
SQL_CACHE_TTL: int = 300
MAX_STEP_RETRIES: int = 2
TIMEOUT_SECONDS: int = 120
COST_LIMIT_USD: float = 0.50
MAX_REPLANS: int = 3
LONG_TERM_THRESHOLD: float = 0.80
