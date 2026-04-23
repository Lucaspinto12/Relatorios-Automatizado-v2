from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

from routes import modelo

load_dotenv()

app = FastAPI(
    title="Cognos Model Generator API",
    description="""
API para geração automática do **model.xml** do IBM Cognos Framework Manager.

## Fluxo
1. Envie as configurações do evento via `POST /modelo/gerar`
2. A API conecta ao Oracle, extrai os metadados e gera o XML
3. O `model_final.xml` é retornado para download

## Integração
Esta API pode ser consumida por qualquer serviço externo via HTTP.
A documentação interativa está disponível em `/docs` (Swagger) e `/redoc`.
    """,
    version="1.0.0",
    contact={"name": "Lucas Pinto"},
)

# CORS — permite o frontend React e outros serviços consumirem a API
origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(modelo.router)


@app.get("/", tags=["Health"])
def health_check():
    """Verifica se a API está no ar."""
    return {"status": "ok", "service": "Cognos Model Generator API"}
