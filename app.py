"""
Bacanitro - Slack Bot para Railway
Fala portunhol mexicano com saudações aleatórias 🇲🇽🇧🇷⚡
Integrado com Groq (Llama 3) para respostas inteligentes
Time: Dados e Planejamento
"""

import os
import sys

# Força unbuffered output imediatamente
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

print("🚀 [STARTUP] Bacanitro iniciando imports...", flush=True)

import json
import random
import hmac
import hashlib
import time
import re
import urllib.request
import urllib.error
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

print("🚀 [STARTUP] Imports básicos OK", flush=True)

from flask import Flask, request, jsonify

print("✅ Flask importado", flush=True)

app = Flask(__name__)

print("✅ App Flask criado", flush=True)

# Configurações via env vars (strip remove espaços/newlines acidentais)
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "").strip()
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET", "").strip()
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()

# Debug: mostra primeiros/últimos chars da key pra validar
if GROQ_API_KEY:
    print(f"🔑 GROQ_API_KEY: {GROQ_API_KEY[:8]}...{GROQ_API_KEY[-4:]} (len={len(GROQ_API_KEY)})", flush=True)
else:
    print("⚠️ GROQ_API_KEY não configurada!", flush=True)

# Canal autorizado para respostas automáticas
CANAL_AUTORIZADO = "C02V74YSS5U"  # #ops-planejamento-dados

# Carrega o manual do Bacanitro como system prompt
def load_system_prompt():
    try:
        with open("BACANITO.md", "r", encoding="utf-8") as f:
            manual = f.read()
        return f"""Você é o Bacanitro. Siga as instruções do seu manual:

{manual}

IMPORTANTE: Responda sempre em português com toques de espanhol mexicano (portunhol).
"""
    except:
        return """Você é o Bacanitro, um bot assistente do time de Dados e Planejamento do PicPay.
Fala portunhol (português + espanhol mexicano). Seja simpático e direto."""

SYSTEM_PROMPT = load_system_prompt()

print(f"✅ System prompt carregado ({len(SYSTEM_PROMPT)} chars)", flush=True)

# Saudações APENAS para fallback em caso de erro técnico
SAUDACOES_FALLBACK = [
    "Órale! 👋",
    "Qué onda! 😎",
    "Ándale! 🚀",
    "Épale! 🌮",
    "Buenas buenas!",
    "Arriba! 🎉",
    "Hola hola! 🌵",
    "Qué tal! 🎊",
    "Ey ey ey! 🔥",
    "Bueno pues! 🌮"
]

# Memória de conversas por canal (últimas 10 mensagens)
# Estrutura: {channel_id: [(role, content), ...]}
channel_memory = {}

# Inicializa o scheduler (vai ser configurado depois das funções)
scheduler = None


def verify_slack_signature(req):
    """Verifica se a request veio do Slack"""
    if not SLACK_SIGNING_SECRET:
        return True  # Skip em dev
    
    timestamp = req.headers.get("X-Slack-Request-Timestamp", "")
    signature = req.headers.get("X-Slack-Signature", "")
    body = req.get_data(as_text=True)
    
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
    except urllib.error.HTTPError as e:
        # Captura o body do erro HTTP pra melhor debug
        error_body = ""
        try:
            error_body = e.read().decode('utf-8')
        except:
            pass
        print(f"❌ HTTP {e.code} Error: {e.reason}", flush=True)
        print(f"❌ Error body: {error_body}", flush=True)
        return None
    except Exception as e:
        print(f"❌ HTTP request error: {e}", flush=True)
        return None


def call_groq(user_message, channel_id=None):
    """Chama a API do Groq para gerar resposta com contexto de histórico"""
    print(f"[GROQ] Chamando com mensagem: {user_message[:100]}...", flush=True)
    print(f"[GROQ] API Key presente: {bool(GROQ_API_KEY)}", flush=True)
    
    if not GROQ_API_KEY:
        return f"{random.choice(SAUDACOES_FALLBACK)} Estou sem conexão com meu cérebro agora, amigo! 🧠❌"
    
    try:
        # Limita o system prompt pra evitar timeout
        system_prompt = SYSTEM_PROMPT[:4000] if len(SYSTEM_PROMPT) > 4000 else SYSTEM_PROMPT
        print(f"[GROQ] System prompt: {len(system_prompt)} chars", flush=True)
        
        # Monta mensagens com histórico do canal
        messages = [{"role": "system", "content": system_prompt}]
        
        # Adiciona histórico se disponível
        if channel_id and channel_id in channel_memory:
            history = channel_memory[channel_id]
            print(f"[GROQ] Incluindo {len(history)} mensagens do histórico", flush=True)
            messages.extend([{"role": role, "content": content} for role, content in history])
        
        # Adiciona mensagem atual
        messages.append({"role": "user", "content": user_message})
        
        response = http_request(
            "https://api.groq.com/openai/v1/chat/completions",
            data={
                "model": "llama-3.3-70b-versatile",
                "messages": messages,
                "max_tokens": 500,
                "temperature": 0.7
            },
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "User-Agent": "Bacanitro/1.0",
                "Accept": "application/json"
            }
        )
        
        print(f"[GROQ] Response: {response}", flush=True)
        
        if response and "choices" in response:
            bot_response = response["choices"][0]["message"]["content"]
            
            # Salva no histórico (user + bot)
            if channel_id:
                if channel_id not in channel_memory:
                    channel_memory[channel_id] = []
                
                channel_memory[channel_id].append(("user", user_message))
                channel_memory[channel_id].append(("assistant", bot_response))
                
                # Mantém apenas últimas 10 mensagens (5 pares user+bot)
                if len(channel_memory[channel_id]) > 10:
                    channel_memory[channel_id] = channel_memory[channel_id][-10:]
                
                print(f"[MEMORY] Canal {channel_id}: {len(channel_memory[channel_id])} mensagens salvas", flush=True)
            
            return bot_response
        else:
            print(f"[GROQ] Error - response inválido: {response}", flush=True)
            return f"{random.choice(SAUDACOES_FALLBACK)} Tuve un problemita técnico, intenta de nuevo! 🔧"
    
    except Exception as e:
        print(f"[GROQ] Exception: {e}", flush=True)
        return f"{random.choice(SAUDACOES_FALLBACK)} Algo salió mal, amigo! Intenta de nuevo en un momento. 🌮"


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


def process_message(text, channel_id=None):
    """Processa mensagem e retorna resposta via Groq"""
    clean_text = re.sub(r'<@[A-Z0-9]+>', '', text).strip()
    
    # Se só mencionou sem texto, deixa o Groq criar uma saudação criativa
    if not clean_text:
        clean_text = "Me chamou sem dizer nada. Cumprimente de forma criativa e pergunte como pode ajudar!"
    
    # SEMPRE adiciona contexto de data (pra qualquer pergunta sobre data ou report)
    hoje = datetime.now()
    data_hoje = hoje.strftime("%d/%m/%Y")
    dia_semana = hoje.strftime("%A")
    
    # Tradução dos dias da semana
    dias_pt = {
        "Monday": "segunda-feira",
        "Tuesday": "terça-feira",
        "Wednesday": "quarta-feira",
        "Thursday": "quinta-feira",
        "Friday": "sexta-feira",
        "Saturday": "sábado",
        "Sunday": "domingo"
    }
    dia_semana_pt = dias_pt.get(dia_semana, dia_semana)
    
    # Adiciona contexto de data no prompt
    contexto_extra = ""
    if "report" in clean_text.lower():
        contexto_extra = "\n\nIMPORTANTE: Use a data de hoje como dia de registro automaticamente. Não pergunte a data ao usuário."
    
    clean_text = f"""CONTEXTO AUTOMÁTICO:
- Data de hoje: {data_hoje}
- Dia da semana: {dia_semana_pt}
- É terça-feira: {'sim' if dia_semana == 'Tuesday' else 'não'}{contexto_extra}

MENSAGEM DO USUÁRIO:
{clean_text}"""
    
    return call_groq(clean_text, channel_id)


@app.route("/", methods=["GET"])
def health():
    """Health check endpoint"""
    jobs = []
    if scheduler and scheduler.running:
        jobs = [{"id": job.id, "next_run": str(job.next_run_time)} for job in scheduler.get_jobs()]
    
    return jsonify({
        "status": "ok",
        "bot": "Bacanito 🌮",
        "message": "Órale! El bot está funcionando!",
        "llm": "Groq (Llama 3.3 70B)" if GROQ_API_KEY else "disabled",
        "scheduler_running": scheduler.running if scheduler else False,
        "scheduled_jobs": jobs,
        "current_time_brasilia": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })


@app.route("/test-lembrete", methods=["POST"])
def test_lembrete():
    """Endpoint pra testar lembrete manualmente"""
    try:
        lembrete_agua()
        return jsonify({"status": "ok", "message": "Lembrete enviado!"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/trigger-lembrete-agua", methods=["POST", "GET"])
def trigger_lembrete_agua():
    """Trigger manual de lembrete de água (GET ou POST)"""
    try:
        lembrete_agua()
        return jsonify({
            "status": "ok",
            "message": "💧 Lembrete de água enviado com sucesso!",
            "channel": CANAL_AUTORIZADO,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/slack/events", methods=["POST"])
def slack_events():
    """Endpoint para eventos do Slack"""
    
    # Verifica assinatura
    if not verify_slack_signature(request):
        return jsonify({"error": "Invalid signature"}), 403
    
    data = request.json
    print(f"Event received: {json.dumps(data)}")
    
    # Challenge do Slack (verificação inicial)
    if data.get("type") == "url_verification":
        return jsonify({"challenge": data.get("challenge")})
    
    # Processa eventos
    if data.get("type") == "event_callback":
        event_data = data.get("event", {})
        event_type = event_data.get("type")
        
        # Ignora mensagens do próprio bot
        if event_data.get("bot_id"):
            return jsonify({"ok": True})
        
        # Ignora subtipos (edições, deletes, etc)
        if event_data.get("subtype"):
            return jsonify({"ok": True})
        
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
                return jsonify({"ok": True})
            
            resposta = process_message(text, channel_id=channel)
            send_slack_message(channel, resposta, thread_ts)
            
            return jsonify({"ok": True})
        
        # Mensagem direta - DESATIVADO
        if event_type == "message" and event_data.get("channel_type") == "im":
            print(f"DM ignorada - bot só responde no canal #ops-planejamento-dados")
            return jsonify({"ok": True})
    
    return jsonify({"ok": True})


# ===== LEMBRETES AUTOMÁTICOS =====

# Mensagens de lembrete de água (variadas pra não enjoar)
LEMBRETES_AGUA = [
    "💧 ¡Hora de beber água, mi gente! Hidratação é vida! 🌊",
    "🚰 Órale, equipo! Pausa pra tomar aquela água fresca. ¡Salud! 💙",
    "💦 Lembrete automático: Beba água agora! Seu corpo agradece. 🙏",
    "🌊 ¡Ey ey ey! Hora de hidratar. Toma água, parceiro! 💧",
    "💧 Pausa estratégica: Água no copo, saúde no corpo! 🎯",
    "🚰 ¡Arriba! Levanta, toma água e volta renovado! 💪💧",
    "💦 Lembrete de saúde: H2O é essencial. Beba agora! 🌟",
    "🌊 ¡Qué tal! Hora de dar aquele gole de água. Vai lá! 🚀"
]

def lembrete_agua():
    """Envia lembrete automático de tomar água"""
    try:
        mensagem = random.choice(LEMBRETES_AGUA)
        send_slack_message(CANAL_AUTORIZADO, mensagem)
        print(f"[LEMBRETE] Água enviado às {datetime.now().strftime('%H:%M')}", flush=True)
    except Exception as e:
        print(f"[LEMBRETE] Erro ao enviar: {e}", flush=True)


# TODO: Scheduler desabilitado temporariamente (causava falha no healthcheck)
# Para enviar lembretes, use: POST /trigger-lembrete-agua
#
# # Inicializa o scheduler
# scheduler = BackgroundScheduler(timezone="America/Sao_Paulo")
# 
# # Lembretes de água: 10h10 e 15h (seg a sex)
# scheduler.add_job(
#     lembrete_agua,
#     CronTrigger(hour=10, minute=10, day_of_week='mon-fri'),
#     id='lembrete_agua_10h10'
# )
# scheduler.add_job(
#     lembrete_agua,
#     CronTrigger(hour=15, minute=0, day_of_week='mon-fri'),
#     id='lembrete_agua_15h'
# )
# 
# scheduler.start()
# print("✅ Scheduler iniciado - Lembretes de água às 10h10 e 15h", flush=True)

# ===== FIM LEMBRETES =====


print("✅ Rotas registradas", flush=True)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"🌮 Bacanitro rodando na porta {port}", flush=True)
    app.run(host="0.0.0.0", port=port, debug=True)
