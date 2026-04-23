from pydantic import BaseModel, Field
from typing import Optional


class ConfiguracaoEvento(BaseModel):
    """Configurações necessárias para gerar o model.xml de um evento."""

    user: str = Field(..., description="Usuário Oracle", example="SAFPOC542_SCH")
    password: str = Field(..., description="Senha Oracle", example="minhasenha")
    dsn: str = Field(..., description="DSN Oracle (host:porta/servico)", example="ocipgd01.aquarius.cpqd.com.br:1521/bd119i1")

    nome_view: str = Field(..., description="Nome da view Oracle do evento", example="VW_EVENT_UNI_CASH_IN")
    nome_cognos: str = Field(..., description="Nome técnico do evento no Cognos", example="EVENT_UNI_CASH_IN")
    nome_negocio: str = Field(..., description="Nome de negócio do evento (usado nas namespaces)", example="Cash-In")
    data_source: str = Field(..., description="Nome da fonte de dados no Cognos", example="SAFO_UNICRED")

    vl_event_campo: Optional[str] = Field(
        None,
        description="Campo de valor da view para alias VL_EVENT no SQL. Deixe vazio para não incluir.",
        example="VL_OPERACAO"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "user": "SAFPOC542_SCH",
                "password": "minhasenha",
                "dsn": "ocipgd01.aquarius.cpqd.com.br:1521/bd119i1",
                "nome_view": "VW_EVENT_UNI_CASH_IN",
                "nome_cognos": "EVENT_UNI_CASH_IN",
                "nome_negocio": "Cash-In",
                "data_source": "SAFO_UNICRED",
                "vl_event_campo": "VL_OPERACAO"
            }
        }
