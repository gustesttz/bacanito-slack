FROM python:3.11-slim

WORKDIR /app

# Instala dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia código e manual
COPY app.py .
COPY BACANITO.md .

# Railway usa PORT env var
ENV PORT=8080
EXPOSE 8080

# Gunicorn pra produção
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app
