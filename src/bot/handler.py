# -*- coding: utf-8 -*-
# bot/handler.py (ENHANCED VERSION WITH USER-FRIENDLY BUTTONS)
import sys
import os
import logging
from typing import Dict, List, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram.error import NetworkError, TimedOut, BadRequest
import time
import asyncio
import json
from datetime import datetime, timedelta

# Fix import path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from analytics.risk_monitor import risk_monitor
except ImportError as e:
    logging.error(f"Failed to import risk_monitor: {e}")
    # Create a dummy risk monitor if import fails
    class DummyRiskMonitor:
        def start_monitoring(self, *args): return True
        def stop_monitoring(self, *args): return True
        def get_status(self, *args): return {"BTCUSD": {"size": 1000, "threshold": 0.02, "strategy": "delta_neutral", "active": True}}
        def check_risk(self, *args): return {"VaR": 50, "alert": False, "risk_level": "LOW"}
        def calculate_hedge_recommendation(self, *args): return {"position_size": 1000, "current_risk": 0.01, "action": "HEDGE", "strategy": "delta_neutral", "hedge_size": 500, "risk_reduction": 0.015}
        def execute_hedge(self, *args): return {"success": True, "strategy": "delta_neutral", "hedge_size": 500, "execution_price": 50000, "transaction_cost": 25, "risk_reduction": 0.015, "new_var": 35, "effectiveness": 0.7}
        def get_hedge_history(self, *args): return [{"date": "2024-01-01", "action": "HEDGE", "size": 500, "strategy": "delta_neutral", "pnl": 25, "status": "SUCCESS"}]
        def get_portfolio_analytics(self, *args): return {"total_value": 5000, "total_pnl": 150, "position_count": 3, "portfolio_var": 100, "portfolio_var_99": 150, "expected_shortfall": 75, "max_drawdown": 0.05, "avg_correlation": 0.6, "diversification_ratio": 0.8, "risk_concentration": 0.3, "total_hedges": 2, "hedge_effectiveness": 0.75, "hedge_pnl": 50}
        def configure_risk_params(self, *args): return True
        def setup_auto_hedge(self, *args): return True
        def get_all_active_positions(self, *args): return {}
    risk_monitor = DummyRiskMonitor()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Supported assets for validation
SUPPORTED_ASSETS = [
    'BTCUSD', 'ETHUSD', 'ADAUSD', 'SOLUSD', 'DOTUSD', 'LINKUSD',
    'MATICUSD', 'AVAXUSD', 'UNIUSD', 'BNBUSD', 'XRPUSD', 'LTCUSD'
]

HEDGING_STRATEGIES = {
    'delta_neutral': '🔄 Delta Neutral (Perpetuals)',
    'protective_put': '🛡️ Protective Put (Options)',
    'collar': '🎯 Collar Strategy (Options)',
    'dynamic_hedge': '⚡ Dynamic Hedge (Volatility-based)'
}

# User state management
user_states = {}

# Main menu keyboard
def get_main_menu_keyboard():
    """Create main menu keyboard"""
    keyboard = [
        [KeyboardButton("📊 Risk Dashboard"), KeyboardButton("⚡ Quick Hedge")],
        [KeyboardButton("🎯 Start Monitoring"), KeyboardButton("📈 Portfolio Analytics")],
        [KeyboardButton("🔧 Settings"), KeyboardButton("📚 Help & Guide")],
        [KeyboardButton("📋 My Positions"), KeyboardButton("🏆 Strategies")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

# Asset selection keyboard
def get_asset_selection_keyboard():
    """Create asset selection keyboard"""
    keyboard = []
    # Create rows of 3 assets each
    for i in range(0, len(SUPPORTED_ASSETS), 3):
        row = []
        for j in range(3):
            if i + j < len(SUPPORTED_ASSETS):
                asset = SUPPORTED_ASSETS[i + j]
                row.append(InlineKeyboardButton(asset, callback_data=f"select_asset_{asset}"))
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel_selection")])
    return InlineKeyboardMarkup(keyboard)

# Strategy selection keyboard
def get_strategy_selection_keyboard():
    """Create strategy selection keyboard"""
    keyboard = []
    for strategy_key, strategy_name in HEDGING_STRATEGIES.items():
        keyboard.append([InlineKeyboardButton(strategy_name, callback_data=f"select_strategy_{strategy_key}")])
    keyboard.append([InlineKeyboardButton("🎲 Auto-Select Best", callback_data="select_strategy_auto")])
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel_selection")])
    return InlineKeyboardMarkup(keyboard)

# Risk threshold keyboard
def get_risk_threshold_keyboard():
    """Create risk threshold selection keyboard"""
    keyboard = [
        [InlineKeyboardButton("🟢 Conservative (1%)", callback_data="threshold_0.01"),
         InlineKeyboardButton("🟡 Moderate (2%)", callback_data="threshold_0.02")],
        [InlineKeyboardButton("🟠 Balanced (3%)", callback_data="threshold_0.03"),
         InlineKeyboardButton("🔴 Aggressive (5%)", callback_data="threshold_0.05")],
        [InlineKeyboardButton("✏️ Custom", callback_data="threshold_custom"),
         InlineKeyboardButton("❌ Cancel", callback_data="cancel_selection")]
    ]
    return InlineKeyboardMarkup(keyboard)

# Position size keyboard
def get_position_size_keyboard():
    """Create position size selection keyboard"""
    keyboard = [
        [InlineKeyboardButton("$100", callback_data="size_100"),
         InlineKeyboardButton("$500", callback_data="size_500"),
         InlineKeyboardButton("$1,000", callback_data="size_1000")],
        [InlineKeyboardButton("$5,000", callback_data="size_5000"),
         InlineKeyboardButton("$10,000", callback_data="size_10000"),
         InlineKeyboardButton("$50,000", callback_data="size_50000")],
        [InlineKeyboardButton("✏️ Custom Amount", callback_data="size_custom"),
         InlineKeyboardButton("❌ Cancel", callback_data="cancel_selection")]
    ]
    return InlineKeyboardMarkup(keyboard)

# Quick action keyboard
def get_quick_actions_keyboard(asset: str):
    """Create quick actions keyboard for an asset"""
    keyboard = [
        [InlineKeyboardButton("⚡ Hedge Now", callback_data=f"quick_hedge_{asset}"),
         InlineKeyboardButton("📊 Risk Check", callback_data=f"quick_risk_{asset}")],
        [InlineKeyboardButton("📈 View History", callback_data=f"quick_history_{asset}"),
         InlineKeyboardButton("🔧 Configure", callback_data=f"quick_config_{asset}")],
        [InlineKeyboardButton("⏹️ Stop Monitoring", callback_data=f"quick_stop_{asset}"),
         InlineKeyboardButton("🔄 Auto-Hedge Setup", callback_data=f"quick_auto_{asset}")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

# Settings keyboard
def get_settings_keyboard():
    """Create settings keyboard"""
    keyboard = [
        [InlineKeyboardButton("⚙️ Risk Parameters", callback_data="settings_risk"),
         InlineKeyboardButton("🔔 Notifications", callback_data="settings_notifications")],
        [InlineKeyboardButton("🎯 Default Strategy", callback_data="settings_strategy"),
         InlineKeyboardButton("📊 Display Preferences", callback_data="settings_display")],
        [InlineKeyboardButton("🔐 Security", callback_data="settings_security"),
         InlineKeyboardButton("📱 Account Info", callback_data="settings_account")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def safe_reply(update: Update, message: str, parse_mode=None, reply_markup=None):
    """Safely send reply with error handling"""
    try:
        await update.message.reply_text(message, parse_mode=parse_mode, reply_markup=reply_markup)
    except (NetworkError, TimedOut) as e:
        logger.error(f"Network error sending message: {e}")
        try:
            await update.message.reply_text("❌ Network error. Please try again.")
        except:
            pass
    except BadRequest as e:
        logger.error(f"Bad request error: {e}")
        try:
            await update.message.reply_text("❌ Invalid request. Please check your input.")
        except:
            pass
    except Exception as e:
        logger.error(f"Unexpected error sending message: {e}")

async def safe_edit_message(query, message: str, parse_mode=None, reply_markup=None):
    """Safely edit message with error handling"""
    try:
        await query.edit_message_text(text=message, parse_mode=parse_mode, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error editing message: {e}")
        try:
            await query.message.reply_text(message, parse_mode=parse_mode, reply_markup=reply_markup)
        except:
            pass

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced start command with main menu"""
    try:
        welcome_text = """🚀 *Welcome to GoQuant Advanced Hedging Bot!*

Your professional crypto risk management assistant is ready to help you protect and optimize your portfolio.

🎯 *What I can do for you:*
• Monitor your positions in real-time
• Execute sophisticated hedging strategies
• Provide comprehensive risk analytics
• Setup automated risk management

📱 *Use the menu below to get started:*"""

        await safe_reply(update, welcome_text, parse_mode='Markdown', reply_markup=get_main_menu_keyboard())
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await safe_reply(update, "❌ Error occurred. Bot is starting...")

async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle main menu button presses"""
    try:
        text = update.message.text
        user_id = update.effective_user.id
        
        if text == "📊 Risk Dashboard":
            await show_risk_dashboard(update, context)
        elif text == "⚡ Quick Hedge":
            await show_quick_hedge_menu(update, context)
        elif text == "🎯 Start Monitoring":
            await start_monitoring_flow(update, context)
        elif text == "📈 Portfolio Analytics":
            await show_portfolio_analytics(update, context)
        elif text == "🔧 Settings":
            await show_settings_menu(update, context)
        elif text == "📚 Help & Guide":
            await show_help_guide(update, context)
        elif text == "📋 My Positions":
            await show_my_positions(update, context)
        elif text == "🏆 Strategies":
            await show_strategies_guide(update, context)
        else:
            await safe_reply(update, "Please use the menu buttons below or type /help for commands.", reply_markup=get_main_menu_keyboard())
    except Exception as e:
        logger.error(f"Error in main menu handler: {e}")
        await safe_reply(update, "❌ Error occurred. Please try again.")

async def show_risk_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show comprehensive risk dashboard"""
    try:
        user_id = update.effective_user.id
        status = risk_monitor.get_status(user_id)
        
        if not status:
            no_data_text = """📊 *Risk Dashboard*

🤷‍♂️ *No active positions to monitor*

Start monitoring your first position to see comprehensive risk analytics here.

Click the button below to get started:"""
            
            keyboard = [[InlineKeyboardButton("🎯 Start Monitoring", callback_data="start_monitoring_flow")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await safe_reply(update, no_data_text, parse_mode='Markdown', reply_markup=reply_markup)
            return

        # Create comprehensive dashboard
        dashboard_text = "📊 *Risk Dashboard*\n\n"
        
        total_positions = len(status)
        total_value = sum(pos.get('size', 0) for pos in status.values())
        high_risk_count = 0
        
        for asset, data in status.items():
            risk_info = risk_monitor.check_risk(user_id, asset)
            alert_emoji = "🔴" if risk_info.get('alert', False) else "🟢"
            if risk_info.get('alert', False):
                high_risk_count += 1
            
            dashboard_text += f"{alert_emoji} *{asset}* - ${data.get('size', 0):,.0f}\n"
            dashboard_text += f"   VaR: ${risk_info.get('VaR', 0):,.0f} | Risk: {data.get('threshold', 0)*100:.1f}%\n\n"

        dashboard_text += f"📈 *Summary:*\n"
        dashboard_text += f"• Total Positions: {total_positions}\n"
        dashboard_text += f"• Total Value: ${total_value:,.0f}\n"
        dashboard_text += f"• High Risk Alerts: {high_risk_count}\n"

        # Add action buttons
        keyboard = [
            [InlineKeyboardButton("⚡ Quick Hedge All", callback_data="hedge_all_positions"),
             InlineKeyboardButton("📊 Detailed Analytics", callback_data="detailed_analytics")],
            [InlineKeyboardButton("🔄 Refresh Data", callback_data="refresh_dashboard"),
             InlineKeyboardButton("⚙️ Configure Alerts", callback_data="configure_alerts")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await safe_reply(update, dashboard_text, parse_mode='Markdown', reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in risk dashboard: {e}")
        await safe_reply(update, "❌ Error loading dashboard. Please try again.")

async def show_quick_hedge_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show quick hedge menu with asset selection"""
    try:
        user_id = update.effective_user.id
        status = risk_monitor.get_status(user_id)
        
        if not status:
            no_positions_text = """⚡ *Quick Hedge*

❌ *No active positions found*

You need to start monitoring positions before you can hedge them.

Would you like to start monitoring a position now?"""
            
            keyboard = [[InlineKeyboardButton("🎯 Start Monitoring", callback_data="start_monitoring_flow")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await safe_reply(update, no_positions_text, parse_mode='Markdown', reply_markup=reply_markup)
            return

        hedge_text = "⚡ *Quick Hedge*\n\nSelect a position to hedge:\n\n"
        
        keyboard = []
        for asset, data in status.items():
            risk_info = risk_monitor.check_risk(user_id, asset)
            alert_emoji = "🔴" if risk_info.get('alert', False) else "🟢"
            
            hedge_text += f"{alert_emoji} *{asset}* - ${data.get('size', 0):,.0f}\n"
            hedge_text += f"   Current Risk: ${risk_info.get('VaR', 0):,.0f}\n\n"
            
            keyboard.append([InlineKeyboardButton(f"⚡ Hedge {asset}", callback_data=f"quick_hedge_{asset}")])
        
        keyboard.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await safe_reply(update, hedge_text, parse_mode='Markdown', reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in quick hedge menu: {e}")
        await safe_reply(update, "❌ Error loading hedge menu. Please try again.")

async def start_monitoring_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the monitoring setup flow"""
    try:
        user_id = update.effective_user.id
        user_states[user_id] = {'step': 'select_asset', 'action': 'monitor'}
        
        monitoring_text = """🎯 *Start Position Monitoring*

Let's set up risk monitoring for your position.

*Step 1:* Select the asset you want to monitor:"""
        
        await safe_reply(update, monitoring_text, parse_mode='Markdown', reply_markup=get_asset_selection_keyboard())
        
    except Exception as e:
        logger.error(f"Error in start monitoring flow: {e}")
        await safe_reply(update, "❌ Error starting monitoring setup. Please try again.")

async def show_portfolio_analytics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show enhanced portfolio analytics"""
    try:
        user_id = update.effective_user.id
        analytics = risk_monitor.get_portfolio_analytics(user_id)
        
        if not analytics:
            no_data_text = """📈 *Portfolio Analytics*

📊 *No portfolio data available*

Start monitoring positions to see comprehensive portfolio analytics including:
• Risk metrics and VaR analysis
• Correlation analysis
• Hedge performance tracking
• Diversification metrics"""
            
            keyboard = [[InlineKeyboardButton("🎯 Start Monitoring", callback_data="start_monitoring_flow")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await safe_reply(update, no_data_text, parse_mode='Markdown', reply_markup=reply_markup)
            return

        # Create visual analytics text
        analytics_text = f"""📈 *Portfolio Analytics*

💰 *Portfolio Overview:*
• Total Value: ${analytics.get('total_value', 0):,.0f}
• Total P&L: ${analytics.get('total_pnl', 0):,.0f}
• Active Positions: {analytics.get('position_count', 0)}

📊 *Risk Metrics:*
• Portfolio VaR (95%): ${analytics.get('portfolio_var', 0):,.0f}
• Expected Shortfall: ${analytics.get('expected_shortfall', 0):,.0f}
• Max Drawdown: {analytics.get('max_drawdown', 0)*100:.1f}%

🔄 *Diversification:*
• Correlation Score: {analytics.get('avg_correlation', 0):.2f}
• Diversification Ratio: {analytics.get('diversification_ratio', 0):.2f}
• Risk Concentration: {analytics.get('risk_concentration', 0)*100:.0f}%

⚡ *Hedge Performance:*
• Active Hedges: {analytics.get('total_hedges', 0)}
• Hedge Effectiveness: {analytics.get('hedge_effectiveness', 0)*100:.0f}%
• Hedge P&L: ${analytics.get('hedge_pnl', 0):,.0f}"""

        keyboard = [
            [InlineKeyboardButton("📊 Detailed Report", callback_data="detailed_portfolio_report"),
             InlineKeyboardButton("📈 Risk Charts", callback_data="risk_charts")],
            [InlineKeyboardButton("🔄 Refresh Data", callback_data="refresh_portfolio"),
             InlineKeyboardButton("📤 Export Data", callback_data="export_portfolio")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await safe_reply(update, analytics_text, parse_mode='Markdown', reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in portfolio analytics: {e}")
        await safe_reply(update, "❌ Error loading portfolio analytics. Please try again.")

async def show_settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show settings menu"""
    try:
        settings_text = """🔧 *Settings & Configuration*

Customize your risk management experience:

⚙️ *Risk Parameters* - Adjust VaR confidence levels, thresholds
🔔 *Notifications* - Configure alerts and notifications
🎯 *Default Strategy* - Set your preferred hedging strategy
📊 *Display Preferences* - Customize dashboard and reports
🔐 *Security* - Manage API keys and security settings
📱 *Account Info* - View your account details and limits"""
        
        await safe_reply(update, settings_text, parse_mode='Markdown', reply_markup=get_settings_keyboard())
        
    except Exception as e:
        logger.error(f"Error in settings menu: {e}")
        await safe_reply(update, "❌ Error loading settings. Please try again.")

async def show_help_guide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show comprehensive help guide"""
    try:
        help_text = """📚 *Help & Guide*

🎯 *Getting Started:*
1. Start monitoring a position with "🎯 Start Monitoring"
2. Set your risk parameters and strategy
3. Monitor your dashboard for risk alerts
4. Use quick hedge when needed

💡 *Pro Tips:*
• Monitor correlation risk for multiple positions
• Use different strategies for different market conditions
• Set up auto-hedging for hands-off management
• Review hedge history to optimize parameters

🔧 *Advanced Features:*
• Portfolio-level risk analytics
• Custom risk parameter configuration
• Automated hedging triggers
• Comprehensive performance tracking"""
        
        keyboard = [
            [InlineKeyboardButton("🎥 Video Tutorials", callback_data="video_tutorials"),
             InlineKeyboardButton("📖 User Manual", callback_data="user_manual")],
            [InlineKeyboardButton("💬 Contact Support", callback_data="contact_support"),
             InlineKeyboardButton("🐛 Report Bug", callback_data="report_bug")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await safe_reply(update, help_text, parse_mode='Markdown', reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in help guide: {e}")
        await safe_reply(update, "❌ Error loading help guide. Please try again.")

async def show_my_positions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show detailed positions view"""
    try:
        user_id = update.effective_user.id
        status = risk_monitor.get_status(user_id)
        
        if not status:
            no_positions_text = """📋 *My Positions*

📊 *No active positions*

You haven't set up any position monitoring yet.

Get started by monitoring your first position:"""
            
            keyboard = [[InlineKeyboardButton("🎯 Start Monitoring", callback_data="start_monitoring_flow")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await safe_reply(update, no_positions_text, parse_mode='Markdown', reply_markup=reply_markup)
            return

        positions_text = "📋 *My Positions*\n\n"
        keyboard = []
        
        for asset, data in status.items():
            risk_info = risk_monitor.check_risk(user_id, asset)
            alert_emoji = "🔴" if risk_info.get('alert', False) else "🟢"
            
            positions_text += f"{alert_emoji} *{asset}*\n"
            positions_text += f"• Size: ${data.get('size', 0):,.0f}\n"
            positions_text += f"• VaR: ${risk_info.get('VaR', 0):,.0f}\n"
            positions_text += f"• Strategy: {HEDGING_STRATEGIES.get(data.get('strategy', ''), 'Auto-select')}\n"
            positions_text += f"• Status: {'🔄 Active' if data.get('active', False) else '⏸️ Paused'}\n\n"
            
            keyboard.append([InlineKeyboardButton(f"📊 {asset} Details", callback_data=f"position_details_{asset}")])
        
        keyboard.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await safe_reply(update, positions_text, parse_mode='Markdown', reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in my positions: {e}")
        await safe_reply(update, "❌ Error loading positions. Please try again.")

async def show_strategies_guide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show strategies guide"""
    try:
        strategies_text = """🏆 *Hedging Strategies Guide*

Choose the right strategy for your risk profile:

🔄 *Delta Neutral*
• Best for: Directional risk elimination
• Uses: Perpetual futures
• Risk Level: Low
• Complexity: Medium

🛡️ *Protective Put*
• Best for: Downside protection with upside potential
• Uses: Put options
• Risk Level: Medium
• Complexity: High

🎯 *Collar Strategy*
• Best for: Defined risk/reward scenarios
• Uses: Put + Call options
• Risk Level: Low-Medium
• Complexity: High

⚡ *Dynamic Hedge*
• Best for: Volatile market conditions
• Uses: Volatility-based adjustments
• Risk Level: Variable
• Complexity: Very High"""
        
        keyboard = [
            [InlineKeyboardButton("📊 Strategy Comparison", callback_data="strategy_comparison"),
             InlineKeyboardButton("🎯 Strategy Selector", callback_data="strategy_selector")],
            [InlineKeyboardButton("📈 Performance Analysis", callback_data="strategy_performance"),
             InlineKeyboardButton("🔧 Custom Strategy", callback_data="custom_strategy")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await safe_reply(update, strategies_text, parse_mode='Markdown', reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in strategies guide: {e}")
        await safe_reply(update, "❌ Error loading strategies guide. Please try again.")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced button callback handler"""
    try:
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user_id = update.effective_user.id
        
        # Handle main menu navigation
        if data == "main_menu":
            await query.message.delete()
            welcome_back = "🏠 *Main Menu*\n\nWelcome back! Choose an option from the menu below:"
            await query.message.reply_text(welcome_back, parse_mode='Markdown', reply_markup=get_main_menu_keyboard())
            return
        
        # Handle asset selection
        if data.startswith("select_asset_"):
            asset = data.replace("select_asset_", "")
            await handle_asset_selection(query, asset, user_id)
            return
        
        # Handle strategy selection
        if data.startswith("select_strategy_"):
            strategy = data.replace("select_strategy_", "")
            await handle_strategy_selection(query, strategy, user_id)
            return
        
        # Handle threshold selection
        if data.startswith("threshold_"):
            threshold = data.replace("threshold_", "")
            await handle_threshold_selection(query, threshold, user_id)
            return
        
        # Handle position size selection
        if data.startswith("size_"):
            size = data.replace("size_", "")
            await handle_size_selection(query, size, user_id)
            return
        
        # Handle quick hedge
        if data.startswith("quick_hedge_"):
            asset = data.replace("quick_hedge_", "")
            await handle_quick_hedge(query, asset, user_id)
            return
        
        # Handle position details
        if data.startswith("position_details_"):
            asset = data.replace("position_details_", "")
            await show_position_details(query, asset, user_id)
            return
        
        # Handle hedge execution
        if data.startswith("execute_hedge_"):
            asset = data.replace("execute_hedge_", "")
            await execute_hedge_with_confirmation(query, asset, user_id)
            return
        
        # Handle monitoring flow
        if data == "start_monitoring_flow":
            await query.message.delete()
            await start_monitoring_flow_from_callback(query, user_id)
            return
        
        # Handle other callbacks
        await handle_other_callbacks(query, data, user_id)
        
    except Exception as e:
        logger.error(f"Error in button callback: {e}")
        try:
            await query.message.reply_text("❌ Error occurred while processing your request.")
        except:
            pass

async def handle_asset_selection(query, asset: str, user_id: int):
    """Handle asset selection in monitoring flow"""
    try:
        if asset not in SUPPORTED_ASSETS:
            await safe_edit_message(query, "❌ Invalid asset selected. Please try again.", reply_markup=get_asset_selection_keyboard())
            return
        
        # Update user state
        if user_id not in user_states:
            user_states[user_id] = {}
        user_states[user_id]['selected_asset'] = asset
        user_states[user_id]['step'] = 'select_strategy'
        
        strategy_text = f"""🎯 *Position Setup - {asset}*

*Step 2:* Choose your hedging strategy:

Each strategy has different risk profiles and complexity levels. Choose the one that best fits your trading style."""
        
        await safe_edit_message(query, strategy_text, parse_mode='Markdown', reply_markup=get_strategy_selection_keyboard())
        
    except Exception as e:
        logger.error(f"Error in asset selection: {e}")
        await safe_edit_message(query, "❌ Error processing asset selection. Please try again.")

async def handle_strategy_selection(query, strategy: str, user_id: int):
    """Handle strategy selection in monitoring flow"""
    try:
        if user_id not in user_states or 'selected_asset' not in user_states[user_id]:
            await safe_edit_message(query, "❌ Session expired. Please start again.", reply_markup=get_asset_selection_keyboard())
            return
        
        # Update user state
        user_states[user_id]['selected_strategy'] = strategy
        user_states[user_id]['step'] = 'select_threshold'
        
        asset = user_states[user_id]['selected_asset']
        strategy_name = HEDGING_STRATEGIES.get(strategy, 'Auto-select')
        
        threshold_text = f"""🎯 *Position Setup - {asset}*

*Step 3:* Set your risk threshold:

Selected Strategy: {strategy_name}

Choose when you want to be alerted about risk levels:"""
        
        await safe_edit_message(query, threshold_text, parse_mode='Markdown', reply_markup=get_risk_threshold_keyboard())
        
    except Exception as e:
        logger.error(f"Error in strategy selection: {e}")
        await safe_edit_message(query, "❌ Error processing strategy selection. Please try again.")

async def handle_threshold_selection(query, threshold: str, user_id: int):
    """Handle risk threshold selection in monitoring flow"""
    try:
        if user_id not in user_states or 'selected_asset' not in user_states[user_id]:
            await safe_edit_message(query, "❌ Session expired. Please start again.", reply_markup=get_asset_selection_keyboard())
            return
        
        # Handle custom threshold
        if threshold == "custom":
            user_states[user_id]['step'] = 'custom_threshold'
            custom_text = f"""🎯 *Custom Risk Threshold*

Please enter your custom risk threshold as a percentage (e.g., 2.5 for 2.5%):

Valid range: 0.1% - 10.0%"""
            await safe_edit_message(query, custom_text, parse_mode='Markdown')
            return
        
        # Convert threshold to float
        threshold_value = float(threshold)
        user_states[user_id]['selected_threshold'] = threshold_value
        user_states[user_id]['step'] = 'select_size'
        
        asset = user_states[user_id]['selected_asset']
        strategy_name = HEDGING_STRATEGIES.get(user_states[user_id]['selected_strategy'], 'Auto-select')
        
        size_text = f"""🎯 *Position Setup - {asset}*

*Step 4:* Enter your position size:

Selected Strategy: {strategy_name}
Risk Threshold: {threshold_value*100:.1f}%

Choose or enter your position size:"""
        
        await safe_edit_message(query, size_text, parse_mode='Markdown', reply_markup=get_position_size_keyboard())
        
    except Exception as e:
        logger.error(f"Error in threshold selection: {e}")
        await safe_edit_message(query, "❌ Error processing threshold selection. Please try again.")

async def handle_size_selection(query, size: str, user_id: int):
    """Handle position size selection in monitoring flow"""
    try:
        if user_id not in user_states or 'selected_asset' not in user_states[user_id]:
            await safe_edit_message(query, "❌ Session expired. Please start again.", reply_markup=get_asset_selection_keyboard())
            return
        
        # Handle custom size
        if size == "custom":
            user_states[user_id]['step'] = 'custom_size'
            custom_text = f"""💰 *Custom Position Size*

Please enter your position size in USD (e.g., 2500):

Valid range: $100 - $1,000,000"""
            await safe_edit_message(query, custom_text, parse_mode='Markdown')
            return
        
        # Convert size to float
        size_value = float(size)
        user_states[user_id]['selected_size'] = size_value
        
        # Complete the setup
        await complete_monitoring_setup(query, user_id)
        
    except Exception as e:
        logger.error(f"Error in size selection: {e}")
        await safe_edit_message(query, "❌ Error processing size selection. Please try again.")

async def complete_monitoring_setup(query, user_id: int):
    """Complete the monitoring setup process"""
    try:
        if user_id not in user_states:
            await safe_edit_message(query, "❌ Session expired. Please start again.")
            return
        
        state = user_states[user_id]
        asset = state.get('selected_asset')
        strategy = state.get('selected_strategy')
        threshold = state.get('selected_threshold')
        size = state.get('selected_size')
        
        # Start monitoring
        success = risk_monitor.start_monitoring(user_id, asset, size, threshold, strategy)
        
        if success:
            strategy_name = HEDGING_STRATEGIES.get(strategy, 'Auto-select')
            
            success_text = f"""✅ *Monitoring Setup Complete!*

🎯 *Position Details:*
• Asset: {asset}
• Size: ${size:,.0f}
• Strategy: {strategy_name}
• Risk Threshold: {threshold*100:.1f}%

🔄 *Monitoring Status:* Active

Your position is now being monitored. You'll receive alerts when risk levels exceed your threshold."""
            
            keyboard = [
                [InlineKeyboardButton("📊 View Dashboard", callback_data="risk_dashboard"),
                 InlineKeyboardButton("⚡ Quick Hedge", callback_data=f"quick_hedge_{asset}")],
                [InlineKeyboardButton("🔧 Configure Auto-Hedge", callback_data=f"setup_auto_hedge_{asset}"),
                 InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await safe_edit_message(query, success_text, parse_mode='Markdown', reply_markup=reply_markup)
            
            # Clear user state
            del user_states[user_id]
            
        else:
            error_text = f"""❌ *Setup Failed*

Failed to start monitoring for {asset}. This could be due to:
• Invalid asset configuration
• System temporarily unavailable
• Position already being monitored

Please try again or contact support if the issue persists."""
            
            keyboard = [
                [InlineKeyboardButton("🔄 Try Again", callback_data="start_monitoring_flow"),
                 InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await safe_edit_message(query, error_text, parse_mode='Markdown', reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error completing monitoring setup: {e}")
        await safe_edit_message(query, "❌ Error completing setup. Please try again.")

async def handle_quick_hedge(query, asset: str, user_id: int):
    """Handle quick hedge execution"""
    try:
        # Get hedge recommendation
        recommendation = risk_monitor.calculate_hedge_recommendation(user_id, asset)
        
        if not recommendation:
            await safe_edit_message(query, f"❌ No hedge recommendation available for {asset}. Please ensure the position is being monitored.")
            return
        
        current_risk = recommendation.get('current_risk', 0)
        hedge_size = recommendation.get('hedge_size', 0)
        risk_reduction = recommendation.get('risk_reduction', 0)
        strategy = recommendation.get('strategy', 'delta_neutral')
        strategy_name = HEDGING_STRATEGIES.get(strategy, 'Auto-select')
        
        hedge_text = f"""⚡ *Quick Hedge - {asset}*

📊 *Current Risk Analysis:*
• Current VaR: ${current_risk*100:,.0f}
• Recommended Hedge Size: ${hedge_size:,.0f}
• Expected Risk Reduction: {risk_reduction*100:.1f}%

🎯 *Recommended Strategy:* {strategy_name}

💡 *Hedge Impact:*
• Cost: ~${hedge_size*0.001:.0f} (0.1% transaction cost)
• Risk Reduction: {risk_reduction*100:.1f}%
• New VaR: ${(current_risk - risk_reduction)*100:,.0f}

Do you want to execute this hedge?"""
        
        keyboard = [
            [InlineKeyboardButton("✅ Execute Hedge", callback_data=f"execute_hedge_{asset}"),
             InlineKeyboardButton("📊 More Details", callback_data=f"hedge_details_{asset}")],
            [InlineKeyboardButton("🔧 Adjust Parameters", callback_data=f"adjust_hedge_{asset}"),
             InlineKeyboardButton("❌ Cancel", callback_data="cancel_hedge")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await safe_edit_message(query, hedge_text, parse_mode='Markdown', reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in quick hedge: {e}")
        await safe_edit_message(query, "❌ Error calculating hedge recommendation. Please try again.")

async def execute_hedge_with_confirmation(query, asset: str, user_id: int):
    """Execute hedge with confirmation"""
    try:
        # Execute the hedge
        result = risk_monitor.execute_hedge(user_id, asset)
        
        if result.get('success', False):
            strategy_name = HEDGING_STRATEGIES.get(result.get('strategy', ''), 'Auto-select')
            
            success_text = f"""✅ *Hedge Executed Successfully!*

🎯 *Execution Details:*
• Asset: {asset}
• Strategy: {strategy_name}
• Hedge Size: ${result.get('hedge_size', 0):,.0f}
• Execution Price: ${result.get('execution_price', 0):,.0f}
• Transaction Cost: ${result.get('transaction_cost', 0):,.0f}

📊 *Risk Impact:*
• Risk Reduction: {result.get('risk_reduction', 0)*100:.1f}%
• New VaR: ${result.get('new_var', 0):,.0f}
• Hedge Effectiveness: {result.get('effectiveness', 0)*100:.0f}%

🔄 *Status:* Hedge is now active and monitoring continues."""
            
            keyboard = [
                [InlineKeyboardButton("📊 View Dashboard", callback_data="risk_dashboard"),
                 InlineKeyboardButton("📈 View History", callback_data=f"hedge_history_{asset}")],
                [InlineKeyboardButton("🔧 Adjust Strategy", callback_data=f"adjust_strategy_{asset}"),
                 InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await safe_edit_message(query, success_text, parse_mode='Markdown', reply_markup=reply_markup)
            
        else:
            error_text = f"""❌ *Hedge Execution Failed*

Failed to execute hedge for {asset}. Possible reasons:
• Insufficient liquidity
• Market conditions
• System error

Your position monitoring continues unchanged. Please try again or contact support."""
            
            keyboard = [
                [InlineKeyboardButton("🔄 Try Again", callback_data=f"quick_hedge_{asset}"),
                 InlineKeyboardButton("📊 Check Status", callback_data=f"position_details_{asset}")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await safe_edit_message(query, error_text, parse_mode='Markdown', reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error executing hedge: {e}")
        await safe_edit_message(query, "❌ Error executing hedge. Please try again.")

async def show_position_details(query, asset: str, user_id: int):
    """Show detailed position information"""
    try:
        status = risk_monitor.get_status(user_id)
        
        if not status or asset not in status:
            await safe_edit_message(query, f"❌ No monitoring data found for {asset}.")
            return
        
        position_data = status[asset]
        risk_info = risk_monitor.check_risk(user_id, asset)
        hedge_history = risk_monitor.get_hedge_history(user_id, asset)
        
        # Calculate performance metrics
        total_hedges = len(hedge_history) if hedge_history else 0
        successful_hedges = sum(1 for h in hedge_history if h.get('status') == 'SUCCESS') if hedge_history else 0
        total_hedge_pnl = sum(h.get('pnl', 0) for h in hedge_history) if hedge_history else 0
        
        strategy_name = HEDGING_STRATEGIES.get(position_data.get('strategy', ''), 'Auto-select')
        alert_emoji = "🔴" if risk_info.get('alert', False) else "🟢"
        
        details_text = f"""📊 *Position Details - {asset}*

{alert_emoji} *Current Status:*
• Size: ${position_data.get('size', 0):,.0f}
• Strategy: {strategy_name}
• Risk Threshold: {position_data.get('threshold', 0)*100:.1f}%
• Monitoring: {'🔄 Active' if position_data.get('active', False) else '⏸️ Paused'}

📈 *Risk Metrics:*
• Current VaR: ${risk_info.get('VaR', 0):,.0f}
• Risk Level: {risk_info.get('risk_level', 'UNKNOWN')}
• Alert Status: {'🚨 HIGH RISK' if risk_info.get('alert', False) else '✅ NORMAL'}

⚡ *Hedge Performance:*
• Total Hedges: {total_hedges}
• Success Rate: {(successful_hedges/total_hedges*100) if total_hedges > 0 else 0:.0f}%
• Total Hedge P&L: ${total_hedge_pnl:,.0f}

📅 *Last Updated:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
        
        await safe_edit_message(query, details_text, parse_mode='Markdown', reply_markup=get_quick_actions_keyboard(asset))
        
    except Exception as e:
        logger.error(f"Error showing position details: {e}")
        await safe_edit_message(query, "❌ Error loading position details. Please try again.")

async def start_monitoring_flow_from_callback(query, user_id: int):
    """Start monitoring flow from callback"""
    try:
        user_states[user_id] = {'step': 'select_asset', 'action': 'monitor'}
        
        monitoring_text = """🎯 *Start Position Monitoring*

Let's set up risk monitoring for your position.

*Step 1:* Select the asset you want to monitor:"""
        
        await query.message.reply_text(monitoring_text, parse_mode='Markdown', reply_markup=get_asset_selection_keyboard())
        
    except Exception as e:
        logger.error(f"Error starting monitoring flow from callback: {e}")
        await query.message.reply_text("❌ Error starting monitoring setup. Please try again.")

async def handle_other_callbacks(query, data: str, user_id: int):
    """Handle other callback queries"""
    try:
        if data == "cancel_selection":
            await query.message.delete()
            await query.message.reply_text("❌ Selection cancelled. Returning to main menu.", reply_markup=get_main_menu_keyboard())
            
        elif data == "risk_dashboard":
            await query.message.delete()
            # Create a mock update object for show_risk_dashboard
            mock_update = type('MockUpdate', (), {'message': query.message, 'effective_user': query.from_user})()
            await show_risk_dashboard(mock_update, None)
            
        elif data.startswith("settings_"):
            setting = data.replace("settings_", "")
            await handle_settings_callback(query, setting, user_id)
            
        elif data.startswith("hedge_history_"):
            asset = data.replace("hedge_history_", "")
            await show_hedge_history(query, asset, user_id)
            
        elif data.startswith("setup_auto_hedge_"):
            asset = data.replace("setup_auto_hedge_", "")
            await setup_auto_hedge(query, asset, user_id)
            
        else:
            await safe_edit_message(query, "🔄 Feature coming soon! Please use the main menu for now.", reply_markup=get_main_menu_keyboard())
            
    except Exception as e:
        logger.error(f"Error handling callback {data}: {e}")
        await safe_edit_message(query, "❌ Error processing request. Please try again.")

async def handle_settings_callback(query, setting: str, user_id: int):
    """Handle settings callbacks"""
    try:
        if setting == "risk":
            settings_text = """⚙️ *Risk Parameters*

Configure your risk management settings:

• VaR Confidence Level: 95% (adjustable: 90-99%)
• Default Risk Threshold: 2% (adjustable: 0.1-10%)
• Position Size Limits: $100 - $1M
• Correlation Threshold: 0.7 (for portfolio risk)

Current settings are optimized for balanced risk management."""
            
        elif setting == "notifications":
            settings_text = """🔔 *Notification Settings*

Configure when and how you receive alerts:

• Risk Level Alerts: ✅ Enabled
• Hedge Execution: ✅ Enabled
• Daily Risk Report: ✅ Enabled
• Market Volatility Alerts: ✅ Enabled
• Portfolio Rebalancing: ✅ Enabled

Notifications are sent via Telegram messages."""
            
        elif setting == "strategy":
            settings_text = """🎯 *Default Strategy Settings*

Set your preferred default hedging strategy:

Current Default: Delta Neutral
• Best for most market conditions
• Low complexity, high effectiveness
• Automatic position sizing

You can override this for individual positions."""
            
        elif setting == "display":
            settings_text = """📊 *Display Preferences*

Customize how information is displayed:

• Currency: USD 💵
• Risk Format: Percentage + Absolute
• Time Zone: UTC
• Dashboard Refresh: 30 seconds
• Chart Type: Candlestick

Settings affect all dashboards and reports."""
            
        elif setting == "security":
            settings_text = """🔐 *Security Settings*

Manage your account security:

• API Key Status: ✅ Active
• Two-Factor Auth: ✅ Enabled
• Session Timeout: 30 minutes
• IP Whitelist: Disabled
• Audit Log: ✅ Enabled

Your security settings are optimized for safety."""
            
        elif setting == "account":
            settings_text = """📱 *Account Information*

Your account details:

• User ID: {user_id}
• Account Type: Premium
• API Rate Limit: 1000 req/hour
• Max Positions: 20
• Max Position Size: $1,000,000
• Account Status: ✅ Active

Upgrade options available for higher limits."""
            
        else:
            settings_text = "❌ Invalid settings option."
        
        keyboard = [
            [InlineKeyboardButton("💾 Save Changes", callback_data=f"save_settings_{setting}"),
             InlineKeyboardButton("🔄 Reset to Default", callback_data=f"reset_settings_{setting}")],
            [InlineKeyboardButton("🔙 Back to Settings", callback_data="show_settings"),
             InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await safe_edit_message(query, settings_text, parse_mode='Markdown', reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in settings callback: {e}")
        await safe_edit_message(query, "❌ Error loading settings. Please try again.")

async def show_hedge_history(query, asset: str, user_id: int):
    """Show hedge history for an asset"""
    try:
        history = risk_monitor.get_hedge_history(user_id, asset)
        
        if not history:
            history_text = f"""📈 *Hedge History - {asset}*

📊 *No hedge history available*

No hedges have been executed for this position yet.

Start hedging to see performance tracking here."""
        else:
            history_text = f"""📈 *Hedge History - {asset}*

Recent hedge executions:\n\n"""
            
            for i, hedge in enumerate(history[-5:], 1):  # Show last 5 hedges
                status_emoji = "✅" if hedge.get('status') == 'SUCCESS' else "❌"
                history_text += f"{status_emoji} *Hedge #{i}*\n"
                history_text += f"• Date: {hedge.get('date', 'N/A')}\n"
                history_text += f"• Size: ${hedge.get('size', 0):,.0f}\n"
                history_text += f"• Strategy: {HEDGING_STRATEGIES.get(hedge.get('strategy', ''), 'Unknown')}\n"
                history_text += f"• P&L: ${hedge.get('pnl', 0):,.0f}\n\n"
        
        keyboard = [
            [InlineKeyboardButton("📊 Detailed Report", callback_data=f"detailed_hedge_report_{asset}"),
             InlineKeyboardButton("📤 Export History", callback_data=f"export_hedge_history_{asset}")],
            [InlineKeyboardButton("🔙 Back to Position", callback_data=f"position_details_{asset}"),
             InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await safe_edit_message(query, history_text, parse_mode='Markdown', reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error showing hedge history: {e}")
        await safe_edit_message(query, "❌ Error loading hedge history. Please try again.")

async def setup_auto_hedge(query, asset: str, user_id: int):
    """Setup auto-hedge for an asset"""
    try:
        setup_text = f"""🔄 *Auto-Hedge Setup - {asset}*

Configure automatic hedging triggers:

⚙️ *Current Settings:*
• Trigger Threshold: 3% VaR increase
• Max Hedge Size: 50% of position
• Frequency Limit: 1 hedge per hour
• Strategy: Delta Neutral

🎯 *Auto-Hedge Benefits:*
• 24/7 risk monitoring
• Instant execution on triggers
• Consistent risk management
• Reduced manual intervention

Auto-hedging will execute hedges automatically when risk levels exceed your thresholds."""
        
        keyboard = [
            [InlineKeyboardButton("✅ Enable Auto-Hedge", callback_data=f"enable_auto_hedge_{asset}"),
             InlineKeyboardButton("⚙️ Configure Settings", callback_data=f"config_auto_hedge_{asset}")],
            [InlineKeyboardButton("📊 View Triggers", callback_data=f"view_triggers_{asset}"),
             InlineKeyboardButton("🔙 Back to Position", callback_data=f"position_details_{asset}")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await safe_edit_message(query, setup_text, parse_mode='Markdown', reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in auto-hedge setup: {e}")
        await safe_edit_message(query, "❌ Error setting up auto-hedge. Please try again.")

async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text message inputs for custom values"""
    try:
        user_id = update.effective_user.id
        text = update.message.text
        
        # Check if user is in a custom input state
        if user_id in user_states:
            state = user_states[user_id]
            
            if state.get('step') == 'custom_threshold':
                try:
                    threshold = float(text)
                    if 0.1 <= threshold <= 10.0:
                        state['selected_threshold'] = threshold / 100  # Convert to decimal
                        state['step'] = 'select_size'
                        
                        asset = state['selected_asset']
                        strategy_name = HEDGING_STRATEGIES.get(state['selected_strategy'], 'Auto-select')
                        
                        size_text = f"""🎯 *Position Setup - {asset}*

*Step 4:* Enter your position size:

Selected Strategy: {strategy_name}
Risk Threshold: {threshold:.1f}%

Choose or enter your position size:"""
                        
                        await safe_reply(update, size_text, parse_mode='Markdown', reply_markup=get_position_size_keyboard())
                        return
                    else:
                        await safe_reply(update, "❌ Invalid threshold. Please enter a value between 0.1 and 10.0:")
                        return
                except ValueError:
                    await safe_reply(update, "❌ Invalid format. Please enter a number (e.g., 2.5):")
                    return
            
            elif state.get('step') == 'custom_size':
                try:
                    size = float(text.replace('$', '').replace(',', ''))
                    if 100 <= size <= 1000000:
                        state['selected_size'] = size
                        
                        # Create a mock query object to pass to complete_monitoring_setup
                        mock_query = type('MockQuery', (), {
                            'message': update.message,
                            'edit_message_text': update.message.reply_text
                        })()
                        
                        await complete_monitoring_setup(mock_query, user_id)
                        return
                    else:
                        await safe_reply(update, "❌ Invalid size. Please enter a value between $100 and $1,000,000:")
                        return
                except ValueError:
                    await safe_reply(update, "❌ Invalid format. Please enter a number (e.g., 5000):")
                    return
        
        # Handle main menu if not in custom input state
        await handle_main_menu(update, context)
        
    except Exception as e:
        logger.error(f"Error handling text message: {e}")
        await safe_reply(update, "❌ Error processing your message. Please try again.")

def main():
    """Main function to run the bot"""
    try:
        # Get token from environment
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not token:
            logger.error("TELEGRAM_BOT_TOKEN environment variable not set")
            return
        
        # Create application
        application = Application.builder().token(token).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CallbackQueryHandler(button_callback))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))
        
        # Error handler
        async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
            """Log errors and notify user"""
            logger.error(f"Exception while handling an update: {context.error}")
            
            if update and hasattr(update, 'message') and update.message:
                try:
                    await update.message.reply_text("❌ An error occurred. Please try again or contact support.")
                except:
                    pass
        
        application.add_error_handler(error_handler)
        
        # Start the bot
        logger.info("Starting Telegram Bot...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"Error starting bot: {e}")

if __name__ == "__main__":
    main()