import requests
from telegram import Bot, Update
from telegram.ext import CommandHandler, ApplicationBuilder, ContextTypes
import asyncio

TELEGRAM_BOT_TOKEN = "7730623043:AAGf9loyGPej8KX9o3LPnXm9rqbz6dhq5Xc"

# Initialiser le bot Telegram
bot = Bot(token=TELEGRAM_BOT_TOKEN)

# Paramètres utilisateur (par défaut)
user_preferences = {
    "exchange_type": "all",   # "centralized", "decentralized", "all"
    "min_volume": 0,          # Volume minimum (en USD)
    "min_percentage": 2.0,    # Pourcentage minimum pour détecter une opportunité
    "is_monitoring": False    # Indique si la surveillance est active
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Commande /start pour initialiser le bot.
    """
    user_id = update.effective_chat.id
    await context.bot.send_message(
        chat_id=user_id,
        text=(
            "👋 Bienvenue sur le bot d'arbitrage crypto !\n"
            "🔧 Utilisez les commandes suivantes pour configurer vos préférences :\n"
            " - `/exchange_type [centralized|decentralized|all]` : Type d'échangeur.\n"
            " - `/min_volume [valeur]` : Volume minimum (en USD).\n"
            " - `/min_percentage [valeur]` : Pourcentage minimum d'arbitrage.\n"
            " - `/surveiller` : Démarrer la surveillance.\n"
            "\n"
            "🚀 Une fois configuré, je surveillerai les opportunités d'arbitrage pour vous."
        )
    )

async def set_exchange_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Commande pour définir le type d'échangeur.
    """
    user_id = update.effective_chat.id
    if not context.args or context.args[0] not in ["centralized", "decentralized", "all"]:
        await context.bot.send_message(
            chat_id=user_id,
            text="❌ Type d'échangeur invalide ! Utilisez : centralized, decentralized, ou all."
        )
        return

    user_preferences["exchange_type"] = context.args[0]
    await context.bot.send_message(
        chat_id=user_id,
        text=f"✅ Type d'échangeur défini sur : {context.args[0]}"
    )

async def set_min_volume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Commande pour définir le volume minimum.
    """
    user_id = update.effective_chat.id
    try:
        min_volume = float(context.args[0])
        user_preferences["min_volume"] = min_volume
        await context.bot.send_message(
            chat_id=user_id,
            text=f"✅ Volume minimum défini sur : {min_volume} USD"
        )
    except (IndexError, ValueError):
        await context.bot.send_message(
            chat_id=user_id,
            text="❌ Format invalide ! Utilisez : /min_volume [valeur]"
        )

async def set_min_percentage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Commande pour définir le pourcentage minimum d'arbitrage.
    """
    user_id = update.effective_chat.id
    try:
        min_percentage = float(context.args[0])
        user_preferences["min_percentage"] = min_percentage
        await context.bot.send_message(
            chat_id=user_id,
            text=f"✅ Pourcentage minimum défini sur : {min_percentage}%"
        )
    except (IndexError, ValueError):
        await context.bot.send_message(
            chat_id=user_id,
            text="❌ Format invalide ! Utilisez : /min_percentage [valeur]"
        )

async def surveiller(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Commande pour démarrer la surveillance.
    """
    user_id = update.effective_chat.id
    if user_preferences["is_monitoring"]:
        await context.bot.send_message(
            chat_id=user_id,
            text="⚠️ La surveillance est déjà en cours !"
        )
        return

    user_preferences["is_monitoring"] = True
    await context.bot.send_message(
        chat_id=user_id,
        text="🚀 Surveillance des opportunités d'arbitrage démarrée..."
    )

    while user_preferences["is_monitoring"]:
        await find_arbitrage_opportunities(user_id, user_preferences["min_percentage"])
        await asyncio.sleep(60)  # Intervalle de vérification (60 secondes)

async def stop_surveiller(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Commande pour arrêter la surveillance.
    """
    user_id = update.effective_chat.id
    user_preferences["is_monitoring"] = False
    await context.bot.send_message(
        chat_id=user_id,
        text="🛑 Surveillance arrêtée."
    )

def get_coin_prices_on_exchanges(coin_id):
    """
    Récupère les prix et volumes d'une crypto sur différents échangeurs.
    """
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/tickers"
    response = requests.get(url)
    if response.status_code == 200:
        tickers = response.json().get("tickers", [])
        return [
            {
                "exchange": ticker.get("market", {}).get("name"),
                "price": ticker.get("converted_last", {}).get("usd"),
                "volume": ticker.get("converted_volume", {}).get("usd"),
                "type": ticker.get("market", {}).get("identifier_type")
            }
            for ticker in tickers if ticker.get("converted_last", {}).get("usd") is not None
        ]
    return []

async def find_arbitrage_opportunities(user_id, threshold):
    """
    Trouve les opportunités d'arbitrage en fonction des préférences utilisateur.
    """
    coins = get_all_coins()
    for coin_id in coins:
        prices = get_coin_prices_on_exchanges(coin_id)
        if len(prices) < 2:
            continue

        filtered_prices = [
            p for p in prices
            if (user_preferences["exchange_type"] == "all" or p["type"] == user_preferences["exchange_type"]) and
               (p["volume"] >= user_preferences["min_volume"])
        ]

        for i in range(len(filtered_prices)):
            for j in range(i + 1, len(filtered_prices)):
                price1, exchange1 = filtered_prices[i]["price"], filtered_prices[i]["exchange"]
                price2, exchange2 = filtered_prices[j]["price"], filtered_prices[j]["exchange"]

                diff_percentage = abs((price1 - price2) / price1) * 100

                if diff_percentage >= threshold:
                    await send_telegram_alert(user_id, coin_id, exchange1, price1, exchange2, price2, diff_percentage)

async def send_telegram_alert(user_id, coin_id, exchange1, price1, exchange2, price2, diff_percentage):
    """
    Envoie une alerte sur Telegram lorsqu'une opportunité est trouvée.
    """
    message = (
        f"💰 *Opportunité d'Arbitrage Détectée !*\n\n"
        f"🔹 Crypto : *{coin_id}*\n"
        f"🔹 Échangeur 1 : *{exchange1}* - Prix : *{price1:.2f} USD*\n"
        f"🔹 Échangeur 2 : *{exchange2}* - Prix : *{price2:.2f} USD*\n"
        f"🔹 Différence : *{diff_percentage:.2f}%*\n\n"
        f"Profitez-en rapidement ! 🚀"
    )
    await bot.send_message(chat_id=user_id, text=message, parse_mode="Markdown")

# Configurer le bot avec les commandes
application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("exchange_type", set_exchange_type))
application.add_handler(CommandHandler("min_volume", set_min_volume))
application.add_handler(CommandHandler("min_percentage", set_min_percentage))
application.add_handler(CommandHandler("surveiller", surveiller))
application.add_handler(CommandHandler("stop", stop_surveiller))

# Lancer le bot
if __name__ == "__main__":
    print("Bot en cours d'exécution...")
    application.run_polling()
