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


from exchanges.okx import get_okx_ticker
from risk_engine.calculator import calculate_delta, calculate_hedge_ratio

async def get_risk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Mock values
    position_size = 2.0  # 2 BTC
    price_change_pct = 0.02  # assume +2% move

    # Get market data
    ticker = get_okx_ticker("BTC-USDT-SWAP")
    mark_price = float(ticker["last"]) if ticker else 0

    # Calculate delta and hedge
    delta = calculate_delta(position_size, price_change_pct)
    beta = 1.0  # Hardcoded beta for now
    hedge = calculate_hedge_ratio(position_size, beta)

    msg = (
        f"📉 Risk Report:\n"
        f"Asset: BTC/USDT\n"
        f"Position: {position_size} BTC\n"
        f"Current Price: ${mark_price}\n"
        f"Estimated Delta: {delta:.2f}\n"
        f"Hedge Ratio: {hedge:.2f} (Short {abs(hedge)} futures)"
    )
    await update.message.reply_text(msg)

    #7731811081:AAHIHDBltkc3Gf8O41EJzDqQ1WVrmWZR__M
