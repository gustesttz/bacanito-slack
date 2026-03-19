"""
Bacanito - Slack Bot para Reports do Farol de Processos Operacionais
Fala portunhol mexicano com saudações aleatórias 🇲🇽🇧🇷
Integrado com Groq (Llama 3) para respostas inteligentes
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
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# Canal autorizado para respostas automáticas
CANAL_AUTORIZADO = "C02V74YSS5U"  # #ops-planejamento-dados

# Personalidade do Bacanito
SYSTEM_PROMPT = """Você é o Bacanito, um bot assistente do time de Operações do PicPay.

PERSONALIDADE:
- Você fala português brasileiro com algumas palavras em espanhol (estilo mexicano/portunhol)
- Use expressões como: "Órale!", "Qué onda!", "Ándale!", "Épale!", "Arriba!", "Bueno!"
- Seja simpático, prestativo e um pouco engraçado
- Use emojis com moderação: 🌮 🚀 👋 😎 📊

CONTEXTO:
- Você ajuda o time com reports do Farol de Processos Operacionais
- Os reports são enviados Seg-Sex no canal #ops-planejamento-dados
- Você pode responder dúvidas sobre processos, jobs do Databricks, monitorias

REGRAS:
- Respostas curtas e diretas (máximo 3-4 linhas, a menos que peçam detalhes)
- Se não souber algo específico, diga que vai verificar
- Nunca invente dados ou números
- Seja profissional mas descontraído

SAUDAÇÕES PARA USAR (varie!):
- "Órale, pessoal! 👋"
- "Qué onda! 😎"  
- "Ándale! 🚀"
- "Épale! 🌮"
- "Buenas buenas!"
"""

# Saudações para respostas rápidas
SAUDACOES = [
    "Órale! 👋",
    "Qué onda! 😎",
    "Ándale! 🚀",
    "Épale! 🌮",
    "Buenas buenas!",
    "Arriba! 🎉"
]


def verify_slack_signature(request):
    """Verifica se a request veio do Slack"""
    if not SLACK_SIGNING_SECRET:
        return True  # Skip em dev
    
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")
    
    if not timestamp or not signature:
        return False
    
    # Evita replay attacks (requests > 5 min)
    try:
        if abs(time.time() - int(timestamp)) > 60 * 5:
            return False
    except:
        return False
    
    sig_basestring = f"v0:{timestamp}:{request.get_data(as_text=True)}"
    my_signature = "v0=" + hmac.new(
        SLACK_SIGNING_SECRET.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(my_signature, signature)


def call_groq(user_message):
    """Chama a API do Groq para gerar resposta"""
    if not GROQ_API_KEY:
        return f"{random.choice(SAUDACOES)} Estou sem conexão com meu cérebro agora, amigo! 🧠❌"
    
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message}
                ],
                "max_tokens": 500,
                "temperature": 0.7
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            return data["choices"][0]["message"]["content"]
        else:
            print(f"Groq error: {response.status_code} - {response.text}")
            return f"{random.choice(SAUDACOES)} Tuve un problemita técnico, intenta de nuevo! 🔧"
    
    except Exception as e:
        print(f"Groq exception: {e}")
        return f"{random.choice(SAUDACOES)} Algo salió mal, amigo! Intenta de nuevo en un momento. 🌮"


def send_slack_message(channel, text, thread_ts=None):
    """Envia mensagem pro Slack"""
    if not SLACK_BOT_TOKEN:
        print(f"Would send to {channel}: {text}")
        return {"ok": False, "error": "no_token"}
    
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


def process_message(text):
    """Processa mensagem e retorna resposta via Groq"""
    # Remove menção do bot
    import re
    clean_text = re.sub(r'<@[A-Z0-9]+>', '', text).strip()
    
    if not clean_text:
        return f"{random.choice(SAUDACOES)} Me chamou? Em que posso ajudar? 🌮"
    
    # Chama o Groq para resposta inteligente
    return call_groq(clean_text)


@app.route("/", methods=["GET"])
def health():
    """Health check"""
    return jsonify({
        "status": "ok",
        "bot": "Bacanito 🌮",
        "message": "Órale! El bot está funcionando!",
        "llm": "Groq (Llama 3.1 70B)" if GROQ_API_KEY else "disabled"
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
        
        # Ignora subtipos (edições, deletes, etc)
        if event.get("subtype"):
            return jsonify({"ok": True})
        
        # Menção ao bot (app_mention)
        if event_type == "app_mention":
            channel = event.get("channel")
            text = event.get("text", "")
            thread_ts = event.get("thread_ts") or event.get("ts")
            user = event.get("user")
            
            print(f"Mention from {user} in {channel}: {text}")
            
            # Só responde automaticamente no canal autorizado
            if channel != CANAL_AUTORIZADO:
                print(f"Ignorando menção em canal não autorizado: {channel}")
                return jsonify({"ok": True})
            
            resposta = process_message(text)
            send_slack_message(channel, resposta, thread_ts)
            
            return jsonify({"ok": True})
        
        # Mensagem direta - DESATIVADO (só responde no canal autorizado)
        if event_type == "message" and event.get("channel_type") == "im":
            print(f"DM ignorada - bot só responde no canal #ops-planejamento-dados")
            return jsonify({"ok": True})
    
    return jsonify({"ok": True})


@app.route("/slack/commands", methods=["POST"])
def slack_commands():
    """Handler para slash commands"""
    
    if not verify_slack_signature(request):
        return jsonify({"error": "Invalid signature"}), 403
    
    command = request.form.get("command")
    text = request.form.get("text", "")
    user_id = request.form.get("user_id")
    
    print(f"Command {command} from {user_id}: {text}")
    
    if command == "/bacanito":
        resposta = process_message(text if text else "help")
        return jsonify({
            "response_type": "in_channel",
            "text": resposta
        })
    
    return jsonify({"ok": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    debug = os.environ.get("DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
