from pydantic import BaseModel, Field
from typing import Any, Dict


class ContextAddRequest(BaseModel):
    text: str = Field(..., description="Texto o contexto a vectorizar y almacenar")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class QueryRequest(BaseModel):
    query_text: str = Field(..., description="Query textual para búsqueda semántica")
    k: int = Field(default=3, description="Número de resultados a devolver")
