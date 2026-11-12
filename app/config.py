import os


def setting(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


REDIS_URL = setting("REDIS_URL", "redis://localhost:6391")
CHROMA_PATH = setting("CHROMA_PATH", ".chroma")
CHROMA_COLLECTION = setting("CHROMA_COLLECTION", "tienda")
OPENAI_MODEL = setting("OPENAI_MODEL")
UMBRAL_CRITICO = int(setting("UMBRAL_CRITICO", "10000") or "10000")
PHOENIX_PROJECT = setting("PHOENIX_PROJECT", "sistema-intelligence")
PHOENIX_ENDPOINT = setting(
    "PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:6006/v1/traces"
)
