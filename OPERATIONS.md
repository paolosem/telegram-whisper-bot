# Messa Operativa

## Cosa e gia pronto

- Bot Telegram con output:
  - Testo pulito
  - Riassumi
  - Schema / mappa
  - Email
  - WhatsApp
- Accesso controllato con trial e piani
- Landing page statica in `landing/`

## Flusso semplice per vendere

1. Metti online la landing page
2. Metti online il bot
3. Inserisci nella landing:
   - username del bot
   - form per richiesta prova gratuita
4. Imposta nel bot:
   - `BOT_USERNAME`
   - `SALES_URL`
   - `ADMIN_TELEGRAM_IDS`
5. Ricevi lo username Telegram via email
6. Chiedi all'utente di aprire il bot e scrivere `/start`
7. Recuperi il suo `telegram_id` con:
   - `/finduser username`
   - oppure l'utente puo mandarti direttamente `/myid`
8. Attivi utenti via Telegram con:
   - `/granttrial <telegram_id> [giorni]`
   - `/grantpaid <telegram_id> [giorni]`

## Comandi admin

- `/granttrial 123456789 7`
- `/grantpaid 123456789 30`
- `/blockuser 123456789`
- `/finduser username`
- `/plan`

## Variabili ambiente consigliate

```powershell
$env:TELEGRAM_BOT_TOKEN="IL_TUO_TOKEN"
$env:BOT_USERNAME="username_del_bot"
$env:SALES_URL="https://buy.stripe.com/IL_TUO_LINK"
$env:ADMIN_TELEGRAM_IDS="TUO_TELEGRAM_ID"
$env:WHISPER_LANGUAGE="it"
$env:WHISPER_PROMPT="Paolo, Irene, Ratanà, Copenaghen"
$env:OPENAI_API_KEY="LA_TUA_OPENAI_API_KEY"
$env:OPENAI_MODEL="gpt-4.1"
$env:OPENAI_TRANSCRIPTION_MODEL="gpt-4o-mini-transcribe"
```

## Nota pratica

La landing usa `formsubmit.co` per mandarti le richieste prova gratuita via email.
Al primo test del form dovrai confermare l'indirizzo email cliccando il link che FormSubmit ti inviera.

## Nota Render

La trascrizione locale con Whisper consumava troppa RAM sul piano Starter.
Adesso il bot usa OpenAI anche per la trascrizione audio, quindi e molto piu adatto a restare online su Render.
