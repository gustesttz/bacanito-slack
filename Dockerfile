FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

# Instala só Flask (sem gunicorn)
RUN pip install --no-cache-dir flask==3.0.0

# Copia código
COPY app.py .
COPY BACANITO.md .

EXPOSE 8080

CMD ["python", "app.py"]
