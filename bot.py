from __future__ import annotations

import logging
import os
import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import httpx
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters


logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
LANGUAGE = os.getenv("WHISPER_LANGUAGE", "it")
INITIAL_PROMPT = os.getenv("WHISPER_PROMPT", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1")
OPENAI_TRANSCRIPTION_MODEL = os.getenv("OPENAI_TRANSCRIPTION_MODEL", "gpt-4o-mini-transcribe")
BOT_USERNAME = os.getenv("BOT_USERNAME", "")
ADMIN_IDS = {
    int(value.strip())
    for value in os.getenv("ADMIN_TELEGRAM_IDS", "").split(",")
    if value.strip()
}
DATA_DIR = Path(__file__).resolve().parent / "data"
USERS_FILE = DATA_DIR / "users.json"

transcript_store: dict[str, dict[str, str]] = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if message is None or update.effective_user is None:
        return

    ensure_user_record(update.effective_user)

    text = (
        "Mandami un vocale o un audio e lo trasformo in testo utile.\n\n"
        "Comandi utili:\n"
        "/start - mostra questo messaggio\n"
        "/myid - mostra il tuo Telegram ID\n"
        "/ping - verifica che il bot sia vivo\n\n"
        "Dopo la trascrizione puoi anche premere:\n"
        "- Schema / mappa concettuale\n"
        "- Riassumi\n"
        "- Email\n"
        "- WhatsApp"
    )
    await message.reply_text(text)


async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Bot attivo.")


async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if message is None or update.effective_user is None:
        return

    ensure_user_record(update.effective_user)
    username = f"@{update.effective_user.username}" if update.effective_user.username else "nessuno"
    await message.reply_text(
        f"Il tuo Telegram ID e: {update.effective_user.id}\nUsername: {username}"
    )


async def plan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if message is None or update.effective_user is None:
        return

    ensure_user_record(update.effective_user)
    await message.reply_text(
        "Il bot e attualmente gratuito. Mandami un vocale e ti restituisco testo pulito, riassunto, schema, email o messaggio WhatsApp pronto.",
    )


async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if message is None or update.effective_user is None:
        return

    ensure_user_record(update.effective_user)

    audio_obj = message.voice or message.audio or message.document
    if audio_obj is None:
        await message.reply_text("Mandami un vocale, un audio o un file audio.")
        return

    await context.bot.send_chat_action(chat_id=message.chat_id, action=ChatAction.TYPING)
    waiting = await message.reply_text("Sto trascrivendo...")

    suffix = _guess_suffix(audio_obj, message)

    with tempfile.TemporaryDirectory() as temp_dir:
        input_path = Path(temp_dir) / f"input{suffix}"
        telegram_file = await context.bot.get_file(audio_obj.file_id)
        await telegram_file.download_to_drive(custom_path=str(input_path))

        try:
            text, detected = await transcribe_audio(input_path)
        except Exception as exc:
            logger.exception("Transcription failed")
            await waiting.edit_text(f"Errore durante la trascrizione: {exc}")
            return

    if not text:
        text = "[Nessun testo riconosciuto]"

    cleaned_text = text
    if OPENAI_API_KEY and text != "[Nessun testo riconosciuto]":
        try:
            await waiting.edit_text("Trascrizione pronta. Sto preparando il testo pulito...")
            cleaned_text = await build_clean_text(text, detected)
        except Exception as exc:
            logger.exception("Correction failed")
            await message.reply_text(f"Nota: correzione AI non riuscita, uso la trascrizione base. ({exc})")

    transcript_id = save_transcript(raw_text=text, cleaned_text=cleaned_text, detected_language=detected)
    response = build_transcript_message(detected, cleaned_text)
    reply_markup = build_actions_markup(transcript_id)

    if len(response) <= 4000:
        await waiting.edit_text(response, reply_markup=reply_markup)
        return

    preview = build_transcript_message(detected, cleaned_text[:3200].rstrip() + "\n\n[Testo accorciato nell'anteprima]")
    await waiting.edit_text(preview, reply_markup=reply_markup)
    with tempfile.TemporaryDirectory() as temp_dir:
        output_path = Path(temp_dir) / "trascrizione.txt"
        output_path.write_text(cleaned_text, encoding="utf-8")
        await message.reply_document(document=output_path.open("rb"), filename="trascrizione.txt")


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None or query.data is None or update.effective_user is None:
        return

    ensure_user_record(update.effective_user)

    await query.answer()

    action, transcript_id = query.data.split(":", 1)
    transcript = transcript_store.get(transcript_id)
    if transcript is None:
        await query.edit_message_text("Questa trascrizione non e piu disponibile. Rimandami il vocale.")
        return

    if action == "map":
        if not OPENAI_API_KEY:
            await query.answer("Schema AI non configurato.", show_alert=True)
            return

        await query.edit_message_text("Sto preparando lo schema...", reply_markup=build_actions_markup(transcript_id))
        concept_map = await build_concept_map(transcript["cleaned_text"], transcript["detected_language"])
        message = (
            f"Lingua rilevata: {transcript['detected_language']}\n\n"
            f"Schema / mappa concettuale:\n{concept_map}"
        )
        if len(message) > 4000:
            message = "Schema troppo lungo per il messaggio: te lo mando come file."
            await query.edit_message_text(message, reply_markup=build_actions_markup(transcript_id))
            with tempfile.TemporaryDirectory() as temp_dir:
                output_path = Path(temp_dir) / "schema.txt"
                output_path.write_text(concept_map, encoding="utf-8")
                await query.message.reply_document(document=output_path.open("rb"), filename="schema.txt")
            return

        await query.edit_message_text(message, reply_markup=build_actions_markup(transcript_id))
        return

    if action == "summary":
        if not OPENAI_API_KEY:
            await query.answer("Riassunto AI non configurato.", show_alert=True)
            return

        await query.edit_message_text("Sto preparando il riassunto...", reply_markup=build_actions_markup(transcript_id))
        summary = await summarize_transcription(transcript["cleaned_text"], transcript["detected_language"])
        message = (
            f"Lingua rilevata: {transcript['detected_language']}\n\n"
            f"Riassunto:\n{summary}\n\n"
            f"Testo pulito:\n{transcript['cleaned_text']}"
        )
        if len(message) > 4000:
            message = (
                f"Lingua rilevata: {transcript['detected_language']}\n\n"
                f"Riassunto:\n{summary}\n\n"
                "Testo corretto troppo lungo per il messaggio: lo trovi nel file gia inviato o puoi rimandare il vocale."
            )
        await query.edit_message_text(message, reply_markup=build_actions_markup(transcript_id))
        return

    if action == "email":
        if not OPENAI_API_KEY:
            await query.answer("Output Email non configurato.", show_alert=True)
            return

        await query.edit_message_text("Sto preparando il testo in stile email...", reply_markup=build_actions_markup(transcript_id))
        email_text = await rewrite_as_email(transcript["cleaned_text"], transcript["detected_language"])
        message = (
            f"Lingua rilevata: {transcript['detected_language']}\n\n"
            f"Versione Email:\n{email_text}"
        )
        if len(message) > 4000:
            message = "Versione Email troppo lunga per il messaggio: te la mando come file."
            await query.edit_message_text(message, reply_markup=build_actions_markup(transcript_id))
            with tempfile.TemporaryDirectory() as temp_dir:
                output_path = Path(temp_dir) / "email.txt"
                output_path.write_text(email_text, encoding="utf-8")
                await query.message.reply_document(document=output_path.open("rb"), filename="email.txt")
            return

        await query.edit_message_text(message, reply_markup=build_actions_markup(transcript_id))
        return

    if action == "whatsapp":
        if not OPENAI_API_KEY:
            await query.answer("Output WhatsApp non configurato.", show_alert=True)
            return

        await query.edit_message_text("Sto preparando il testo in stile WhatsApp...", reply_markup=build_actions_markup(transcript_id))
        whatsapp_text = await rewrite_as_whatsapp(transcript["cleaned_text"], transcript["detected_language"])
        message = (
            f"Lingua rilevata: {transcript['detected_language']}\n\n"
            f"Versione WhatsApp:\n{whatsapp_text}"
        )
        if len(message) > 4000:
            message = "Versione WhatsApp troppo lunga per il messaggio: te la mando come file."
            await query.edit_message_text(message, reply_markup=build_actions_markup(transcript_id))
            with tempfile.TemporaryDirectory() as temp_dir:
                output_path = Path(temp_dir) / "whatsapp.txt"
                output_path.write_text(whatsapp_text, encoding="utf-8")
                await query.message.reply_document(document=output_path.open("rb"), filename="whatsapp.txt")
            return

        await query.edit_message_text(message, reply_markup=build_actions_markup(transcript_id))
        return


async def build_clean_text(text: str, detected_language: str) -> str:
    system_prompt = (
        "Ricevi una trascrizione audio imperfetta e devi trasformarla in un testo pulito, naturale e sensato. "
        "Correggi errori evidenti di riconoscimento, parole storpiate, abbreviazioni, punteggiatura e nomi propri plausibili nel contesto. "
        "Usa il contesto per ricostruire la parola piu probabile quando l'errore e evidente. "
        "Non inventare fatti nuovi e non riassumere. Restituisci solo il testo finale pulito."
    )

    user_prompt = (
        f"Lingua rilevata: {detected_language}\n"
        f"Prompt di contesto: {INITIAL_PROMPT or 'nessuno'}\n\n"
        "Trascrizione da ripulire:\n"
        f"{text}"
    )

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0,
    }

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

    content = data["choices"][0]["message"]["content"].strip()
    return content or text


async def transcribe_audio(file_path: Path) -> tuple[str, str]:
    if not OPENAI_API_KEY:
        raise RuntimeError("Manca OPENAI_API_KEY: senza questa chiave non posso trascrivere l'audio online.")

    form_data = {
        "model": OPENAI_TRANSCRIPTION_MODEL,
    }

    if LANGUAGE != "auto":
        form_data["language"] = LANGUAGE

    if INITIAL_PROMPT:
        form_data["prompt"] = INITIAL_PROMPT

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
    }

    with file_path.open("rb") as audio_file:
        files = {
            "file": (file_path.name, audio_file, "application/octet-stream"),
        }
        async with httpx.AsyncClient(timeout=180) as client:
            response = await client.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers=headers,
                data=form_data,
                files=files,
            )
            response.raise_for_status()
            data = response.json()

    text = (data.get("text") or "").strip()
    detected = data.get("language") or LANGUAGE or "sconosciuta"
    return text, detected


async def build_concept_map(text: str, detected_language: str) -> str:
    system_prompt = (
        "Trasforma il contenuto in uno schema chiaro o mappa concettuale testuale. "
        "Usa una struttura gerarchica pulita, con titolo breve e punti rientrati. "
        "Evidenzia concetti principali, sottopunti, decisioni, date, persone e prossimi step se presenti. "
        "Non inventare nulla. Restituisci solo lo schema."
    )
    return await call_openai_text(system_prompt, text, detected_language)


async def summarize_transcription(text: str, detected_language: str) -> str:
    system_prompt = (
        "Riassumi un messaggio vocale in italiano in modo molto chiaro e breve. "
        "Massimo 5 punti brevi oppure 1 paragrafo corto se ha piu senso. "
        "Non inventare nulla."
    )
    return await call_openai_text(system_prompt, text, detected_language)


async def rewrite_as_email(text: str, detected_language: str) -> str:
    system_prompt = (
        "Trasforma il contenuto di un vocale in una email chiara, naturale e pronta da inviare. "
        "Mantieni il significato, struttura bene il testo, aggiungi un oggetto sintetico all'inizio come 'Oggetto: ...'. "
        "Non inventare informazioni."
    )
    return await call_openai_text(system_prompt, text, detected_language)


async def rewrite_as_whatsapp(text: str, detected_language: str) -> str:
    system_prompt = (
        "Trasforma il contenuto di un vocale in un messaggio WhatsApp chiaro, breve e naturale. "
        "Tono colloquiale ma ordinato. "
        "Mantieni il significato, non inventare informazioni, evita formalismi da email."
    )
    return await call_openai_text(system_prompt, text, detected_language)


async def call_openai_text(system_prompt: str, text: str, detected_language: str) -> str:
    user_prompt = (
        f"Lingua rilevata: {detected_language}\n"
        f"Prompt di contesto: {INITIAL_PROMPT or 'nessuno'}\n\n"
        f"Testo da elaborare:\n{text}"
    )

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0,
    }

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

    content = data["choices"][0]["message"]["content"].strip()
    return content or text


def save_transcript(raw_text: str, cleaned_text: str, detected_language: str) -> str:
    transcript_id = uuid4().hex[:12]
    transcript_store[transcript_id] = {
        "raw_text": raw_text,
        "cleaned_text": cleaned_text,
        "detected_language": detected_language,
    }
    return transcript_id


def build_actions_markup(transcript_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Schema / mappa", callback_data=f"map:{transcript_id}"),
            ],
            [
                InlineKeyboardButton("Riassumi", callback_data=f"summary:{transcript_id}"),
                InlineKeyboardButton("Email", callback_data=f"email:{transcript_id}"),
            ],
            [
                InlineKeyboardButton("WhatsApp", callback_data=f"whatsapp:{transcript_id}"),
            ],
        ]
    )


def build_transcript_message(detected_language: str, text: str) -> str:
    return f"Lingua rilevata: {detected_language}\n\nTesto pulito:\n{text}"


def ensure_user_record(user) -> dict[str, str | None]:
    users = load_users()
    key = str(user.id)
    record = users.get(key)
    if record is None:
        record = {
            "id": user.id,
            "username": user.username or "",
            "first_name": user.first_name or "",
            "tier": "free",
            "expires_at": None,
        }
        users[key] = record
        save_users(users)
        return record

    updated = False
    if record.get("username") != (user.username or ""):
        record["username"] = user.username or ""
        updated = True
    if record.get("first_name") != (user.first_name or ""):
        record["first_name"] = user.first_name or ""
        updated = True
    if updated:
        users[key] = record
        save_users(users)
    return record


def load_users() -> dict[str, dict[str, str | None]]:
    DATA_DIR.mkdir(exist_ok=True)
    if not USERS_FILE.exists():
        return {}
    return json.loads(USERS_FILE.read_text(encoding="utf-8"))


def save_users(users: dict[str, dict[str, str | None]]) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    USERS_FILE.write_text(json.dumps(users, ensure_ascii=False, indent=2), encoding="utf-8")


def _guess_suffix(audio_obj, message: Update.message) -> str:
    filename = getattr(audio_obj, "file_name", "") or ""
    suffix = Path(filename).suffix
    if suffix:
        return suffix
    if message.voice:
        return ".ogg"
    return ".bin"


def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("Manca TELEGRAM_BOT_TOKEN nelle variabili d'ambiente.")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CommandHandler("plan", plan))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO | filters.Document.ALL, handle_audio))

    logger.info("Bot avviato")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
