import asyncio
import time

import httpx

QUERIES = [
    "¿Cuántos pedidos tiene el cliente 7?",
    "Ticket del cliente 102",
    "¿Cuál es la política de reembolso?",
    "¿Cuánto tarda el envío express?",
    "Pedidos del cliente 441",
]


async def main() -> None:
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000", timeout=30) as client:
        started = time.perf_counter()
        responses = await asyncio.gather(
            *[client.post("/tasks", json={"query": query}) for query in QUERIES]
        )
        elapsed = time.perf_counter() - started
    for query, response in zip(QUERIES, responses):
        print(response.status_code, response.json(), query)
    print(f"5 POST en {elapsed:.3f}s")


if __name__ == "__main__":
    asyncio.run(main())
