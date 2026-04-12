# Messa Operativa

## Cosa e gia pronto

- Bot Telegram con output:
  - Testo pulito
  - Riassumi
  - Schema / mappa
  - Email
  - WhatsApp
- Bot gratuito e aperto
- Landing page statica in `landing/`

## Flusso semplice

1. Metti online la landing page
2. Metti online il bot
3. Nella landing inserisci solo il link al bot
4. L'utente apre il bot e lo usa subito

## Comandi disponibili

- `/start`
- `/myid`
- `/plan`

## Variabili ambiente consigliate

```powershell
$env:TELEGRAM_BOT_TOKEN="IL_TUO_TOKEN"
$env:BOT_USERNAME="username_del_bot"
$env:WHISPER_LANGUAGE="it"
$env:WHISPER_PROMPT="Paolo, Irene, Ratanà, Copenaghen"
$env:OPENAI_API_KEY="LA_TUA_OPENAI_API_KEY"
$env:OPENAI_MODEL="gpt-4.1"
$env:OPENAI_TRANSCRIPTION_MODEL="gpt-4o-mini-transcribe"
```

## Nota Render

La trascrizione locale con Whisper consumava troppa RAM sul piano Starter.
Adesso il bot usa OpenAI anche per la trascrizione audio, quindi e molto piu adatto a restare online su Render.
