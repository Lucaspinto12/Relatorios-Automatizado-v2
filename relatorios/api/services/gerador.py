"""
Serviço que orquestra a geração do model.xml.
Importa os módulos da automação existente e os executa com as
configurações recebidas via API.
"""
import sys
import os
import tempfile
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

# Adiciona o path da automação para importar os módulos
# api/ está em relatorios/api/, então sobe 2 níveis para chegar em relatorios/
AUTOMACAO_PATH = Path(__file__).parent.parent.parent / "CPqD_Antifraude_Relatorios_Usuario"
sys.path.insert(0, str(AUTOMACAO_PATH))


def gerar_modelo(config_data: dict, model_base_path: str) -> bytes:
    """
    Executa a automação com as configurações recebidas e retorna
    o conteúdo do model_final.xml como bytes.
    """
    import importlib
    import config as cfg
    import oracle_utils
    import auto_modeler

    # Forçar reload dos módulos para garantir estado limpo entre chamadas
    importlib.reload(cfg)
    importlib.reload(oracle_utils)
    importlib.reload(auto_modeler)

    # Sobrescrever as configurações com os valores recebidos via API
    cfg.USER           = config_data["user"]
    cfg.PASS           = config_data["password"]
    cfg.DSN            = config_data["dsn"]
    cfg.NOME_VIEW      = config_data["nome_view"]
    cfg.NOME_COGNOS    = config_data["nome_cognos"]
    cfg.NOME_NEGOCIO   = config_data["nome_negocio"]
    cfg.DATA_SOURCE    = config_data["data_source"]
    cfg.VL_EVENT_CAMPO = config_data.get("vl_event_campo") or None

    from datetime import datetime
    cfg.DATA_HOJE = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

    # Buscar metadados do Oracle
    cols_oracle = oracle_utils.buscar_metadados()
    if not cols_oracle:
        raise RuntimeError("Não foi possível conectar ao Oracle ou a view não foi encontrada.")

    # Enriquecer dicionário com nomes de negócio do banco
    nomes_negocio_db, ordem_colunas_db = oracle_utils.buscar_nomes_negocio()
    if nomes_negocio_db:
        cfg.DICIONARIO_NEGOCIO.update(nomes_negocio_db)
    cfg.ORDEM_COLUNAS_DB = ordem_colunas_db

    # Parsear o model.xml base
    ET.register_namespace('', cfg.NS_URL)
    tree = ET.parse(model_base_path)
    root_xml = tree.getroot()

    # Executar todas as camadas da automação
    lista = auto_modeler.montar_camada_fisica(root_xml, cols_oracle)
    auto_modeler.montar_camada_star(root_xml)
    auto_modeler.montar_relacionamentos_ft(root_xml)
    auto_modeler.montar_relacionamentos_pontes_dim(root_xml)
    auto_modeler.montar_relacionamentos_dim(root_xml)
    auto_modeler.montar_camada_consolidation(root_xml, lista, cols_oracle)
    auto_modeler.montar_camada_presentation(root_xml)

    # Serializar para string XML (lógica do finalizer)
    import re
    xml_str = ET.tostring(root_xml, encoding='utf-8').decode('utf-8')
    xml_str = xml_str.replace('ns0:', '').replace(':ns0', '')
    xml_str = xml_str.replace('"', '___QUOT___')
    xml_str = re.sub(r'=(\s*)___QUOT___(.*?)\___QUOT___', r'="\2"', xml_str)
    xml_str = xml_str.replace('___QUOT___', '&quot;')
    xml_str = xml_str.replace("'", "&apos;")
    xml_str = xml_str.replace('&amp;', '&')
    xml_str = xml_str.replace("> = <", ">=<").replace("> AND <", ">AND<")

    conteudo = ('<?xml version="1.0" encoding="UTF-8" ?>\n' + xml_str).encode('utf-8')
    return conteudo
