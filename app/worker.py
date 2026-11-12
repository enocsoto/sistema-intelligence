import asyncio
import json
from typing import Any

from langgraph.types import Command
from redis.asyncio import Redis

from app.graph import build_graph

QUEUE = "intel_tasks"
PREFIX = "intel:job:"


def job_key(job_id: str) -> str:
    return f"{PREFIX}{job_id}"


async def save(redis: Redis, job_id: str, payload: dict[str, Any]) -> None:
    payload["job_id"] = job_id
    await redis.set(job_key(job_id), json.dumps(payload, ensure_ascii=False))


async def load(redis: Redis, job_id: str) -> dict[str, Any] | None:
    raw = await redis.get(job_key(job_id))
    if raw is None:
        return None
    return json.loads(raw)


def _interrumpido(snapshot) -> bool:
    if snapshot.next:
        return True
    for task in snapshot.tasks:
        if getattr(task, "interrupts", None):
            return True
    return False


async def run_job(graph, redis: Redis, job_id: str, query: str) -> None:
    current = await load(redis, job_id)
    if current is None:
        return
    current["status"] = "RUNNING"
    await save(redis, job_id, current)
    config = {"configurable": {"thread_id": job_id}, "recursion_limit": 12}
    try:
        await graph.ainvoke(_entrada(query), config)
        await _cerrar(graph, redis, job_id, config)
    except Exception as exc:
        failed = await load(redis, job_id) or {"query": query}
        failed["status"] = "FAILED"
        failed["error"] = str(exc)
        await save(redis, job_id, failed)


async def resume_job(graph, redis: Redis, job_id: str, aprobado: bool) -> None:
    config = {"configurable": {"thread_id": job_id}, "recursion_limit": 12}
    try:
        await graph.ainvoke(Command(resume={"aprobado": aprobado}), config)
        await _cerrar(graph, redis, job_id, config)
    except Exception as exc:
        current = await load(redis, job_id) or {}
        current["status"] = "FAILED"
        current["error"] = str(exc)
        await save(redis, job_id, current)


async def _cerrar(graph, redis: Redis, job_id: str, config: dict) -> None:
    snapshot = await graph.aget_state(config)
    current = await load(redis, job_id) or {}
    if _interrumpido(snapshot):
        current["status"] = "WAITING_APPROVAL"
        current["result"] = None
        await save(redis, job_id, current)
        return
    values = snapshot.values or {}
    texto = values.get("analysis") or ""
    if not texto:
        messages = values.get("messages") or []
        if messages:
            texto = str(messages[-1].content)
    current["status"] = "REJECTED" if values.get("approved") is False else "DONE"
    current["result"] = texto
    current["error"] = None
    await save(redis, job_id, current)


def _entrada(query: str) -> dict:
    return {
        "messages": [],
        "query": query,
        "next_agent": "research",
        "steps": 0,
        "findings": "",
        "analysis": "",
        "critical": False,
        "approved": None,
        "task_completed": False,
    }


async def worker_loop(redis: Redis, graph) -> None:
    print("worker listo", flush=True)
    while True:
        try:
            item = await redis.blpop(QUEUE, timeout=2)
        except Exception as exc:
            print("worker error", exc, flush=True)
            await asyncio.sleep(1)
            continue
        if not item:
            continue
        _, job_id = item
        payload = await load(redis, job_id)
        if payload is None:
            continue
        await run_job(graph, redis, job_id, payload["query"])


def compile_graph(saver):
    return build_graph(saver)
