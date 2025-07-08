from telegram import Update
from telegram.ext import ContextTypes

async def monitor_risk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Risk monitoring started for BTC-USDT at threshold 5%.")

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'monitor':
        await query.edit_message_text("✅ Monitoring started (BTC-USDT, threshold 5%)")
    elif query.data == 'hedge':
        await query.edit_message_text("🔁 Hedging triggered...\nDelta: 0.65\nRecommended Hedge: Short 0.65 BTC")
