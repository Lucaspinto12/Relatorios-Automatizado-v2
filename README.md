# Cognos Model Generator — API + Frontend

Interface web e API REST para geração automática do `model.xml` do IBM Cognos Framework Manager.

## Estrutura

```
/
├── api/          ← Backend FastAPI (Python)
├── frontend/     ← Frontend React + TypeScript
└── relatorios/   ← Automação CLI (Python)
    └── CPqD_Antifraude_Relatorios_Usuario/
```

## Como rodar

### Backend
```bash
cd api
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
# Swagger: http://localhost:8000/docs
```

### Frontend
```bash
cd frontend
npm install
npm run dev
# App: http://localhost:5173
```

### CLI (sem API)
```bash
cd relatorios/CPqD_Antifraude_Relatorios_Usuario
pip install -r requirements.txt
python auto_modeler.py
```

Desenvolvido por Lucas Pinto.
