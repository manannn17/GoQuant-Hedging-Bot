from telegram import Update
from telegram.ext import ContextTypes

from exchanges.okx import get_okx_ticker
from risk_engine.calculator import calculate_delta, calculate_hedge_ratio
from risk_engine.hedging import calculate_hedge_size, simulate_hedge_execution
from bot.monitor import start_monitoring_task


# 🔁 Monitor Risk Command
async def monitor_risk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Risk monitoring started for BTC-USDT at threshold 5%.")

# 🔘 Inline Button Handler
async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'monitor':
        await query.edit_message_text("✅ Monitoring started (BTC-USDT, threshold 5%)")
    elif query.data == 'hedge':
        asset = "BTC-USDT"
        position_size = 2.0
        beta = 1.0

        ticker = get_okx_ticker("BTC-USDT-SWAP")
        mark_price = float(ticker["last"]) if ticker else 0
        hedge_size = calculate_hedge_size(position_size, beta)
        result = simulate_hedge_execution(asset, hedge_size, mark_price)

        await query.edit_message_text(
            f"🔁 Hedge Executed:\n"
            f"Asset: {asset}\n"
            f"Hedge Size: {hedge_size:.2f}\n"
            f"Price: ${mark_price:.2f}\n"
            f"Estimated Cost: ${result['cost']:.2f}"
        )

# 📉 /get_risk Command
async def get_risk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    asset = "BTC-USDT"
    position_size = 2.0  # 2 BTC
    price_change_pct = 0.02  # 2% price move assumed

    ticker = get_okx_ticker("BTC-USDT-SWAP")
    mark_price = float(ticker["last"]) if ticker else 0

    delta = calculate_delta(position_size, price_change_pct)
    beta = 1.0
    hedge = calculate_hedge_ratio(position_size, beta)

    msg = (
        f"📉 Risk Report:\n"
        f"Asset: {asset}\n"
        f"Position: {position_size} BTC\n"
        f"Current Price: ${mark_price:.2f}\n"
        f"Estimated Delta: {delta:.2f}\n"
        f"Hedge Ratio: {hedge:.2f} (Short {abs(hedge):.2f} futures)"
    )
    await update.message.reply_text(msg)

# 🔁 /hedge_now Command
async def hedge_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    asset = "BTC-USDT"
    position_size = 2.0
    beta = 1.0

    ticker = get_okx_ticker("BTC-USDT-SWAP")
    mark_price = float(ticker["last"]) if ticker else 0
    hedge_size = calculate_hedge_size(position_size, beta)
    execution_result = simulate_hedge_execution(asset, hedge_size, mark_price)

    msg = (
        f"🔁 Hedge Executed:\n"
        f"Asset: {asset}\n"
        f"Hedge Size: {hedge_size:.2f} (short)\n"
        f"Price: ${mark_price:.2f}\n"
        f"Estimated Cost: ${execution_result['cost']:.2f}"
    )
    await update.message.reply_text(msg)


async def auto_hedge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        asset = context.args[0]
        position_size = float(context.args[1])
        threshold = float(context.args[2])

        started = start_monitoring_task(
            application=context.application,  # ✅ pass app context
            chat_id=update.effective_chat.id,
            asset=asset,
            position_size=position_size,
            threshold=threshold
        )

        if started:
            await update.message.reply_text(f"✅ Auto-hedging monitor started for {asset}")
        else:
            await update.message.reply_text(f"⚠️ Monitor already running for {asset}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}\nUsage: /auto_hedge BTC 2.0 0.6")
