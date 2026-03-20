FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Instala só Flask
RUN pip install flask==3.0.0

# App mínimo inline - nem precisa de arquivo
RUN echo 'from flask import Flask\nimport os\napp = Flask(__name__)\n@app.route("/")\ndef health():\n    return "OK"\nif __name__ == "__main__":\n    print("STARTING...", flush=True)\n    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))' > app.py

RUN cat app.py

CMD ["python", "app.py"]
