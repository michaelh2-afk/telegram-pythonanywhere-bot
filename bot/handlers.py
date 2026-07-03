import os
import random
from datetime import datetime
from bot.clients import bot, BOT_INFO
from bot.config import COMMIT_SHA, HF_SPACE_ID, RATE_LIMIT, SYSTEM_PROMPT
from bot.ai import ask_ai
from bot.providers import generate
from bot.helpers import is_allowed, keep_typing, send_reply, should_respond
from bot.history import clear_history
from bot.notes import add_note, clear_notes, get_notes
from bot.preferences import get_level, get_provider, set_level, set_provider
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
    _ai_command(
        message,
        "The user just typed /start — it's their first message to you. Write a short, warm welcome "
        "(2-3 sentences): greet them, say in one line that you help them find the best programming "
        "language and tech direction for them and can then teach it step by step, and invite them to "
        "type /help to see what you can do. Be friendly and encouraging, and avoid technical jargon.",
        "Hi! 👋 I can help you find the best programming language and tech direction for you, then "
        "teach it step by step. Type /help to see everything I can do.",
    )


@bot.message_handler(commands=["help"], func=is_allowed)
def cmd_help(message):
    """show this message"""
    cmd_list = [
        "/start — welcome message\n"
        "/help — show this message\n"
        "/reset — clear your conversation history\n"
        "/about — about this bot\n"
        "/teach — learn a language: teach <language>\n"
        "/level — set your learning level: level <beginner|elementary|intermediate>\n"
        "/quiz — test your knowledge: quiz <language>\n"
        "/explain — explain a term: explain <term>\n"
        "/example — show a code example: example <topic>\n"
        "/roadmap — a learning roadmap: roadmap <language>\n"
        "/joke — tell a joke\n"
        "/roll — roll a dice (1-6)\n"
        "/fact — share a surprising fact\n"
        "/compliment — brighten someone's day\n"
        "/quote — an original motivational line\n"
        "/remember — save a note: remember <text>\n"
        "/recall — list all saved notes\n"
        "/forget — clear all saved notes\n"
        "/sha — show the live git commit SHA"
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


# Maps a saved learning level to a short description of the learner, so the
# learning commands can pitch at the right place. The lesson always aims up
# to a solid intermediate level; the level just moves the starting line.
LEVEL_AUDIENCE = {
    "beginner": "a complete beginner who has never written code before",
    "elementary": "someone who knows only the very basics (variables, printing, simple loops) and wants to go further",
    "intermediate": "someone already comfortable with the basics who wants to reach a solid intermediate level",
}


@bot.message_handler(commands=["teach"], func=is_allowed)
def cmd_teach(message):
    """learn a programming language: /teach <language>"""
    level = get_level(message.from_user.id)
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        bot.send_message(
            message.chat.id,
            "Usage: /teach <language>\n\n"
            "Example: /teach python\n\n"
            f"I'll teach it from your level (currently: {level}) up toward an intermediate "
            "level, explaining every new term along the way.\n"
            "Change your level anytime with /level. "
            "Try a language like python, javascript, java, c++, go, or rust.",
        )
        return
    language = parts[1].strip()
    audience = LEVEL_AUDIENCE.get(level, LEVEL_AUDIENCE["beginner"])
    _ai_command(
        message,
        f"The user typed /teach {language}. Their self-reported learning level is '{level}': "
        f"teach as if to {audience}. They have chosen to learn the {language} programming "
        "language, so do NOT ask quiz questions — teach it directly. Give a clear lesson that "
        "starts from their level and takes them up toward a solid intermediate level. "
        "IMPORTANT: explain every technical term the first time you use it, in plain language a "
        "learner at this level understands (a short parenthesis or one simple sentence per term). "
        "Structure it as: "
        f"(1) one line on what {language} is and what it's good for; (2) how to get started "
        "(install and where to run code) — you may skip this if the level is intermediate; "
        "(3) the core concepts to learn at this level, each with a tiny code example; (4) a short "
        "roadmap of the next intermediate topics to grow into; (5) one small practice-project idea "
        "and one free resource. Keep code examples short and correct, use Markdown with fenced code "
        f"blocks, and stay encouraging and concise. If {language} is not a real programming "
        "language, say so kindly and suggest a few popular ones to try instead.",
        f"Sorry, I couldn't put together a {language} lesson right now — try /teach {language} again!",
    )


@bot.message_handler(commands=["level"], func=is_allowed)
def cmd_level(message):
    """set your learning level: /level <beginner|elementary|intermediate>"""
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) == 1:
        current = get_level(message.from_user.id)
        bot.send_message(
            message.chat.id,
            f"Your current level: {current}\n\n"
            "Options:\n"
            "/level beginner — you've never programmed before\n"
            "/level elementary — you know the very basics\n"
            "/level intermediate — you're comfortable with the basics\n\n"
            "Your level decides where /teach starts — it always teaches up toward an "
            "intermediate level.",
        )
        return
    choice = parts[1].strip().lower()
    if choice not in ("beginner", "elementary", "intermediate"):
        bot.send_message(
            message.chat.id,
            "Invalid level. Use: /level beginner, /level elementary, or /level intermediate",
        )
        return
    if not set_level(message.from_user.id, choice):
        bot.send_message(
            message.chat.id,
            "Could not save your level — the bot may be running without a database. Try again later.",
        )
        return
    bot.send_message(
        message.chat.id,
        f"Got it — your level is now {choice}. /teach will start from there. 🎯",
    )


@bot.message_handler(commands=["quiz"], func=is_allowed)
def cmd_quiz(message):
    """quiz yourself on a language: /quiz <language>"""
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        bot.send_message(message.chat.id, "Usage: /quiz <language>\n\nExample: /quiz python")
        return
    language = parts[1].strip()
    level = get_level(message.from_user.id)
    _ai_command(
        message,
        f"The user typed /quiz {language}. Make a short self-contained quiz to test their "
        f"{language} knowledge at a '{level}' level. Do NOT ask the questions interactively. "
        "First list 5 clear, numbered questions (a mix of multiple-choice and short-answer). Then "
        "write 'Answers below — no peeking!' followed by a few blank lines, then an answer key "
        "with a one-line explanation for each. Keep it concise and use Markdown.",
        f"Sorry, I couldn't make a {language} quiz right now — try /quiz {language} again!",
    )


@bot.message_handler(commands=["explain"], func=is_allowed)
def cmd_explain(message):
    """explain a programming term: /explain <term>"""
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        bot.send_message(message.chat.id, "Usage: /explain <term>\n\nExample: /explain recursion")
        return
    term = parts[1].strip()
    level = get_level(message.from_user.id)
    _ai_command(
        message,
        f"The user typed /explain {term}. Explain the programming concept or term '{term}' in "
        f"simple, plain language suitable for a '{level}'-level learner. Define any jargon you "
        "use. Include one tiny code example if it helps. Keep it short — a few sentences plus the "
        f"example — and use Markdown. If '{term}' is not a programming term, say so briefly and "
        "give the closest useful explanation.",
        f"Sorry, I couldn't explain '{term}' right now — try /explain {term} again!",
    )


@bot.message_handler(commands=["example"], func=is_allowed)
def cmd_example(message):
    """show a code example: /example <topic>"""
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        bot.send_message(message.chat.id, "Usage: /example <topic>\n\nExample: /example python loops")
        return
    topic = parts[1].strip()
    level = get_level(message.from_user.id)
    _ai_command(
        message,
        f"The user typed /example {topic}. Show one short, correct, well-commented code example "
        f"that demonstrates '{topic}', aimed at a '{level}'-level learner. Put the code in a "
        "Markdown fenced code block, then add 1-3 sentences explaining how it works and defining "
        "any new term. Keep it focused on this one example.",
        f"Sorry, I couldn't put together an example for '{topic}' right now — try /example {topic} again!",
    )


@bot.message_handler(commands=["roadmap"], func=is_allowed)
def cmd_roadmap(message):
    """learning roadmap for a language: /roadmap <language>"""
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        bot.send_message(message.chat.id, "Usage: /roadmap <language>\n\nExample: /roadmap python")
        return
    language = parts[1].strip()
    level = get_level(message.from_user.id)
    _ai_command(
        message,
        f"The user typed /roadmap {language}. Give a step-by-step learning roadmap for {language} "
        f"that starts from a '{level}' level and goes up to a solid intermediate level. Present it "
        "as an ordered list of 5-8 milestones; for each, name the topics to learn and one thing to "
        "build to practice. End with one or two good free resources. Explain any technical term you "
        f"use. Keep it concise and use Markdown. If {language} is not a real programming language, "
        "say so kindly and suggest alternatives.",
        f"Sorry, I couldn't build a {language} roadmap right now — try /roadmap {language} again!",
    )


# Random topics for /joke so repeated calls vary. The joke itself is always
# written by the AI; the topic just steers it to a fresh subject each time
# (the /joke command has no conversation history, so an identical prompt
# tends to produce identical output).
JOKE_TOPICS = [
    "animals",
    "food",
    "school",
    "space",
    "the weather",
    "sports",
    "music",
    "the ocean",
    "everyday life",
    "time travel",
    "robots",
    "the weekend",
]


@bot.message_handler(commands=["joke"], func=is_allowed)
def cmd_joke(message):
    """tell a joke"""
    topic = random.choice(JOKE_TOPICS)
    _ai_command(
        message,
        f"The user typed /joke. Tell a short, original, family-friendly joke about {topic}. "
        "Do NOT make it about programming, coding, or Rust. Make it different from common, "
        "well-known jokes. Keep it to a few lines and make it land.",
        "Sorry, I couldn't think of a joke right now — try /joke again!",
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


@bot.message_handler(commands=["sha"], func=is_allowed)
def cmd_sha(message):
    sha = COMMIT_SHA or "unknown"
    bot.send_message(message.chat.id, f"Live SHA: {sha}")


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
