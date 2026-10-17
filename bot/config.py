import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "5994037577:AAFySeJ-huI_ATLuCsfu0OWOqCE2EQED08Q")
ADMIN_ID = int(os.getenv("ADMIN_ID", "1813590984"))

# SQLite file (on Railway use a volume path, e.g. /data/bot.db)
DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "..", "bot.db"))

BINANCE_FUTURES_URL = "https://fapi.binance.com"

# Default settings (admin can change them live via /settings — stored in DB)
DEFAULTS = {
    "signals_interval_min": 30,   # як часто генерувати нові зделки
    "signals_count": 5,           # скільки зделок видавати за один прохід
    "min_score": 65,              # мінімальний "шанс" (%), щоб монета потрапила в сигнал
    "base_price": 10,             # ціна базової підписки (USDT)
    "base_days": 30,              # тривалість базової підписки (днів)
    "pro_price": 25,              # ціна професійної підписки (USDT)
    "pro_days": 30,               # тривалість професійної підписки (днів)
}
