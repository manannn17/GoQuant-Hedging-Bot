from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from bot.handlers import handle_button, monitor_risk, get_risk, hedge_now
import os
from bot.handlers import hedge_now, auto_hedge


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Start Risk Monitoring", callback_data='monitor')],
        [InlineKeyboardButton("Hedge Now", callback_data='hedge')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📊 Welcome to GoQuant Hedging Bot!", reply_markup=reply_markup)

def run_bot():
    TOKEN = os.getenv("TG_API_TOKEN") or "7731811081:AAHIHDBltkc3Gf8O41EJzDqQ1WVrmWZR__M"
    app = ApplicationBuilder().token(TOKEN).build()

    # ✅ Add ALL handlers BEFORE running polling
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("monitor_risk", monitor_risk))
    app.add_handler(CommandHandler("get_risk", get_risk))
    app.add_handler(CommandHandler("hedge_now", hedge_now))  # <- moved here
    app.add_handler(CallbackQueryHandler(handle_button))
    app.add_handler(CommandHandler("auto_hedge", auto_hedge))


    print("✅ Bot running...")
    app.run_polling()

