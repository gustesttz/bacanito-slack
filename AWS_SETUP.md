# Bacanito — Setup AWS Lambda 🌮

Guia passo a passo pra colocar o Bacanito na AWS.

---

## 📦 Passo 1: Empacotar o código

No terminal, na pasta do projeto:

```bash
cd ~/Projects/bacanito-slack
zip bacanito.zip lambda_function.py
```

---

## 🔧 Passo 2: Criar a função Lambda

1. Acessar **AWS Console** → **Lambda** → **Create function**

2. Configurar:
   - **Function name:** `bacanito-slack`
   - **Runtime:** `Python 3.11`
   - **Architecture:** `arm64` (mais barato) ou `x86_64`

3. Clicar **Create function**

4. Na aba **Code**:
   - Clicar **Upload from** → **.zip file**
   - Selecionar o `bacanito.zip`
   - Clicar **Save**

5. Em **Runtime settings** → **Edit**:
   - **Handler:** `lambda_function.lambda_handler`
   - Clicar **Save**

---

## ⚙️ Passo 3: Configurar variáveis de ambiente

Em **Configuration** → **Environment variables** → **Edit**:

| Key | Value |
|-----|-------|
| `GROQ_API_KEY` | `gsk_...` (sua key do Groq) |
| `SLACK_BOT_TOKEN` | `xoxb-...` (depois da aprovação) |
| `SLACK_SIGNING_SECRET` | `...` (depois da aprovação) |

Por enquanto, só coloca a `GROQ_API_KEY`. As do Slack ficam vazias até aprovar.

---

## ⏱️ Passo 4: Aumentar timeout

Em **Configuration** → **General configuration** → **Edit**:

- **Timeout:** `30 segundos` (Groq pode demorar um pouco)
- **Memory:** `256 MB` (suficiente)

---

## 🌐 Passo 5: Criar API Gateway (Function URL)

Opção mais fácil — **Function URL** (sem criar API Gateway separado):

1. Em **Configuration** → **Function URL** → **Create function URL**

2. Configurar:
   - **Auth type:** `NONE` (o Slack autentica via signature)
   - **CORS:** Não precisa

3. Clicar **Save**

4. **Copiar a URL** gerada (algo como `https://xxxxx.lambda-url.us-east-1.on.aws/`)

---

## ✅ Passo 6: Testar o health check

No navegador ou terminal:

```bash
curl https://xxxxx.lambda-url.us-east-1.on.aws/
```

Deve retornar:
```json
{
  "status": "ok",
  "bot": "Bacanito 🌮",
  "message": "Órale! El bot está funcionando!",
  "llm": "Groq (Llama 3.3 70B)"
}
```

---

## 🔗 Passo 7: Conectar ao Slack (depois da aprovação)

Quando o Slack App for aprovado:

1. No Slack App → **Event Subscriptions** → **Enable Events**

2. **Request URL:** colar a URL do Lambda
   ```
   https://xxxxx.lambda-url.us-east-1.on.aws/
   ```

3. Esperar o ✅ verde (Slack vai verificar)

4. Em **Subscribe to bot events**, adicionar:
   - `app_mention`

5. Salvar e **reinstalar o app** no workspace

6. Voltar na Lambda e adicionar as variáveis:
   - `SLACK_BOT_TOKEN` (de OAuth & Permissions)
   - `SLACK_SIGNING_SECRET` (de Basic Information)

---

## 🎉 Pronto!

Agora quando mencionarem o Bacanito no canal #ops-planejamento-dados, ele vai responder!

---

## 🔍 Troubleshooting

| Problema | Solução |
|----------|---------|
| Slack não verifica URL | Checar se Lambda está pública (Function URL auth = NONE) |
| Bot não responde | Ver logs no CloudWatch (Lambda → Monitor → Logs) |
| Timeout | Aumentar timeout pra 30s |
| Erro de permissão | Verificar se variáveis de ambiente estão corretas |

---

## 💰 Custo estimado

- **Lambda:** ~$0 (free tier = 1M requests/mês)
- **Groq:** $0 (free tier = 30 req/min)
- **Total:** **GRÁTIS** 🎉

---

_Guía creada por Bacanito 🌮_
