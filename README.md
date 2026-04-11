# Telegram Whisper Bot

Bot Telegram minimale per trascrivere vocali e audio.

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
$env:WHISPER_PROMPT="Paolo, Irene, Ratanà, Copenaghen"
$env:OPENAI_API_KEY="LA_TUA_OPENAI_API_KEY"
$env:OPENAI_MODEL="gpt-4.1"
$env:OPENAI_TRANSCRIPTION_MODEL="gpt-4o-mini-transcribe"
```

5. Avvia il bot:

```powershell
python bot.py
```

## Uso

- manda un vocale al bot
- il bot risponde direttamente con un `Testo pulito`
- se il testo è troppo lungo, ti invia un `.txt`
- se imposti `OPENAI_API_KEY`, il `Testo pulito` viene ricostruito in modo piu sensato a partire dalla trascrizione base
- sotto la risposta trovi due bottoni:
  - `Schema / mappa`: genera una mappa concettuale testuale del contenuto
  - `Riassumi`: genera un riassunto breve del vocale
- trovi anche:
  - `Email`: riscrive il contenuto in stile email pronta da copiare
  - `WhatsApp`: riscrive il contenuto in stile messaggio WhatsApp pronto da copiare

## Note

- la trascrizione audio ora passa da OpenAI, quindi il bot è molto più leggero su Render
- `gpt-4.1` è il default per testo pulito e riscritture: migliore qualità, costo più alto
- `OPENAI_TRANSCRIPTION_MODEL` controlla il modello di trascrizione audio
- `WHISPER_PROMPT` aiuta parecchio con nomi e luoghi difficili
- `OPENAI_API_KEY` abilita la ricostruzione del `Testo pulito`
- OpenAI trascrive l'audio e GPT lo trasforma in testo leggibile e contestualmente piu corretto
- il bot conserva in memoria le ultime trascrizioni per poter usare i bottoni senza reinviare il vocale
