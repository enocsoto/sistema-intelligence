import json
import os

from langchain_core.messages import AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.config import OPENAI_MODEL
from app.hitl import es_critica
from app.llm import redactar
from app.state import OrchestratorState
from app.tools import (
    buscar_cliente,
    buscar_politica,
    calcular_ticket_promedio,
    cliente_de,
)

MAX_STEPS = 6


def decidir(state: OrchestratorState, steps: int) -> str:
    """Cierra solo con hallazgo y análisis. Corta el bucle a los 6 pasos."""
    if steps >= MAX_STEPS:
        return "finish"
    if not state.get("findings"):
        return "research"
    if state.get("critical") and state.get("approved") is None:
        return "hitl"
    if state.get("approved") is False:
        return "finish"
    if not state.get("analysis"):
        return "analyst"
    return "finish"


class Decision(BaseModel):
    next_agent: str = Field(description="research, analyst, hitl o finish")
    reason: str


async def research_node(state: OrchestratorState) -> dict:
    query = state.get("query") or ""
    cliente = cliente_de(query)
    if cliente is None:
        raw = await buscar_politica.ainvoke({"consulta": query})
    else:
        raw = await buscar_cliente.ainvoke({"cliente_id": cliente})
    text = await redactar(
        "Sos el investigador. Resumí el JSON en una frase. No calcules promedios.",
        raw,
    )
    return {
        "findings": raw,
        "critical": es_critica(query, raw),
        "messages": [AIMessage(content=text, name="research")],
    }


async def analyst_node(state: OrchestratorState) -> dict:
    findings = state.get("findings") or ""
    total, cantidad = _numeros(findings)
    if total is None or cantidad is None:
        raw = findings
        text = await redactar(
            "Resumí el conocimiento recuperado. No inventes reglas ni cifras.",
            raw,
        )
    else:
        raw = await calcular_ticket_promedio.ainvoke(
            {"total": total, "cantidad": cantidad}
        )
        text = await redactar(
            "Decí el ticket promedio y si supera 4000. No inventes cifras.",
            raw,
        )
    return {"analysis": text, "messages": [AIMessage(content=text, name="analyst")]}


async def supervisor_node(state: OrchestratorState) -> dict:
    steps = int(state.get("steps", 0)) + 1
    if os.getenv("OPENAI_API_KEY", "").strip() and OPENAI_MODEL:
        await _proponer(state)
    nxt = decidir(state, steps)
    return {
        "next_agent": nxt,
        "steps": steps,
        "task_completed": nxt == "finish",
        "messages": [AIMessage(content=f"supervisor -> {nxt}", name="supervisor")],
    }


def route(state: OrchestratorState) -> str:
    return state["next_agent"]


async def _proponer(state: OrchestratorState) -> str:
    model = ChatOpenAI(model=OPENAI_MODEL, temperature=0)
    decision = await model.with_structured_output(Decision).ainvoke(
        [
            SystemMessage(
                content=(
                    "Elegí el siguiente nodo. finish solo si ya hay hallazgo y análisis. "
                    "hitl si la tarea es crítica y nadie aprobó. "
                    "research si no hay hallazgo. analyst si hay hallazgo y falta el cálculo."
                )
            ),
            SystemMessage(
                content=(
                    f"query={state.get('query', '')}\n"
                    f"findings={state.get('findings') or '(vacío)'}\n"
                    f"analysis={state.get('analysis') or '(vacío)'}\n"
                    f"critical={state.get('critical')}\n"
                    f"approved={state.get('approved')}"
                )
            ),
        ]
    )
    return decision.next_agent


def _numeros(findings: str) -> tuple[float | None, int | None]:
    try:
        data = json.loads(findings)
    except json.JSONDecodeError:
        return None, None
    if "error" in data or "total" not in data or "pedidos" not in data:
        return None, None
    return float(data["total"]), int(data["pedidos"])
