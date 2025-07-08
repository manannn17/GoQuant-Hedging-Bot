from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from bot.handlers import handle_button, monitor_risk, get_risk
import os

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Start Risk Monitoring", callback_data='monitor')],
        [InlineKeyboardButton("Hedge Now", callback_data='hedge')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📊 Welcome to GoQuant Hedging Bot!", reply_markup=reply_markup)

def run_bot():
    TOKEN = os.getenv("TG_API_TOKEN") or "7731811081:AAHIHDBltkc3Gf8O41EJzDqQ1WVrmWZR__M"  # Replace if needed
    app = ApplicationBuilder().token(TOKEN).build()

    # Add handlers inside the function
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("monitor_risk", monitor_risk))
    app.add_handler(CommandHandler("get_risk", get_risk))
    app.add_handler(CallbackQueryHandler(handle_button))

    print("✅ Bot running...")
    app.run_polling()
