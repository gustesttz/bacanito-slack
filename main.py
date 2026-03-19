"""
Bacanito - Slack Bot para Reports do Farol de Processos Operacionais
Fala portunhol mexicano com saudações aleatórias 🇲🇽🇧🇷
"""

import os
import json
import random
import hmac
import hashlib
import time
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# Configurações via env vars
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET")

# Saudações mexicanas do Bacanito
SAUDACOES = [
    "Órale, pessoal! 👋",
    "Ándale, mi gente! 🚀",
    "Qué onda, galera! 😎",
    "Buenos días, parceiros! ☀️",
    "Hola hola, time! 👊",
    "Épale, pessoal! 🙌",
    "Qué tal, galera! ✌️",
    "Buenas buenas, mi gente! 🌮",
    "Ey ey ey, chegou o Bacanito! 📊",
    "Arriba arriba, pessoal! 🎉"
]

# Respostas do Bacanito
RESPOSTAS = {
    "oi": "Órale! 👋 Em que posso ajudar, amigo?",
    "ajuda": """Qué onda! Soy el Bacanito 🌮

Posso te ajudar com:
• `@Bacanito report` - Gerar report do Farol
• `@Bacanito status` - Ver status dos jobs
• `@Bacanito help` - Esta mensagem

Cualquier cosa, me chama! 😎""",
    "help": """Qué onda! Soy el Bacanito 🌮

Posso te ajudar com:
• `@Bacanito report` - Gerar report do Farol
• `@Bacanito status` - Ver status dos jobs
• `@Bacanito help` - Esta mensagem

Cualquier cosa, me chama! 😎""",
    "status": "Épale! 📊 Los jobs están configurados pra rodar Seg-Sex. Tudo tranquilo por aqui, parceiro!",
    "report": "Ándale! 📋 Vou preparar o report... Un momento, por favor!"
}


def verify_slack_signature(request):
    """Verifica se a request veio do Slack"""
    if not SLACK_SIGNING_SECRET:
        return True  # Skip em dev
    
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")
    
    # Evita replay attacks (requests > 5 min)
    if abs(time.time() - int(timestamp)) > 60 * 5:
        return False
    
    sig_basestring = f"v0:{timestamp}:{request.get_data(as_text=True)}"
    my_signature = "v0=" + hmac.new(
        SLACK_SIGNING_SECRET.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(my_signature, signature)


def send_slack_message(channel, text, thread_ts=None):
    """Envia mensagem pro Slack"""
    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "channel": channel,
        "text": text
    }
    if thread_ts:
        payload["thread_ts"] = thread_ts
    
    response = requests.post(
        "https://slack.com/api/chat.postMessage",
        headers=headers,
        json=payload
    )
    return response.json()


def get_resposta(texto):
    """Processa o texto e retorna resposta apropriada"""
    texto_lower = texto.lower()
    
    # Remove menção do bot
    texto_clean = texto_lower.replace("<@", "").split(">")[-1].strip()
    
    # Procura keywords
    for keyword, resposta in RESPOSTAS.items():
        if keyword in texto_clean:
            return resposta
    
    # Resposta padrão com saudação aleatória
    saudacao = random.choice(SAUDACOES)
    return f"{saudacao}\n\nNo entendí muy bien, amigo. Tenta `@Bacanito help` pra ver o que posso fazer! 🌮"


@app.route("/", methods=["GET"])
def health():
    """Health check"""
    return jsonify({
        "status": "ok",
        "bot": "Bacanito 🌮",
        "message": "Órale! El bot está funcionando!"
    })


@app.route("/slack/events", methods=["POST"])
def slack_events():
    """Handler para eventos do Slack"""
    
    # Verifica assinatura
    if not verify_slack_signature(request):
        return jsonify({"error": "Invalid signature"}), 403
    
    data = request.json
    
    # Challenge do Slack (verificação inicial)
    if data.get("type") == "url_verification":
        return jsonify({"challenge": data.get("challenge")})
    
    # Processa eventos
    if data.get("type") == "event_callback":
        event = data.get("event", {})
        event_type = event.get("type")
        
        # Ignora mensagens do próprio bot
        if event.get("bot_id"):
            return jsonify({"ok": True})
        
        # Menção ao bot (app_mention)
        if event_type == "app_mention":
            channel = event.get("channel")
            text = event.get("text", "")
            thread_ts = event.get("thread_ts") or event.get("ts")
            
            resposta = get_resposta(text)
            send_slack_message(channel, resposta, thread_ts)
            
            return jsonify({"ok": True})
        
        # Mensagem direta
        if event_type == "message" and event.get("channel_type") == "im":
            channel = event.get("channel")
            text = event.get("text", "")
            thread_ts = event.get("ts")
            
            resposta = get_resposta(text)
            send_slack_message(channel, resposta)
            
            return jsonify({"ok": True})
    
    return jsonify({"ok": True})


@app.route("/slack/commands", methods=["POST"])
def slack_commands():
    """Handler para slash commands"""
    
    if not verify_slack_signature(request):
        return jsonify({"error": "Invalid signature"}), 403
    
    command = request.form.get("command")
    text = request.form.get("text", "")
    channel_id = request.form.get("channel_id")
    
    if command == "/bacanito":
        if "report" in text.lower():
            return jsonify({
                "response_type": "in_channel",
                "text": "Ándale! 📋 Preparando el report del Farol..."
            })
        elif "help" in text.lower():
            return jsonify({
                "response_type": "ephemeral",
                "text": RESPOSTAS["help"]
            })
        else:
            saudacao = random.choice(SAUDACOES)
            return jsonify({
                "response_type": "ephemeral",
                "text": f"{saudacao}\n\nUsa `/bacanito help` pra ver os comandos!"
            })
    
    return jsonify({"ok": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port, debug=True)
