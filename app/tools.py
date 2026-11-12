import json
import re

from langchain_core.tools import tool
from pydantic import BaseModel, ValidationError

from app.rag import buscar_cliente as _cliente
from app.rag import buscar_politica as _politica
from app.schemas import (
    ClienteArgs,
    ErrorCliente,
    ErrorPolitica,
    HallazgoCliente,
    HallazgoPolitica,
    PoliticaArgs,
    PromedioArgs,
    TicketSalida,
)


@tool(args_schema=ClienteArgs)
async def buscar_cliente(cliente_id: int) -> str:
    """Recupera pedidos y total de un cliente con búsqueda híbrida. No calcula promedios."""
    return _validar(await _cliente(cliente_id), HallazgoCliente, ErrorCliente)


@tool(args_schema=PoliticaArgs)
async def buscar_politica(consulta: str) -> str:
    """Recupera políticas de la base (reembolso, envío) combinando vectores y BM25."""
    return _validar(await _politica(consulta), HallazgoPolitica, ErrorPolitica)


@tool(args_schema=PromedioArgs)
async def calcular_ticket_promedio(total: float, cantidad: int) -> str:
    """Calcula el ticket promedio y dice si supera 4000. No inventa cifras."""
    promedio = round(total / cantidad, 2)
    return TicketSalida(
        total=total,
        cantidad=cantidad,
        ticket_promedio=promedio,
        supera_4000=promedio > 4000,
    ).model_dump_json()


def _validar(raw: str, *modelos: type[BaseModel]) -> str:
    """La salida de la herramienta tiene que calzar en uno de los modelos."""
    data = json.loads(raw)
    ultimo: ValidationError | None = None
    for modelo in modelos:
        try:
            return modelo.model_validate(data).model_dump_json()
        except ValidationError as exc:
            ultimo = exc
    if ultimo is not None:
        raise ultimo
    raise ValidationError.from_exception_data("salida", [])


def cliente_de(query: str) -> int | None:
    match = re.search(r"cliente\s+(\d+)", query, flags=re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None
