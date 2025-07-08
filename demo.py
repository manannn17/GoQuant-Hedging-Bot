from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Hello, I am your baap')

app = ApplicationBuilder().token('7312751530:AAGhH4dacNvb0OIilhz7s93P2899n3I0ybE').build()
app.add_handler(CommandHandler('start', start))
app.run_polling()