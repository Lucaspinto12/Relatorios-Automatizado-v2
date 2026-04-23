# Cognos Model Generator — API + Frontend

Interface web e API REST para geração automática do `model.xml` do IBM Cognos Framework Manager.

## Estrutura

```
/
├── api/          ← Backend FastAPI (Python)
├── frontend/     ← Frontend React + TypeScript
└── relatorios/
    ├── CPqD_Antifraude_Relatorios_Suite_Antifraude/   ← Automação Suite
    └── CPqD_Antifraude_Relatorios_Usuario/            ← Automação Usuário
```

---

## 🗂️ Suite Antifraude — `update_model.py`

Script para atualizar o `model.xml` da **Suite Antifraude** ao adicionar um novo evento.
Injeta os trechos de SQL necessários nas tabelas de fato, dashboard e score.

### Configuração

Edite as variáveis no topo do `update_model.py`:

```python
novo_evento  = 'uni_cash_in'   # Nome técnico do evento (ex: pix_internacional)
valor_evento = 'vl_operacao'   # Coluna de valor da view (ou '0' se não houver)
```

### Execução

```bash
cd relatorios/CPqD_Antifraude_Relatorios_Suite_Antifraude
python update_model.py
```

O arquivo `model_atualizado.xml` é gerado na mesma pasta.

### O que é atualizado

| Tabela | O que é injetado |
|---|---|
| `FT_NOT_ALARMED_RULE`, `FT_CASE_MANAGEMENT` | `UNION ALL` com a view do novo evento |
| `FT_EVENT_TODAY`, `FT_EVENT_LAST_24HRS`, `FT_EVENT_LAST_7DAYS` | `UNION ALL` com filtros de data |
| `DIM_SCORE` | Dois blocos de `UNION ALL` (select simples + group by) |

---

## 👤 Relatórios do Usuário — `auto_modeler.py`

Gera o `model.xml` completo da camada de usuário para um novo evento.
Conecta ao Oracle, extrai metadados e gera todas as camadas do Framework Manager.

### Configuração (`.env`)

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
cd relatorios/CPqD_Antifraude_Relatorios_Usuario
pip install -r requirements.txt
python auto_modeler.py
```

### O que é gerado

| Camada | O que é criado |
|---|---|
| **Original Database** | `querySubject` com SQL da view, todos os campos como `attribute` |
| **Star Schema View** | Atalhos `FT_`, `DIM_` e 4 pontes |
| **Relacionamentos** | FT↔Pontes, FT↔DIMs, DIM↔FTs de histórico |
| **Consolidation View** | DIM e Fato com pasta Identificadores |
| **Presentation View** | Namespace `Evento <Nome>` com atalhos padrão |

---

## 🌐 API + Frontend

### Backend (FastAPI)

```bash
cd api
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
# Swagger: http://localhost:8000/docs
```

### Frontend (React)

```bash
cd frontend
npm install
npm run dev
# App: http://localhost:5173
```

### Endpoints

| Método | Endpoint | Descrição |
|---|---|---|
| `GET` | `/` | Health check |
| `POST` | `/modelo/gerar` | Gera XML usando model.xml do servidor |
| `POST` | `/modelo/gerar-com-base` | Gera XML com upload do model.xml base |

---

Desenvolvido por Lucas Pinto.
