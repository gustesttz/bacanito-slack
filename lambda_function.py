"""
Bacanito - Slack Bot para AWS Lambda
Fala portunhol mexicano com saudações aleatórias 🇲🇽🇧🇷
Integrado com Groq (Llama 3) para respostas inteligentes
"""

import os
import json
import random
import hmac
import hashlib
import time
import re
import urllib.request
import urllib.parse

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


def verify_slack_signature(headers, body):
    """Verifica se a request veio do Slack"""
    if not SLACK_SIGNING_SECRET:
        return True  # Skip em dev
    
    timestamp = headers.get("x-slack-request-timestamp", "")
    signature = headers.get("x-slack-signature", "")
    
    if not timestamp or not signature:
        return False
    
    # Evita replay attacks (requests > 5 min)
    try:
        if abs(time.time() - int(timestamp)) > 60 * 5:
            return False
    except:
        return False
    
    sig_basestring = f"v0:{timestamp}:{body}"
    my_signature = "v0=" + hmac.new(
        SLACK_SIGNING_SECRET.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(my_signature, signature)


def http_request(url, data=None, headers=None):
    """Helper para fazer HTTP requests sem dependências externas"""
    if headers is None:
        headers = {}
    
    if data:
        data = json.dumps(data).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    
    req = urllib.request.Request(url, data=data, headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"HTTP request error: {e}")
        return None


def call_groq(user_message):
    """Chama a API do Groq para gerar resposta"""
    if not GROQ_API_KEY:
        return f"{random.choice(SAUDACOES)} Estou sem conexão com meu cérebro agora, amigo! 🧠❌"
    
    try:
        response = http_request(
            "https://api.groq.com/openai/v1/chat/completions",
            data={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message}
                ],
                "max_tokens": 500,
                "temperature": 0.7
            },
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}"
            }
        )
        
        if response and "choices" in response:
            return response["choices"][0]["message"]["content"]
        else:
            print(f"Groq error: {response}")
            return f"{random.choice(SAUDACOES)} Tuve un problemita técnico, intenta de nuevo! 🔧"
    
    except Exception as e:
        print(f"Groq exception: {e}")
        return f"{random.choice(SAUDACOES)} Algo salió mal, amigo! Intenta de nuevo en un momento. 🌮"


def send_slack_message(channel, text, thread_ts=None):
    """Envia mensagem pro Slack"""
    if not SLACK_BOT_TOKEN:
        print(f"Would send to {channel}: {text}")
        return {"ok": False, "error": "no_token"}
    
    payload = {
        "channel": channel,
        "text": text
    }
    if thread_ts:
        payload["thread_ts"] = thread_ts
    
    response = http_request(
        "https://slack.com/api/chat.postMessage",
        data=payload,
        headers={
            "Authorization": f"Bearer {SLACK_BOT_TOKEN}"
        }
    )
    return response


def process_message(text):
    """Processa mensagem e retorna resposta via Groq"""
    clean_text = re.sub(r'<@[A-Z0-9]+>', '', text).strip()
    
    if not clean_text:
        return f"{random.choice(SAUDACOES)} Me chamou? Em que posso ajudar? 🌮"
    
    return call_groq(clean_text)


def lambda_handler(event, context):
    """Handler principal do Lambda"""
    
    print(f"Event received: {json.dumps(event)}")
    
    # Pega headers (lowercase no API Gateway)
    headers = {k.lower(): v for k, v in event.get("headers", {}).items()}
    
    # Pega body
    body = event.get("body", "{}")
    if event.get("isBase64Encoded"):
        import base64
        body = base64.b64decode(body).decode('utf-8')
    
    # Health check (GET /)
    if event.get("httpMethod") == "GET" or event.get("requestContext", {}).get("http", {}).get("method") == "GET":
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "status": "ok",
                "bot": "Bacanito 🌮",
                "message": "Órale! El bot está funcionando!",
                "llm": "Groq (Llama 3.3 70B)" if GROQ_API_KEY else "disabled"
            })
        }
    
    # Verifica assinatura do Slack
    if not verify_slack_signature(headers, body):
        return {
            "statusCode": 403,
            "body": json.dumps({"error": "Invalid signature"})
        }
    
    # Parse do body
    try:
        data = json.loads(body)
    except:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Invalid JSON"})
        }
    
    # Challenge do Slack (verificação inicial)
    if data.get("type") == "url_verification":
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"challenge": data.get("challenge")})
        }
    
    # Processa eventos
    if data.get("type") == "event_callback":
        event_data = data.get("event", {})
        event_type = event_data.get("type")
        
        # Ignora mensagens do próprio bot
        if event_data.get("bot_id"):
            return {"statusCode": 200, "body": json.dumps({"ok": True})}
        
        # Ignora subtipos (edições, deletes, etc)
        if event_data.get("subtype"):
            return {"statusCode": 200, "body": json.dumps({"ok": True})}
        
        # Menção ao bot (app_mention)
        if event_type == "app_mention":
            channel = event_data.get("channel")
            text = event_data.get("text", "")
            thread_ts = event_data.get("thread_ts") or event_data.get("ts")
            user = event_data.get("user")
            
            print(f"Mention from {user} in {channel}: {text}")
            
            # Só responde no canal autorizado
            if channel != CANAL_AUTORIZADO:
                print(f"Ignorando menção em canal não autorizado: {channel}")
                return {"statusCode": 200, "body": json.dumps({"ok": True})}
            
            resposta = process_message(text)
            send_slack_message(channel, resposta, thread_ts)
            
            return {"statusCode": 200, "body": json.dumps({"ok": True})}
        
        # Mensagem direta - DESATIVADO
        if event_type == "message" and event_data.get("channel_type") == "im":
            print(f"DM ignorada - bot só responde no canal #ops-planejamento-dados")
            return {"statusCode": 200, "body": json.dumps({"ok": True})}
    
    return {"statusCode": 200, "body": json.dumps({"ok": True})}
