from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS: let the grader's web page call this service from the browser
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Layer 1: defaults ----------
DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}

# ---------- Layer 2: config.development.yaml ----------
YAML_LAYER = {
    "api_key": "key-y8nbpoowmm",
}

# ---------- Layer 3: .env file ----------
DOTENV_TEXT = """
APP_PORT=8454
APP_DEBUG=false
APP_LOG_LEVEL=warning
APP_API_KEY=key-do72pmzr3s
"""

# ---------- Layer 4: OS environment variables ----------
OS_ENV = {
    "APP_LOG_LEVEL": "error",
    "APP_API_KEY": "key-3bpda2nuqt",
}

ALIASES = {"num_workers": "workers"}
INT_KEYS = {"port", "workers"}
TRUE_WORDS = {"true", "1", "yes", "on"}


def normalize_key(raw_key: str) -> str:
    """APP_PORT -> port, NUM_WORKERS -> workers, Port -> port"""
    key = raw_key.strip().lower()
    if key.startswith("app_"):
        key = key[4:]
    return ALIASES.get(key, key)


def coerce(key: str, value):
    if key in INT_KEYS:
        return int(str(value).strip())
    if key == "debug":
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in TRUE_WORDS
    return str(value)


def parse_dotenv(text: str) -> dict:
    result = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        result[normalize_key(k)] = v.strip().strip('"').strip("'")
    return result


def parse_os_env(env: dict) -> dict:
    result = {}
    for k, v in env.items():
        if k.upper().startswith("APP_"):
            result[normalize_key(k)] = v
    return result


@app.get("/")
def home():
    return {"status": "ok", "use": "GET /effective-config"}


@app.get("/effective-config")
def effective_config(request: Request):
    merged = dict(DEFAULTS)                         # lowest
    merged.update(YAML_LAYER)                       # then YAML
    merged.update(parse_dotenv(DOTENV_TEXT))        # then .env
    merged.update(parse_os_env(OS_ENV))             # then OS env

    # Highest: CLI overrides like ?set=port=9000&set=debug=true
    for item in request.query_params.getlist("set"):
        if "=" not in item:
            continue
        k, v = item.split("=", 1)
        merged[normalize_key(k)] = v

    try:
        final = {k: coerce(k, v) for k, v in merged.items()}
    except ValueError:
        raise HTTPException(status_code=400, detail="port and workers must be integers")

    final["api_key"] = "****"                       # always mask the secret
    return final