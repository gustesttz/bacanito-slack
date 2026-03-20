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
# Força Python a não bufferizar stdout/stderr
ENV PYTHONUNBUFFERED=1

EXPOSE 8080

# Gunicorn com preload pra mostrar erros de import + logs no stdout
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 120 --preload --access-logfile - --error-logfile - app:app
