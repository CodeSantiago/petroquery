from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OGTMetadata(BaseModel):
    cuenca: Optional[str] = Field(None, examples=["Vaca Muerta", "Neuquina"])
    tipo_equipo: Optional[str] = Field(None, examples=["BOP", "Christmas Tree", "Pumpjack", "Casing", "Tubing"])
    normativa_aplicable: Optional[str] = Field(None, examples=["IAPG-IRAM 301", "Res. SE 123/2018", "API RP 14B"])
    tipo_documento: Optional[str] = Field(None, examples=["manual", "normativa", "reporte", "especificacion"])
    pozo_referencia: Optional[str] = None
    fecha_documento: Optional[datetime] = None
    seccion: Optional[str] = Field(None, description="Section or chapter reference")
    tabla_referencia: Optional[str] = Field(None, description="Table identifier (e.g., 'Tabla 3.2')")
    figura_referencia: Optional[str] = Field(None, description="Figure identifier (e.g., 'Figura 4.1')")


class SourceReference(BaseModel):
    documento: str = Field(..., description="Exact document name")
    pagina: int = Field(..., description="Exact page number")
    seccion: Optional[str] = Field(None, description="Section or chapter")
    tabla_referencia: Optional[str] = None
    figura_referencia: Optional[str] = None
    score_confianza: float = Field(..., ge=0.0, le=1.0, description="Retrieval confidence score")
    contenido_citado: str = Field(..., description="Literal text from the source chunk")
    cuenca: Optional[str] = None
    normativa_aplicable: Optional[str] = None


class OGTechnicalAnswer(BaseModel):
    respuesta_tecnica: str = Field(..., description="Structured technical answer in markdown")
    advertencia_seguridad: Optional[str] = Field(None, description="Safety warning if query involves operational risk")
    fuentes: list[SourceReference] = Field(..., min_length=0, description="Complete traceability sources")
    score_global_confianza: float = Field(..., ge=0.0, le=1.0)
    necesita_revision_humana: bool = Field(False, description="True if confidence < 0.7 or safety-critical ambiguity")
    tipo_consulta: str = Field(..., examples=["operacional", "normativa", "seguridad", "equipos", "general"])


class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    company_id: Optional[UUID] = None
    cuenca: Optional[str] = None
    ubicacion: Optional[str] = None

class ProjectCreate(ProjectBase):
    pass

class ProjectResponse(ProjectBase):
    id: int
    created_by: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ProjectMemberBase(BaseModel):
    user_id: int
    role: str = Field(default="viewer", pattern="^(admin|editor|viewer)$")

class ProjectMemberCreate(ProjectMemberBase):
    pass

class ProjectMemberResponse(BaseModel):
    id: int
    project_id: int
    user_id: int
    role: str
    joined_at: datetime
    model_config = ConfigDict(from_attributes=True)

class CompanyBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)

class CompanyCreate(CompanyBase):
    pass

class CompanyResponse(CompanyBase):
    id: UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
