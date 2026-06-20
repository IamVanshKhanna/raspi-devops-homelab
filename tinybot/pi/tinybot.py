import os
import sys
import logging
import asyncio
import urllib.request
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
ENV_PATH = os.path.join(TINYBOT_ROOT, ".env")

BOT_TOKEN = None
if os.path.exists(ENV_PATH):
    with open(ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if line.startswith("TELEGRAM_BOT_TOKEN="):
                BOT_TOKEN = line.split("=", 1)[1].strip().strip('"').strip("'")
if not BOT_TOKEN:
    BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")


def search_web(query, max_results=4):
    try:
        data = urllib.parse.urlencode({"q": query}).encode()
        req = urllib.request.Request(
            "https://lite.duckduckgo.com/lite/",
            data=data,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")

        links = re.findall(r"<a\s+([^>]+)>(.*?)</a>", html, re.DOTALL)
        snippets = re.findall(r"class='result-snippet'>(.*?)</td>", html, re.DOTALL)

        results = []
        si = 0
        for attrs, txt in links:
            if "result-link" in attrs:
                href_m = re.search(r'href="([^"]*)"', attrs)
                href = href_m.group(1) if href_m else ""
                title = re.sub(r"<[^>]+>", "", txt).strip()
                body = re.sub(r"<[^>]+>", "", snippets[si]).strip() if si < len(snippets) else ""
                si += 1
                results.append(f"\u2022 {title}\n  {body}\n  {href}")

        if not results:
            return "No results found."
        return "\n\n".join(results[:max_results])
    except Exception as e:
        logger.warning(f"Search failed: {e}")
        return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hey! I'm TinyBot on a Raspberry Pi 4B.\n"
        "Commands: /health, /fan, /search, /chatid, /help"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/help    - This message\n"
        "/health  - Pi CPU, RAM, temp, disk\n"
        "/fan     - Fan & GPIO status\n"
        "/search  - Web search (DuckDuckGo)\n"
        "/chatid  - Your Telegram chat ID\n"
        "/start   - Greeting"
    )


async def fan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import subprocess
    temp = "N/A"
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            val = int(f.read().strip())
            temp = f"{val / 1000:.1f}C"
    except Exception:
        pass
    gpio = subprocess.getoutput("pinctrl 12 2>/dev/null").strip() or "N/A"
    deskpi = subprocess.getoutput("systemctl is-active deskpi.service 2>/dev/null").strip()
    load = open("/proc/loadavg").read().split()[:3]
    fan_status = "RUNNING (PWM auto)" if deskpi == "active" else "MANUAL (GPIO fixed)"
    await update.message.reply_text(
        f"Fan Status:\n"
        f"Temp: {temp}\n"
        f"GPIO12: {gpio}\n"
        f"DeskPi: {deskpi}\n"
        f"Fan: {fan_status}\n"
        f"Load: {' '.join(load)}"
    )


async def health_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import psutil
    cpu = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            temp = int(f.read().strip()) / 1000
    except Exception:
        temp = None

    msg = (
        f"CPU: {cpu}%\n"
        f"RAM: {mem.percent}% ({mem.used // 1024 // 1024}MB / {mem.total // 1024 // 1024}MB)\n"
        f"Disk: {disk.percent}% ({disk.free // 1024 // 1024 // 1024}GB free)\n"
    )
    if temp is not None:
        msg += f"Temp: {temp:.1f}C\n"
    msg += f"Uptime: {os.popen('uptime -p 2>/dev/null').read().strip() or 'N/A'}"
    await update.message.reply_text(msg.strip())


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

    await update.message.reply_text(f'Web search results for "{query}":\n\n{search_results}')


async def chatid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = update.message.chat_id
    await update.message.reply_text(f"Your chat ID: {cid}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "I'm a simple bot - no LLM running on this Pi.\n"
        "Use /search <query> for web search, or /health for system status."
    )


def main():
    if not BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set.")
        sys.exit(1)

    import telegram
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(register_commands).connect_timeout(30).read_timeout(30).write_timeout(30).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("health", health_command))
    app.add_handler(CommandHandler("fan", fan_command))
    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(CommandHandler("chatid", chatid_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("TinyBot starting (no LLM)...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


async def register_commands(app):
    cmds = [
        ("help", "Show commands"),
        ("health", "Pi system status"),
        ("fan", "Fan & GPIO status"),
        ("search", "Search the web"),
        ("chatid", "Your Telegram chat ID"),
        ("start", "Greeting"),
    ]
    try:
        await app.bot.set_my_commands([telegram.BotCommand(c, d) for c, d in cmds])
        logger.info("Registered bot commands with Telegram")
    except Exception as e:
        logger.warning(f"Could not register commands: {e}")


if __name__ == "__main__":
    main()

