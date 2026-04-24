from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import Response
import os
import json
import tempfile
from pathlib import Path

from schemas import ConfiguracaoEvento
from services.gerador import gerar_modelo

router = APIRouter(prefix="/modelo", tags=["Modelo"])


@router.post(
    "/gerar",
    summary="Gerar model.xml (usa arquivo base do servidor)",
    description="""
Gera o **model.xml** usando o arquivo base configurado no servidor via `MODEL_BASE_PATH`.
    """,
    response_class=Response,
    responses={
        200: {"content": {"application/xml": {}}, "description": "model_final.xml gerado"},
        400: {"description": "Configuração inválida"},
        500: {"description": "Erro ao conectar ao Oracle ou gerar o modelo"},
    },
)
async def gerar(configuracao: ConfiguracaoEvento):
    model_base_path = os.getenv(
        "MODEL_BASE_PATH",
        str(Path("/automacao/model.xml") if Path("/automacao").exists()
            else Path(__file__).parent.parent.parent / "CPqD_Antifraude_Relatorios_Usuario" / "model.xml")
    )
    if not Path(model_base_path).exists():
        raise HTTPException(status_code=400, detail=f"model.xml base não encontrado em: {model_base_path}")

    try:
        xml_bytes = gerar_modelo(configuracao.model_dump(), model_base_path)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro inesperado: {str(e)}")

    nome_arquivo = f"model_{configuracao.nome_cognos}.xml"
    return Response(
        content=xml_bytes,
        media_type="application/xml",
        headers={"Content-Disposition": f"attachment; filename={nome_arquivo}"}
    )


@router.post(
    "/gerar-com-base",
    summary="Gerar model.xml com upload do arquivo base",
    description="""
Recebe o **model.xml base** como upload de arquivo junto com as configurações do evento.

Ideal para uso via frontend ou integração com outros serviços que gerenciam seus próprios arquivos base.
    """,
    response_class=Response,
    responses={
        200: {"content": {"application/xml": {}}, "description": "model_final.xml gerado"},
        500: {"description": "Erro ao conectar ao Oracle ou gerar o modelo"},
    },
)
async def gerar_com_base(
    configuracao: str = Form(..., description="JSON com as configurações do evento"),
    model_base: UploadFile = File(..., description="Arquivo model.xml base do Cognos"),
):
    """
    Recebe o model.xml base como upload e as configurações como JSON no campo `configuracao`.
    """
    try:
        config_data = json.loads(configuracao)
        config_obj = ConfiguracaoEvento(**config_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Configuração inválida: {str(e)}")

    # Salvar o arquivo enviado em um temp file
    with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as tmp:
        conteudo = await model_base.read()
        tmp.write(conteudo)
        tmp_path = tmp.name

    try:
        xml_bytes = gerar_modelo(config_obj.model_dump(), tmp_path)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro inesperado: {str(e)}")
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    nome_arquivo = f"model_{config_obj.nome_cognos}.xml"
    return Response(
        content=xml_bytes,
        media_type="application/xml",
        headers={"Content-Disposition": f"attachment; filename={nome_arquivo}"}
    )
