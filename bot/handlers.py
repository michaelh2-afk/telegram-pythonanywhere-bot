import os
import random
from datetime import datetime
from bot.clients import bot, BOT_INFO
from bot.config import HF_SPACE_ID, RATE_LIMIT, SYSTEM_PROMPT
from bot.ai import ask_ai
from bot.providers import generate
from bot.helpers import is_allowed, keep_typing, send_reply, should_respond
from bot.history import clear_history
from bot.notes import add_note, clear_notes, get_notes
from bot.preferences import get_provider, set_provider
from bot.rate_limit import is_rate_limited

# Verbose console logging for local dev and teaching. Enabled by
# BOT_VERBOSE_LOG=1 (run_local.py sets this automatically). Prints one
# line per inbound/outbound message so kids and teachers can see the
# conversation flow in their terminal while the bot is running.
VERBOSE_LOG = os.environ.get("BOT_VERBOSE_LOG", "").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)


def _log(message, direction: str, text: str) -> None:
    """Print a one-line trace of a message in verbose mode.

    direction is "in" (user → bot) or "out" (bot → user). Text is
    truncated to 500 characters so long AI replies don't flood the
    terminal. Newlines are collapsed for single-line readability.
    """
    if not VERBOSE_LOG:
        return
    user = message.from_user
    user_name = (
        f"@{user.username}" if user.username else (user.first_name or f"user:{user.id}")
    )
    bot_name = f"@{BOT_INFO.username}"
    snippet = (text or "").replace("\n", " ").replace("\r", " ")
    if len(snippet) > 500:
        snippet = snippet[:500] + "..."
    if direction == "in":
        sender, receiver = user_name, bot_name
    else:
        sender, receiver = bot_name, user_name
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {sender} → {receiver}: {snippet}", flush=True)


def _ai_command(message, prompt, fallback):
    """Run a one-shot AI prompt and reply, with a canned fallback on error.

    Shared by the simple AI commands (/about, /joke, /fact, /compliment,
    /quote) — each just supplies its own prompt and offline fallback text.
    """
    try:
        with keep_typing(message.chat.id):
            reply = generate(message.from_user.id, [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ])
        send_reply(message, reply)
    except Exception as e:
        print(f"Error in AI command: {e}")
        bot.send_message(message.chat.id, fallback)


@bot.message_handler(commands=["start"], func=is_allowed)
def cmd_start(message):
    """welcome message"""
    bot.send_message(
        message.chat.id,
        "Hello! I'm your AI assistant to learn rust programming language.\nUse /help to see available commands.",
    )


@bot.message_handler(commands=["help"], func=is_allowed)
def cmd_help(message):
    """show this message"""
    cmd_list = [
        "/start — welcome message\n"
        "/help — show this message\n"
        "/reset — clear your conversation history\n"
        "/about — about this bot\n"
        "/joke — tell a joke\n"
        "/roll — roll a dice (1-6)\n"
        "/fact — share a surprising fact\n"
        "/compliment — brighten someone's day\n"
        "/quote — an original motivational line\n"
        "/remember — save a note: remember <text>\n"
        "/recall — list all saved notes\n"
        "/forget — clear all saved notes"
    ]
    bot.send_message(
        message.chat.id,
        "Here are the commands you can use:\n\n" + "\n".join(cmd_list),
    )


@bot.message_handler(commands=["reset"], func=is_allowed)
def cmd_reset(message):
    """clear your conversation history"""
    clear_history(message.from_user.id)
    bot.send_message(message.chat.id, "Conversation cleared. Starting fresh!")


@bot.message_handler(commands=["about"], func=is_allowed)
def cmd_about(message):
    """about this bot"""
    _ai_command(
        message,
        "The user typed /about. Write a short, friendly message (2-4 sentences, no technical details) "
        "explaining who you are, what you're for, and what you can do.",
        "I'm Ferris, your friendly Rust programming tutor on Telegram!",
    )


@bot.message_handler(commands=["joke"], func=is_allowed)
def cmd_joke(message):
    """tell a joke"""
    _ai_command(
        message,
        "The user typed /joke. Tell a short, original, family-friendly joke about "
        "programming (Rust especially welcome). Keep it to a few lines and make it land.",
        "Why do Rustaceans stay so calm? Because they always know when to borrow and when to let go.",
    )


@bot.message_handler(commands=["roll"], func=is_allowed)
def cmd_roll(message):
    """roll a dice (1-6)"""
    result = random.randint(1, 6)
    bot.send_message(message.chat.id, f"🎲 You rolled a {result}!")


@bot.message_handler(commands=["fact"], func=is_allowed)
def cmd_fact(message):
    """share a surprising fact"""
    _ai_command(
        message,
        "The user typed /fact. Share one genuinely surprising, true fact in a sentence or two. "
        "Pick something unexpected — surprise me. Keep it friendly and easy to understand.",
        "Honey never spoils — archaeologists have found 3,000-year-old honey in Egyptian tombs that's still edible.",
    )


@bot.message_handler(commands=["compliment"], func=is_allowed)
def cmd_compliment(message):
    """brighten someone's day"""
    _ai_command(
        message,
        "The user typed /compliment. Write one warm, genuine, original compliment to brighten "
        "their day. Keep it short (1-2 sentences), kind, and specific enough to feel real.",
        "You show up and keep trying, and that quiet persistence is something to be proud of.",
    )


@bot.message_handler(commands=["quote"], func=is_allowed)
def cmd_quote(message):
    """an original motivational line"""
    _ai_command(
        message,
        "The user typed /quote. Write one original, motivational line (do not quote a real person). "
        "Make it uplifting and memorable — a single sentence.",
        "Every expert was once a beginner who refused to quit.",
    )


@bot.message_handler(commands=["remember"], func=is_allowed)
def cmd_remember(message):
    """save a note: /remember <text>"""
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        bot.send_message(message.chat.id, "Usage: /remember <text>")
        return
    note = parts[1].strip()
    if note.lower() == "me":
        note = "you"
    note = parts[1].strip()
    if note.lower() == "my":
        note = 'your'
    if add_note(message.from_user.id, note):
        bot.send_message(message.chat.id, "Got it — I'll remember that. 📝")
    else:
        bot.send_message(message.chat.id, "Sorry, I couldn't save that note right now.")


@bot.message_handler(commands=["recall"], func=is_allowed)
def cmd_recall(message):
    """list all saved notes"""
    notes = get_notes(message.from_user.id)
    if not notes:
        bot.send_message(message.chat.id, "You have no saved notes yet. Add one with /remember <text>")
        return
    lines = [f"{i}. {note}" for i, note in enumerate(notes, start=1)]
    bot.send_message(message.chat.id, "Your notes:\n\n" + "\n".join(lines))


@bot.message_handler(commands=["forget"], func=is_allowed)
def cmd_forget(message):
    """clear all saved notes"""
    clear_notes(message.from_user.id)
    bot.send_message(message.chat.id, "All your notes have been cleared. 🧹")


if HF_SPACE_ID:

    @bot.message_handler(commands=["model"], func=is_allowed)
    def cmd_model(message):
        """switch AI provider"""
        parts = (message.text or "").split(maxsplit=1)
        if len(parts) == 1:
            current = get_provider(message.from_user.id)
            bot.send_message(
                message.chat.id,
                f"Current provider: {current}\n\n"
                "Options:\n"
                "/model main — Cerebras (fast, multilingual, with memory)\n"
                "/model hf — ArmGPT (Armenian only, slow, no memory)",
            )
            return
        choice = parts[1].strip().lower()
        if choice not in ("main", "hf"):
            bot.send_message(
                message.chat.id, "Invalid choice. Use: /model main or /model hf"
            )
            return
        if not set_provider(message.from_user.id, choice):
            bot.send_message(
                message.chat.id, "Could not save preference. Try again later."
            )
            return
        if choice == "hf":
            bot.send_message(
                message.chat.id,
                "Switched to hf (ArmGPT).\n\n"
                "Note: this is a tiny base completion model trained only on Armenian text. "
                "It will continue whatever you write rather than answer questions, "
                "and it does not understand English. Replies take ~30-60s and there is no memory.",
            )
        else:
            bot.send_message(message.chat.id, "Switched to Main Provider.")


@bot.message_handler(content_types=["text"], func=is_allowed)
def handle_message(message):
    if not should_respond(message):
        return
    text = (message.text or "").replace(f"@{BOT_INFO.username}", "").strip()
    if not text:
        # Edited messages, forwards, or stickers-with-empty-caption can
        # arrive with no usable text. Don't burn rate-limit / AI calls on them.
        return
    _log(message, "in", text)
    if is_rate_limited(message.from_user.id):
        limit_msg = f"You've reached the daily limit of {RATE_LIMIT} messages. Try again tomorrow."
        bot.send_message(message.chat.id, limit_msg)
        _log(message, "out", f"[rate limited] {limit_msg}")
        return
    try:
        with keep_typing(message.chat.id):
            reply = ask_ai(message.from_user.id, text)
        send_reply(message, reply)
        _log(message, "out", reply)
    except Exception as e:
        print(f"Error in handle_message: {e}")
        bot.send_message(message.chat.id, "Something went wrong. Please try again.")
        _log(message, "out", f"[error] {e}")
