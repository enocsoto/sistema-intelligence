import asyncio
import os
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from redis.asyncio import Redis

from app.config import REDIS_URL
from app.observability import setup_tracing
from app.schemas import ApprovalIn, ApprovalOut, JobOut, TaskCreated, TaskIn
from app.worker import QUEUE, compile_graph, load, resume_job, save, worker_loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_tracing()
    redis = Redis.from_url(REDIS_URL, decode_responses=True)
    saver = AsyncRedisSaver(redis_url=REDIS_URL)
    await saver.setup()
    graph = compile_graph(saver)
    app.state.redis = redis
    app.state.graph = graph
    task = asyncio.create_task(worker_loop(redis, graph))
    try:
        yield
    finally:
        task.cancel()
        await redis.aclose()


app = FastAPI(
    title="Sistema Intelligence",
    description="RAG híbrido, supervisor, aprobación humana y trazas.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.post("/tasks", response_model=TaskCreated)
async def create_task(body: TaskIn):
    job_id = str(uuid.uuid4())
    await save(
        app.state.redis,
        job_id,
        {"status": "PENDING", "query": body.query, "result": None, "error": None},
    )
    await app.state.redis.rpush(QUEUE, job_id)
    return TaskCreated(job_id=job_id, status="PENDING")


@app.get("/tasks/{job_id}", response_model=JobOut)
async def get_task(job_id: str):
    payload = await load(app.state.redis, job_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    return JobOut.model_validate(payload)


@app.post("/tasks/{job_id}/approve", response_model=ApprovalOut)
async def approve(job_id: str, body: ApprovalIn):
    payload = await load(app.state.redis, job_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    if payload["status"] != "WAITING_APPROVAL":
        raise HTTPException(status_code=409, detail="El job no está esperando aprobación")
    asyncio.create_task(
        resume_job(app.state.graph, app.state.redis, job_id, body.aprobado)
    )
    return ApprovalOut(job_id=job_id, status="RESUMING")


def main() -> None:
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=False,
    )
