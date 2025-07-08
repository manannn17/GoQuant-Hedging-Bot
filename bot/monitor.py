import asyncio
from telegram import Bot
from exchanges.okx import get_okx_ticker
from risk_engine.calculator import calculate_delta
from risk_engine.hedging import calculate_hedge_size

# Store running monitor tasks
monitoring_tasks = {}

async def monitor_asset(bot: Bot, chat_id, asset, position_size, threshold):
    print(f"🟡 Starting risk monitor for {asset}, size={position_size}, threshold={threshold}")

    while True:
        try:
            ticker = get_okx_ticker("BTC-USDT-SWAP")
            mark_price = float(ticker["last"]) if ticker else 0

            price_change_pct = 0.02  # Simulate for now
            delta = calculate_delta(position_size, price_change_pct)

            if abs(delta) > threshold:
                hedge_size = calculate_hedge_size(position_size)
                await bot.send_message(
                    chat_id=chat_id,
                    text=(
                        f"🚨 Risk Alert for {asset}!\n"
                        f"Delta: {delta:.2f}\n"
                        f"Threshold: {threshold}\n"
                        f"Recommended Hedge: {hedge_size:.2f}\n"
                        f"/hedge_now to execute."
                    )
                )
        except Exception as e:
            print(f"❌ Monitor error: {e}")

        await asyncio.sleep(10)  # Check every 10 seconds

def start_monitoring_task(application, chat_id, asset, position_size, threshold):
    key = f"{chat_id}_{asset}"
    if key in monitoring_tasks:
        print("🟠 Monitor already running.")
        return False

    task = application.create_task(
        monitor_asset(application.bot, chat_id, asset, position_size, threshold)
    )
    monitoring_tasks[key] = task
    return True