import datetime
import os
from dotenv import load_dotenv

# Carrega variáveis do arquivo .env (se existir)
load_dotenv()

USER          = os.getenv("COGNOS_USER",          "SAFPOC542_SCH")
PASS          = os.getenv("COGNOS_PASS",          "SAFPOC542_SCH")
DSN           = os.getenv("COGNOS_DSN",           "ocipgd01.aquarius.cpqd.com.br:1521/bd119i1")

NOME_VIEW     = os.getenv("COGNOS_NOME_VIEW",     "VW_EVENT_UNI_CASH_IN")
NOME_COGNOS   = os.getenv("COGNOS_NOME_COGNOS",   "EVENT_UNI_CASH_IN")
NOME_NEGOCIO  = os.getenv("COGNOS_NOME_NEGOCIO",  "Cash-In")
DATA_SOURCE   = os.getenv("COGNOS_DATA_SOURCE",   "SAFO_UNICRED")

# Campo de valor da view que será exposto como VL_EVENT no SQL.
# Defina o nome da coluna de origem ou None para não incluir.
_vl = os.getenv("COGNOS_VL_EVENT_CAMPO", "VL_OPERACAO")
VL_EVENT_CAMPO = _vl if _vl and _vl.upper() != "NONE" else None

DATA_HOJE     = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
USUARIO       = "cpqd"

NS_URL = "http://www.developer.cognos.com/schemas/bmt/60/12"
BASE_SS = "[Star Schema View (Database)]"

# Dicionário de fallback para colunas calculadas no SQL que não existem no banco.
# As demais colunas (nomes de negócio e ordem) são buscadas via column_configuration.
DICIONARIO_NEGOCIO = {
    # Colunas calculadas no SQL (padrão todos os eventos)
    "DT_HR_EVENT":      "Data e Hora do Evento",
    "DT_EVENT":         "Data do Evento",
    "HR_EVENT":         "Hora do Evento",
    "DT_HR_PROCESSING": "Data e Hora do Processamento do Evento",
    "DT_PROCESSING":    "Data do Processamento do Evento",
    "HR_PROCESSING":    "Hora do Processamento do Evento",
    "NR_EVENT":         "Número do Evento",
    "QTD_EVENT":        "Quantidade de Evento",
    "ID_EVENT":         "Identificador do Evento",
    "ID_EVENT_TYPE":    "Identificador do Tipo de Evento",
    "VL_EVENT":         "Valor do Evento",
    # Campos da pasta Identificadores — fixos, padrão em todos os eventos
    "ID_RULE":                  "Identificador da Regra",
    "ID_ACTION_TYPE":           "Identificador da Recomendação de Aprovação",
    "CD_LABEL_EVENT_STATE":     "Identificador do Status do Evento",
    "CD_LABEL_EVENT_POC_STATE": "Identificador do Status do Evento de POC",
    "NM_SERVER_DECISION":       "Nome do Servidor de Decisão",
    # Campos de data/hora de processamento interno — padrão todos os eventos
    "DT_EXTRA_FIELD_1":         "Data e hora em que o evento iniciou o processo de persistência",
    "DT_EXTRA_FIELD_2":         "Data e hora em que a execução do projeto de regras foi finalizada",
    "DT_EXTRA_FIELD_3":         "Data e hora em que a execução do projeto de regras complexas foi finalizada",
    "DT_EXTRA_FIELD_4":         "Data e hora que a lista de restrição foi finalizada",
    "DT_INPUT_CEP":              "Data e hora em que o evento chegou no módulo de regras complexas",
    "DT_INPUT_CONNECTOR":        "Data e hora em que o evento chegou no conector do módulo de eventos",
    "DT_INPUT_DECISION":         "Data e hora em que o evento chegou no módulo de decisão",
    "DT_INPUT_ENRICHMENT":       "Data e hora em que o evento chegou no enriquecimento",
    "DT_INPUT_EVENTS":           "Data e hora em que o evento chegou no módulo de eventos",
    "DT_INPUT_RESTRICTION_LIST": "Data e hora que a lista de restrição foi iniciada",
    "DT_INPUT_RULE":             "Data e hora em que o evento chegou no módulo de regras simples",
    "DT_INPUT_SCORE":            "Data e hora em que o evento chegou no score",
    "DT_INPUT_SUMMARY":          "Data e hora de resumo do evento",
    "DT_OUTPUT_DECISION":        "Data e hora em que o evento saiu do módulo de decisão",
    "DT_OUTPUT_EVENTS":          "Data e hora em que o evento saiu do módulo de eventos",
}
