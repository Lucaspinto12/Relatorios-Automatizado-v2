FROM python:3.11-slim

WORKDIR /app

# Instalar dependências da API
COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código da API
COPY api/ .

# Copiar automação (importada pelo gerador.py)
COPY CPqD_Antifraude_Relatorios_Usuario/ /automacao/

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
