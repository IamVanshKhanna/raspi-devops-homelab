import os
import sys
import json
import logging
import asyncio
from datetime import datetime
import urllib.request
import urllib.error
import urllib.parse
import re

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TINYBOT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(TINYBOT_ROOT, '.env')

BOT_TOKEN = None
if os.path.exists(ENV_PATH):
    with open(ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if line.startswith('TELEGRAM_BOT_TOKEN='):
                BOT_TOKEN = line.split('=', 1)[1].strip().strip('"').strip("'")
if not BOT_TOKEN:
    BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "qwen2.5:0.5b"
MODEL_TEMP = 0.5

SYSTEM_PROMPT = "You are TinyBot, a helpful AI assistant on a Raspberry Pi 4B (qwen2.5:0.5b). Be concise and friendly."

MAX_HISTORY = 8
MESSAGES_BEFORE_RESET = 8
OLLAMA_TIMEOUT = 180
MAX_RESPONSE_TOKENS = 512
OLLAMA_CTX_SIZE = 2048

LOGS_DIR = os.path.join(TINYBOT_ROOT, "logs", "conversations")
os.makedirs(LOGS_DIR, exist_ok=True)

chat_data = {}

def call_ollama(messages):
    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": MODEL_TEMP,
            "num_predict": MAX_RESPONSE_TOKENS,
            "num_ctx": OLLAMA_CTX_SIZE
        }
    }).encode()
    req = urllib.request.Request(
        OLLAMA_URL, data=payload,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=OLLAMA_TIMEOUT) as resp:
            result = json.loads(resp.read())
            return result.get("message", {}).get("content", "No response from model.")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        return f"Ollama error: {e.code} - {body}"
    except urllib.error.URLError as e:
        if "timed out" in str(e).lower():
            return f"The Pi took too long to respond (>{OLLAMA_TIMEOUT}s). Try a simpler question or /clear to reset."
        return f"Network error: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"


def search_web(query, max_results=4):
    try:
        data = urllib.parse.urlencode({"q": query}).encode()
        req = urllib.request.Request(
            "https://lite.duckduckgo.com/lite/",
            data=data,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")

        links = re.findall(r'<a\s+([^>]+)>(.*?)</a>', html, re.DOTALL)
        snippets = re.findall(r"class='result-snippet'>(.*?)</td>", html, re.DOTALL)

        results = []
        si = 0
        for attrs, txt in links:
            if "result-link" in attrs:
                href_m = re.search(r'href="([^"]*)"', attrs)
                href = href_m.group(1) if href_m else ""
                title = re.sub(r'<[^>]+>', '', txt).strip()
                body = re.sub(r'<[^>]+>', '', snippets[si]).strip() if si < len(snippets) else ""
                si += 1
                results.append(f"• {title}\n  {body}\n  {href}")

        if not results:
            return "No results found."
        return "\n\n".join(results[:max_results])
    except Exception as e:
        logger.warning(f"Search failed: {e}")
        return None


def get_chat(chat_id):
    if chat_id not in chat_data:
        chat_data[chat_id] = {
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}],
            "user_count": 0
        }
    return chat_data[chat_id]


def add_message(chat_id, role, content):
    chat = get_chat(chat_id)
    chat["messages"].append({"role": role, "content": content})
    if role == "user":
        chat["user_count"] += 1
    non_system = [m for m in chat["messages"] if m["role"] != "system"]
    if len(non_system) > MAX_HISTORY:
        excess = len(non_system) - MAX_HISTORY
        for _ in range(excess):
            for i, m in enumerate(chat["messages"]):
                if m["role"] != "system":
                    del chat["messages"][i]
                    break


def archive_chat(chat_id):
    chat = get_chat(chat_id)
    msgs = chat["messages"]
    if len(msgs) <= 1:
        return
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(LOGS_DIR, f"chat_{chat_id}_{ts}.json")
    with open(path, "w") as f:
        json.dump(msgs, f, indent=2)
    logger.info(f"Archived {len(msgs)} messages for chat {chat_id} to {path}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hey! I'm TinyBot on a Pi 4B with Ollama (qwen2.5:0.5b).\n"
        "Send me a message. /help for commands."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/help    — This message\n"
        "/health  — Pi CPU, RAM, temp\n"
        "/status  — Bot config\n"
        "/search  — Web search\n"
        "/clear   — Reset conversation\n"
        "/start   — Greeting\n\n"
        "Context auto-resets after 8 messages (archived to disk)."
    )


async def health_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import psutil
    cpu = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    try:
        with open('/sys/class/thermal/thermal_zone0/temp') as f:
            temp = int(f.read().strip()) / 1000
    except Exception:
        temp = None

    msg = (
        f"CPU: {cpu}%\n"
        f"RAM: {mem.percent}% ({mem.used // 1024 // 1024}MB / {mem.total // 1024 // 1024}MB)\n"
        f"Disk: {disk.percent}% ({disk.free // 1024 // 1024 // 1024}GB free)\n"
    )
    if temp is not None:
        msg += f"Temp: {temp:.1f}°C\n"
    msg += f"Uptime: {os.popen('uptime -p 2>/dev/null').read().strip() or 'N/A'}"
    await update.message.reply_text(msg.strip())


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    active = len(chat_data)
    total = sum(len(c["messages"]) for c in chat_data.values())
    await update.message.reply_text(
        f"Model: {OLLAMA_MODEL}\n"
        f"Context: {OLLAMA_CTX_SIZE} tokens\n"
        f"Max response: {MAX_RESPONSE_TOKENS} tokens\n"
        f"History: {MAX_HISTORY} msgs, resets every {MESSAGES_BEFORE_RESET}\n"
        f"Active chats: {active}\n"
        f"Total msgs cached: {total}"
    )


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if chat_id in chat_data:
        archive_chat(chat_id)
        del chat_data[chat_id]
    await update.message.reply_text("Conversation archived and reset.")


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args)
    if not query:
        await update.message.reply_text("Usage: /search <query>")
        return

    await update.message.reply_text("Searching the web...")
    loop = asyncio.get_event_loop()
    search_results = await loop.run_in_executor(None, search_web, query)

    if search_results is None:
        await update.message.reply_text("Search failed. The Pi may not have internet, or DuckDuckGo is rate-limiting.")
        return
    if search_results == "No results found.":
        await update.message.reply_text("No results found for that query.")
        return

    context_text = (
        f"Web search results for \"{query}\":\n\n{search_results}\n\n"
        f"Answer the user's question based on the search results above."
    )

    chat = get_chat(update.message.chat_id)
    temp_msgs = chat["messages"] + [{"role": "user", "content": context_text}]

    try:
        await context.bot.send_chat_action(chat_id=update.message.chat_id, action="typing")
    except Exception:
        pass

    reply = await loop.run_in_executor(None, call_ollama, temp_msgs)

    if reply.startswith("Error") or reply.startswith("Ollama error"):
        await update.message.reply_text(reply)
        return

    add_message(update.message.chat_id, "user", f"[Web search] {query}")
    add_message(update.message.chat_id, "assistant", reply)
    await update.message.reply_text(reply)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    text = update.message.text

    try:
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    except Exception:
        pass

    chat = get_chat(chat_id)

    if chat["user_count"] >= MESSAGES_BEFORE_RESET:
        archive_chat(chat_id)
        chat["messages"] = [{"role": "system", "content": SYSTEM_PROMPT}]
        chat["user_count"] = 0
        logger.info(f"Chat {chat_id} session reset after {MESSAGES_BEFORE_RESET} messages")

    add_message(chat_id, "user", text)

    loop = asyncio.get_event_loop()
    reply = await loop.run_in_executor(None, call_ollama, chat["messages"])

    if reply.startswith("Error") or reply.startswith("Ollama error"):
        await update.message.reply_text(reply)
        return

    add_message(chat_id, "assistant", reply)
    await update.message.reply_text(reply)


def main():
    if not BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set.")
        sys.exit(1)

    app = ApplicationBuilder().token(BOT_TOKEN).post_init(register_commands).connect_timeout(30).read_timeout(30).write_timeout(30).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("health", health_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Ollama chat bot starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


import telegram

async def register_commands(app):
    cmds = [
        ("help", "Show commands"),
        ("health", "Pi system status"),
        ("status", "Bot config"),
        ("search", "Search the web"),
        ("clear", "Reset conversation"),
        ("start", "Greeting"),
    ]
    try:
        await app.bot.set_my_commands([telegram.BotCommand(c, d) for c, d in cmds])
        logger.info("Registered bot commands with Telegram")
    except Exception as e:
        logger.warning(f"Could not register commands: {e}")


if __name__ == '__main__':
    main()
