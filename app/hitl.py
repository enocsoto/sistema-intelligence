from typing import Any

from langchain_core.messages import AIMessage
from langgraph.types import interrupt

from app.config import UMBRAL_CRITICO
from app.state import OrchestratorState

RECHAZO = "Reembolso rechazado por el revisor"


def es_critica(query: str, findings: str) -> bool:
    """Total alto, o la palabra crítico en el pedido."""
    texto = f"{query} {findings}".lower()
    if "crítico" in texto or "critico" in texto:
        return True
    for token in findings.replace(",", " ").split():
        limpio = token.strip('":{}')
        if limpio.isdigit() and int(limpio) >= UMBRAL_CRITICO:
            return True
    return False


async def hitl_node(state: OrchestratorState) -> dict[str, Any]:
    """Pausa el grafo si la tarea es crítica. El resume trae {"aprobado": bool}."""
    if not state.get("critical"):
        return {"approved": True}
    decision = interrupt(
        {
            "motivo": "Tarea crítica: hace falta un revisor antes de seguir.",
            "query": state.get("query", ""),
            "findings": state.get("findings", ""),
        }
    )
    aprobado = bool(isinstance(decision, dict) and decision.get("aprobado"))
    if not aprobado:
        return {
            "approved": False,
            "analysis": RECHAZO,
            "task_completed": True,
            "messages": [AIMessage(content=RECHAZO, name="hitl")],
        }
    return {
        "approved": True,
        "messages": [AIMessage(content="Aprobado por el revisor", name="hitl")],
    }
