# Telegram Whisper Bot

Bot Telegram gratuito per trasformare vocali e audio in testo utile.

## Setup

1. Crea un bot con `@BotFather`
2. Copia il token
3. Installa le dipendenze:

```powershell
pip install -r requirements.txt
```

4. Imposta le variabili d'ambiente:

```powershell
$env:TELEGRAM_BOT_TOKEN="IL_TUO_TOKEN"
$env:WHISPER_LANGUAGE="it"
$env:OPENAI_API_KEY="LA_TUA_OPENAI_API_KEY"
$env:OPENAI_MODEL="gpt-4.1"
$env:OPENAI_TRANSCRIPTION_MODEL="gpt-4o-mini-transcribe"
```

5. Avvia il bot:

```powershell
python bot.py
```

## Uso

- apri il bot su Telegram
- manda un vocale al bot
- il bot risponde direttamente con un `Testo pulito`
- se il testo è troppo lungo, ti invia un `.txt`
- sotto la risposta trovi:
  - `Schema / mappa`
  - `Riassumi`
  - `Email`
  - `WhatsApp`

## Note

- la trascrizione audio ora passa da OpenAI, quindi il bot è molto più leggero su Render
- `gpt-4.1` è il default per testo pulito e riscritture: migliore qualità, costo più alto
- `OPENAI_TRANSCRIPTION_MODEL` controlla il modello di trascrizione audio
- `OPENAI_API_KEY` abilita la ricostruzione del `Testo pulito`
- OpenAI trascrive l'audio e GPT lo trasforma in testo leggibile e contestualmente piu corretto
- il bot conserva in memoria le ultime trascrizioni per poter usare i bottoni senza reinviare il vocale
- il bot e pensato per essere condiviso liberamente con chi ne ha bisogno
