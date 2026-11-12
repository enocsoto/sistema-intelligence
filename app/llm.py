import os

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.config import OPENAI_MODEL


async def redactar(instruccion: str, datos: str) -> str:
    """Si hay clave y modelo, el LLM redacta. Si no, sale el dato de la herramienta."""
    if not os.getenv("OPENAI_API_KEY", "").strip() or not OPENAI_MODEL:
        return datos
    model = ChatOpenAI(model=OPENAI_MODEL, temperature=0)
    message = await model.ainvoke(
        [SystemMessage(content=instruccion), HumanMessage(content=datos)]
    )
    return str(message.content)
