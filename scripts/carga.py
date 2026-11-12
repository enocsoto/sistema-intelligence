import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

import httpx

QUERIES = [
    "¿Cuántos pedidos tiene el cliente 7?",
    "Ticket del cliente 102",
    "¿Cuál es la política de reembolso?",
    "¿Cuánto tarda el envío express?",
    "Pedidos del cliente 441",
]
TERMINALES = {"DONE", "WAITING_APPROVAL", "REJECTED", "FAILED"}
PHOENIX = "http://127.0.0.1:6006"
PROYECTO = "sistema-intelligence"
SALIDA = Path(__file__).resolve().parent.parent / "traces" / "pruebas.json"


async def _esperar(client: httpx.AsyncClient, job_id: str) -> dict:
    for _ in range(40):
        response = await client.get(f"/tasks/{job_id}")
        response.raise_for_status()
        cuerpo = response.json()
        if cuerpo["status"] in TERMINALES:
            return cuerpo
        await asyncio.sleep(0.5)
    raise SystemExit(f"La tarea {job_id} no terminó.")


def _spans(desde: datetime) -> int:
    proyectos = httpx.get(f"{PHOENIX}/v1/projects", timeout=10).json()["data"]
    proyecto = next(item for item in proyectos if item["name"] == PROYECTO)
    vistos = 0
    cursor = None
    while True:
        params = {"limit": 200}
        if cursor:
            params["cursor"] = cursor
        pagina = httpx.get(
            f"{PHOENIX}/v1/projects/{proyecto['id']}/spans",
            params=params,
            timeout=20,
        ).json()
        for span in pagina["data"]:
            inicio = datetime.fromisoformat(span["start_time"])
            if inicio >= desde:
                vistos += 1
        cursor = pagina.get("next_cursor")
        if not cursor:
            return vistos


async def main() -> None:
    desde = datetime.now(timezone.utc)
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000", timeout=30) as client:
        respuestas = await asyncio.gather(
            *[client.post("/tasks", json={"query": query}) for query in QUERIES]
        )
        for respuesta in respuestas:
            respuesta.raise_for_status()
        jobs = [respuesta.json()["job_id"] for respuesta in respuestas]
        finales = await asyncio.gather(*[_esperar(client, job_id) for job_id in jobs])
    spans = _spans(desde)
    if spans < 1:
        raise SystemExit("Phoenix no recibió spans de estas 5 pruebas.")
    informe = {
        "proyecto": PROYECTO,
        "spans_nuevos": spans,
        "pruebas": [
            {"query": query, "status": final["status"], "result": final.get("result")}
            for query, final in zip(QUERIES, finales)
        ],
    }
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps(informe, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(informe, ensure_ascii=False, indent=2))
    print(f"Informe en {SALIDA}")


if __name__ == "__main__":
    asyncio.run(main())
