import json
import re

from langchain_core.tools import tool

from app.rag import buscar_cliente as _cliente
from app.rag import buscar_politica as _politica
from app.schemas import ClienteArgs, PoliticaArgs, PromedioArgs


@tool(args_schema=ClienteArgs)
async def buscar_cliente(cliente_id: int) -> str:
    """Recupera pedidos y total de un cliente con búsqueda híbrida. No calcula promedios."""
    return await _cliente(cliente_id)


@tool(args_schema=PoliticaArgs)
async def buscar_politica(consulta: str) -> str:
    """Recupera políticas de la base (reembolso, envío) combinando vectores y BM25."""
    return await _politica(consulta)


@tool(args_schema=PromedioArgs)
async def calcular_ticket_promedio(total: float, cantidad: int) -> str:
    """Calcula el ticket promedio y dice si supera 4000. No inventa cifras."""
    promedio = round(total / cantidad, 2)
    return json.dumps(
        {
            "total": total,
            "cantidad": cantidad,
            "ticket_promedio": promedio,
            "supera_4000": promedio > 4000,
        },
        ensure_ascii=False,
    )


def cliente_de(query: str) -> int | None:
    match = re.search(r"cliente\s+(\d+)", query, flags=re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None
