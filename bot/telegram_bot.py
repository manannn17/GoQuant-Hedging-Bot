from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from bot.handlers import handle_button, monitor_risk
import os

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Start Risk Monitoring", callback_data='monitor')],
        [InlineKeyboardButton("Hedge Now", callback_data='hedge')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📊 Welcome to GoQuant Hedging Bot!", reply_markup=reply_markup)

def run_bot():
    TOKEN = os.getenv("TG_API_TOKEN") or "7312751530:AAGhH4dacNvb0OIilhz7s93P2899n3I0ybE"
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("monitor_risk", monitor_risk))
    app.add_handler(CallbackQueryHandler(handle_button))

    print("✅ Bot running...")
    app.run_polling()
