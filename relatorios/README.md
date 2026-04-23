# Relatórios Automatizados (CPqD Antifraude) 🚀

## 📋 Sobre o Projeto

Este projeto automatiza a geração de modelos de metadados para o **IBM Cognos Framework Manager**, eliminando o processo manual de criação de tabelas, atalhos, relacionamentos e namespaces no arquivo `model.xml`.

---

## 💡 O Problema

A modelagem manual no Cognos Framework Manager é morosa e propensa a erros, especialmente ao lidar com grandes volumes de colunas vindas do Oracle. Problemas comuns incluem caracteres especiais mal formatados, aspas inválidas e hierarquias complexas que causam **Erro Fatal** na publicação do pacote.

## ✅ A Solução

Dois modos de uso — mesma lógica de geração:

| Modo | Como usar | Quando usar |
|---|---|---|
| **CLI** | `python auto_modeler.py` | Uso local, scripts, automação |
| **API + Frontend** | Interface web + FastAPI | Uso por outros times, integração com outros serviços |

---

## 🚀 Modo 1 — CLI (linha de comando)

### Pré-requisitos
- Python 3.10+
- `pip install -r requirements.txt`

### Configuração (`.env`)

Edite `CPqD_Antifraude_Relatorios_Usuario/.env`:

```env
COGNOS_USER=SAFPOC542_SCH
COGNOS_PASS=SUA_SENHA
COGNOS_DSN=ocipgd01.aquarius.cpqd.com.br:1521/bd119i1

COGNOS_NOME_VIEW=VW_EVENT_UNI_CASH_IN
COGNOS_NOME_COGNOS=EVENT_UNI_CASH_IN
COGNOS_NOME_NEGOCIO=Cash-In
COGNOS_DATA_SOURCE=SAFO_UNICRED

# Campo de valor para alias VL_EVENT. Deixe vazio para não incluir.
COGNOS_VL_EVENT_CAMPO=VL_OPERACAO
```

### Execução

```bash
cd CPqD_Antifraude_Relatorios_Usuario
python auto_modeler.py
```

O `model_final.xml` é gerado na mesma pasta. Renomeie para `model.xml` e abra o `.cpf` no Cognos Framework Manager.

---

## 🌐 Modo 2 — API + Frontend

### Estrutura

```
/
├── relatorios/CPqD_Antifraude_Relatorios_Usuario/   ← automação (CLI)
├── api/                                              ← FastAPI backend
└── frontend/                                         ← React frontend
```

### Rodando o Backend (FastAPI)

```bash
cd api
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

- **API**: `http://localhost:8000`
- **Swagger (documentação interativa)**: `http://localhost:8000/docs`

### Rodando o Frontend (React)

```bash
cd frontend
npm install
npm run dev
```

- **App**: `http://localhost:5173`

### Endpoints da API

| Método | Endpoint | Descrição |
|---|---|---|
| `GET` | `/` | Health check |
| `POST` | `/modelo/gerar` | Gera o XML usando o `model.xml` do servidor |
| `POST` | `/modelo/gerar-com-base` | Gera o XML com upload do `model.xml` base |

O frontend usa o endpoint `/modelo/gerar-com-base` — o usuário faz upload do `model.xml` base diretamente pela interface.

---

## 📦 O que é gerado automaticamente

| Camada | O que é criado |
|---|---|
| **Original Database** | `querySubject` com SQL da view, todos os campos como `attribute` |
| **Star Schema View** | Atalhos `FT_`, `DIM_` e 4 pontes (`x_ALARMED_RULE`, `x_ACTION_RECOMMENDATION`, `x_EVENT_POC_STATE_LAST`, `x_EVENT_STATE_LAST`) |
| **Relacionamentos** | FT↔Pontes, FT↔DIMs compartilhadas (DATE/HOUR/EVENT_TYPE), FD_UNI_COOPERADO, DIM↔FT_ALARMED_RULE, FT_PT_CASE_MANAGEMENT↔DIM |
| **Consolidation View** | `Evento <Nome>` (DIM — todos `attribute`) e `Fato Evento <Nome>` (Merge das 5 FTs com pasta Identificadores) |
| **Presentation View** | Namespace `Evento <Nome>` com atalhos padrão + atalho do Fato nas pastas Ação/Gerenciamento do Caso/Regra Alarmada |

### Regras de Usage no Fato

| Campo | Pasta | Usage |
|---|---|---|
| `QTD_EVENT` | fora | `fact` + `countDistinct` |
| `VL_EVENT` (se configurado) | fora | `fact` + `sum` |
| `ID_EVENT`, `ID_EVENT_TYPE`, `ID_RULE`, `ID_ACTION_TYPE`, `CD_LABEL_*` | Identificadores | `identifier` |
| `DT_*`, `HR_*`, `NM_SERVER_DECISION` | Identificadores | `attribute` |
| Demais campos de negócio | fora | `attribute` |

### Nomes de negócio — automático via banco

Os nomes são buscados automaticamente da tabela `column_configuration` (campo `DS_COLUMN`), na ordem de `ID_COLUMN_CONFIGURATION`. O `DICIONARIO_NEGOCIO` no `config.py` serve como fallback para colunas calculadas no SQL.

### VL_EVENT — campo de valor opcional

```env
# Inclui VL_EVENT = VL_OPERACAO no SQL
COGNOS_VL_EVENT_CAMPO=VL_OPERACAO

# Não inclui
COGNOS_VL_EVENT_CAMPO=
```

---

## 📁 Estrutura de Arquivos

```
CPqD_Antifraude_Relatorios_Usuario/
├── auto_modeler.py     # Motor principal — orquestra todas as camadas
├── config.py           # Configurações (lê do .env automaticamente)
├── oracle_utils.py     # Conexão Oracle: metadados e nomes de negócio
├── xml_helpers.py      # Helpers ElementTree com namespace Cognos BMT
├── finalizer.py        # Serializa o XML final
├── requirements.txt    # Dependências Python
└── .env.example        # Template de configuração

api/
├── main.py             # FastAPI app + CORS
├── schemas.py          # Modelos Pydantic
├── routes/modelo.py    # Endpoints POST /modelo/gerar*
├── services/gerador.py # Orquestra a automação via API
└── requirements.txt

frontend/
├── src/
│   ├── App.tsx
│   ├── components/
│   │   ├── Header.tsx
│   │   ├── FormField.tsx
│   │   └── ModeloForm.tsx   # Formulário com upload do model.xml
│   └── api/modeloApi.ts     # Chamadas à API
└── package.json
```

---

Desenvolvido por Lucas Pinto.
