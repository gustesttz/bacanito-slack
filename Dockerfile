FROM python:3.11-slim

WORKDIR /app

# Força Python a não bufferizar stdout/stderr
ENV PYTHONUNBUFFERED=1

# Instala dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia código e manual
COPY app.py .
COPY BACANITO.md .

# Railway injeta PORT como env var
EXPOSE 8080

# Usar Python direto pra debug (Flask dev server)
CMD python app.py
