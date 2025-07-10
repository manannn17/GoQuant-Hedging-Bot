"""# src/main.py

import dotenv
import os
from bot.handler import get_app
from exchanges.okx import get_okx_ticker

print("OKX Price:", get_okx_ticker())

if __name__ == "__main__":
    dotenv.load_dotenv()
    app = get_app()
    app.run_polling()

from analytics.greeks import calculate_greeks
from analytics.hedge_ratio import calculate_beta, hedge_ratio
from analytics.var_drawdown import historical_var, max_drawdown

# Sample mocks
print("Delta:", calculate_greeks(29000, 30000, 0.1, 0.01, 0.7))
print("Beta:", calculate_beta([0.01, 0.02], [0.011, 0.019]))
print("VaR:", historical_var([-0.01, 0.02, -0.03]))
"""

"""# src/main.py

import os
from dotenv import load_dotenv
from bot.handler import get_app

def main():
    load_dotenv()  # Ensure .env is loaded before anything
    app = get_app()  # Get configured bot application
    app.run_polling()  # Start bot loop

if __name__ == "__main__":
    main()
"""

"""from bot.handler import get_app

if __name__ == "__main__":
    app = get_app()
    app.run_polling()
"""

# main.py (FIXED VERSION)
import logging
from bot.handler import get_app

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    try:
        app = get_app()
        print("🚀 Starting GoQuant Hedging Bot...")
        app.run_polling(drop_pending_updates=True)
    except KeyboardInterrupt:
        print("Bot stopped")
    except Exception as e:
        print(f"Error: {e}")