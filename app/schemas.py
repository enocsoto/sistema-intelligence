from typing import Any, Literal

from pydantic import BaseModel, Field

JobStatus = Literal[
    "PENDING",
    "RUNNING",
    "WAITING_APPROVAL",
    "RESUMING",
    "FAILED",
    "DONE",
    "REJECTED",
]


class TaskIn(BaseModel):
    query: str = Field(min_length=3, max_length=2000)


class TaskCreated(BaseModel):
    job_id: str
    status: Literal["PENDING"]


class JobOut(BaseModel):
    job_id: str
    status: JobStatus
    query: str
    result: str | None = None
    error: str | None = None


class ApprovalIn(BaseModel):
    aprobado: bool


class ApprovalOut(BaseModel):
    job_id: str
    status: Literal["RESUMING"]


class ClienteArgs(BaseModel):
    cliente_id: int = Field(ge=1, description="Id numérico del cliente")


class PoliticaArgs(BaseModel):
    consulta: str = Field(min_length=3, max_length=500)


class PromedioArgs(BaseModel):
    total: float = Field(ge=0)
    cantidad: int = Field(ge=1)


class DocumentoRecuperado(BaseModel):
    id: str
    texto: str
    metadata: dict[str, Any]


class HallazgoCliente(BaseModel):
    consulta: str
    documentos: list[DocumentoRecuperado]
    cliente_id: int
    pedidos: int = Field(ge=0)
    total: float = Field(ge=0)
    ultimo: str
    fuente: str


class ErrorCliente(BaseModel):
    error: str
    cliente_id: int
    sugerencia: str


class HallazgoPolitica(BaseModel):
    consulta: str
    documentos: list[DocumentoRecuperado] = Field(min_length=1)


class ErrorPolitica(BaseModel):
    error: str
    consulta: str


class TicketSalida(BaseModel):
    total: float = Field(ge=0)
    cantidad: int = Field(ge=1)
    ticket_promedio: float = Field(ge=0)
    supera_4000: bool
