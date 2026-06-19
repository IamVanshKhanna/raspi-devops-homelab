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

LOGS_DIR = os.path.join(TINYBOT_ROOT, "logs", "conversations")
os.makedirs(LOGS_DIR, exist_ok=True)

chat_data = {}

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
        chat_data[chat_id] = {"messages": [], "user_count": 0}
    return chat_data[chat_id]


def add_message(chat_id, role, content):
    chat = get_chat(chat_id)
    chat["messages"].append({"role": role, "content": content})
    if role == "user":
        chat["user_count"] += 1


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
        "Hey! I'm TinyBot on a Raspberry Pi 4B.\n"
        "Commands: /health, /search, /status, /clear, /help"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/help    — This message\n"
        "/health  — Pi CPU, RAM, temp, disk\n"
        "/status  — Bot status\n"
        "/search  — Web search (DuckDuckGo)\n"
        "/clear   — Reset conversation\n"
        "/start   — Greeting"
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
        f"TinyBot status\n"
        f"Active chats: {active}\n"
        f"Total msgs cached: {total}\n"
        f"No LLM — web search only"
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

    await update.message.reply_text(f"Web search results for \"{query}\":\n\n{search_results}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    text = update.message.text

    chat = get_chat(chat_id)
    add_message(chat_id, "user", text)

    await update.message.reply_text(
        "I'm a simple bot — no LLM running on this Pi.\n"
        "Use /search <query> for web search, or /health for system status."
    )
    add_message(chat_id, "assistant", "No LLM response")


def main():
    if not BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set.")
        sys.exit(1)

    import telegram
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(register_commands).connect_timeout(30).read_timeout(30).write_timeout(30).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("health", health_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("TinyBot starting (no LLM)...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


async def register_commands(app):
    cmds = [
        ("help", "Show commands"),
        ("health", "Pi system status"),
        ("status", "Bot status"),
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