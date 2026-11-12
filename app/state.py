from typing import Literal

from langgraph.graph import MessagesState


class OrchestratorState(MessagesState):
    """Estado del orquestador. messages se acumula; el resto lo pisa cada nodo."""

    query: str
    next_agent: Literal["research", "analyst", "hitl", "finish"]
    steps: int
    findings: str
    analysis: str
    critical: bool
    approved: bool | None
    task_completed: bool
