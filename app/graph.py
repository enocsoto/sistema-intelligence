from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from app.hitl import hitl_node
from app.nodes import analyst_node, research_node, route, supervisor_node
from app.state import OrchestratorState


def build_graph(checkpointer: BaseCheckpointSaver):
    graph = StateGraph(OrchestratorState)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("research", research_node)
    graph.add_node("hitl", hitl_node)
    graph.add_node("analyst", analyst_node)
    graph.add_edge(START, "supervisor")
    graph.add_conditional_edges(
        "supervisor",
        route,
        {"research": "research", "analyst": "analyst", "hitl": "hitl", "finish": END},
    )
    graph.add_edge("research", "supervisor")
    graph.add_edge("hitl", "supervisor")
    graph.add_edge("analyst", "supervisor")
    return graph.compile(checkpointer=checkpointer)
