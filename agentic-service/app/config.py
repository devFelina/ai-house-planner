import os
from pathlib import Path

OUTPUT_PLANS_DIR = Path(__file__).resolve().parents[1] / "output_plans"
OUTPUT_PLANS_DIR.mkdir(parents=True, exist_ok=True)
def load_dotenv():
    env_paths = [
        os.path.join(os.path.dirname(__file__), "..", ".env"),
        os.path.join(os.path.dirname(__file__), "..", "..", "HousePlanner.API", ".env"),
    ]
    for env_path in env_paths:
        if not os.path.exists(env_path):
            continue
        with open(env_path) as f:
            for line in f:
                if line.strip() and not line.startswith("#"):
                    if "=" in line:
                        key, val = line.strip().split("=", 1)
                        # Don't overwrite if already set by an earlier .env or actual env
                        if key.strip() not in os.environ:
                            os.environ[key.strip()] = val.strip().strip('"\'')

load_dotenv()

def _dotnet_to_psycopg2(dotnet_str: str) -> str:
    """Convert .NET-style connection string to psycopg2 DSN."""
    parts: dict[str, str] = {}
    for segment in dotnet_str.split(';'):
        segment = segment.strip()
        if '=' in segment:
            k, v = segment.split('=', 1)
            parts[k.strip().lower()] = v.strip()

    host = parts.get('host', 'localhost')
    port = parts.get('port', '5432')
    dbname = parts.get('database', 'postgres')
    user = parts.get('username', 'postgres')
    password = parts.get('password', '')
    sslmode = 'require' if 'require' in parts.get('ssl mode', '').lower() else 'prefer'

    return f"host={host} port={port} dbname={dbname} user={user} password={password} sslmode={sslmode}"

def get_db_connection_string() -> str:
    """Build a psycopg2-compatible DSN from the .env DATABASE_CONNECTION_STRING."""
    raw = os.getenv('DATABASE_CONNECTION_STRING', '')
    if raw:
        return _dotnet_to_psycopg2(raw)
    raise RuntimeError("DATABASE_CONNECTION_STRING not found in .env or environment.")

ASPNET_API_URL = os.getenv("ASPNET_API_URL", "http://localhost:5265/api/v1")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY")
if not INTERNAL_API_KEY:
    raise RuntimeError("INTERNAL_API_KEY must be configured in the environment or agentic-service/.env")
PRICING_VERIFY_TLS = os.getenv("PRICING_VERIFY_TLS", "true").strip().lower() not in {"0", "false", "no"}

DESIGN_PROVIDER_ORDER = [
    p.strip()
    for p in os.getenv("DESIGN_PROVIDER_ORDER", "openai,ollama").split(",")
    if p.strip()
]

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")

# Optional Fallbacks
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
