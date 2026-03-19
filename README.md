# Bacanito 🌮

Slack Bot para Reports do Farol de Processos Operacionais.
Fala portunhol mexicano com saudações aleatórias!

## Deploy no Railway

1. Push este repo pro GitHub
2. Conecte no Railway
3. Configure as env vars:
   - `SLACK_BOT_TOKEN` - Token do bot (xoxb-...)
   - `SLACK_SIGNING_SECRET` - Signing secret do app

## Endpoints

- `GET /` - Health check
- `POST /slack/events` - Eventos do Slack (menções, DMs)
- `POST /slack/commands` - Slash commands (/bacanito)

## Comandos

- `@Bacanito help` - Lista de comandos
- `@Bacanito report` - Gerar report do Farol
- `@Bacanito status` - Status dos jobs
- `/bacanito [comando]` - Slash command

## Env Vars

```
SLACK_BOT_TOKEN=xoxb-...
SLACK_SIGNING_SECRET=...
PORT=3000
```

---

Órale! 🚀
