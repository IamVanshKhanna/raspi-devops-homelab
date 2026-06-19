import os
import subprocess
import psutil
import requests

def load_token():
    with open('/home/vansh/raspi-devops-homelab/tinybot/.env', 'r') as f:
        for line in f:
            if line.startswith('TELEGRAM_BOT_TOKEN='):
                return line.split('=')[1].strip()
    return None

def load_chat_id():
    try:
        with open('/home/vansh/raspi-devops-homelab/tinybot/state/admin_chat.txt', 'r') as f:
            return f.read().strip()
    except: return None

def get_stats():
    ram = psutil.virtual_memory()
    temp = subprocess.getoutput('vcgencmd measure_temp').replace('temp=', '')
    fan = 'ON (DeskPi)' if subprocess.getoutput('systemctl is-active deskpi.service') == 'active' else 'OFF'
    return f'⏰ Scheduled Health Report:\n🌡️ Temp: {temp}\n📊 RAM: {ram.used/(1024**3):.2f}GB / {ram.total/(1024**3):.2f}GB\n🌀 Fan: {fan}'

token = load_token()
chat_id = load_chat_id()
if token and chat_id:
    url = f'https://api.telegram.org/bot{token}/sendMessage'
    requests.post(url, json={'chat_id': chat_id, 'text': get_stats()})
