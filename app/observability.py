import os

from app.config import PHOENIX_ENDPOINT, PHOENIX_PROJECT


def setup_tracing() -> None:
    """LangSmith se prende con LANGCHAIN_TRACING_V2. Phoenix, con PHOENIX_ENABLED=1."""
    if os.getenv("PHOENIX_ENABLED", "0") != "1":
        return
    from openinference.instrumentation.langchain import LangChainInstrumentor
    from phoenix.otel import register

    provider = register(
        project_name=PHOENIX_PROJECT,
        endpoint=PHOENIX_ENDPOINT,
        auto_instrument=False,
    )
    LangChainInstrumentor().instrument(tracer_provider=provider)
