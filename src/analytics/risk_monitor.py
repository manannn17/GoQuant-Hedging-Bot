# -*- coding: utf-8 -*-
# analytics/risk_monitor.py
import logging
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import numpy as np
from threading import Lock
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RiskMonitor:
    """Advanced risk monitoring system for cryptocurrency portfolios"""
    
    def __init__(self):
        self.active_positions = {}  # {user_id: {asset: position_data}}
        self.hedge_history = {}     # {user_id: {asset: [hedge_records]}}
        self.risk_params = {}       # {user_id: {asset: risk_parameters}}
        self.auto_hedge_config = {} # {user_id: {asset: auto_hedge_settings}}
        self.lock = Lock()
        
        # Default risk parameters
        self.default_risk_params = {
            'var_confidence': 0.95,
            'var_confidence_99': 0.99,
            'monitoring_frequency': 60,  # seconds
            'correlation_threshold': 0.7,
            'volatility_threshold': 0.05,
            'max_position_size': 100000,  # USD
            'min_hedge_size': 100  # USD
        }
        
        logger.info("Risk monitoring system initialized")
    
    def start_monitoring(self, user_id: int, asset: str, size: float, threshold: float, strategy: str = None) -> bool:
        """Start monitoring a position with proper error handling"""
        try:
            with self.lock:
                if user_id not in self.active_positions:
                    self.active_positions[user_id] = {}
                
                position_data = {
                    'asset': asset,
                    'size': size,
                    'threshold': threshold,
                    'strategy': strategy,
                    'start_time': datetime.now(),
                    'active': True,
                    'entry_price': self._get_current_price(asset),
                    'current_price': self._get_current_price(asset),
                    'pnl': 0.0,
                    'var_95': 0.0,
                    'var_99': 0.0,
                    'active_hedges': 0,
                    'total_hedge_size': 0.0,
                    'hedge_effectiveness': 0.0,
                    'last_hedge_time': None,
                    'auto_hedge': False
                }
                
                self.active_positions[user_id][asset] = position_data
                
                # Initialize risk parameters if not exists
                if user_id not in self.risk_params:
                    self.risk_params[user_id] = {}
                if asset not in self.risk_params[user_id]:
                    self.risk_params[user_id][asset] = self.default_risk_params.copy()
                
                # Initialize hedge history
                if user_id not in self.hedge_history:
                    self.hedge_history[user_id] = {}
                if asset not in self.hedge_history[user_id]:
                    self.hedge_history[user_id][asset] = []
                
                logger.info(f"Started monitoring {asset} for user {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error starting monitoring: {e}")
            return False
    
    def stop_monitoring(self, user_id: int, asset: str) -> bool:
        """Stop monitoring a specific asset"""
        try:
            with self.lock:
                if (user_id in self.active_positions and 
                    asset in self.active_positions[user_id]):
                    
                    self.active_positions[user_id][asset]['active'] = False
                    logger.info(f"Stopped monitoring {asset} for user {user_id}")
                    return True
                    
                return False
                
        except Exception as e:
            logger.error(f"Error stopping monitoring: {e}")
            return False
    
    def get_status(self, user_id: int) -> Dict:
        """Get current monitoring status for a user"""
        try:
            with self.lock:
                if user_id not in self.active_positions:
                    return {}
                
                # Update current prices and calculate metrics
                status = {}
                for asset, position in self.active_positions[user_id].items():
                    if position['active']:
                        # Update current price and PnL
                        current_price = self._get_current_price(asset)
                        entry_price = position['entry_price']
                        size = position['size']
                        
                        pnl = (current_price - entry_price) * size / entry_price
                        position['current_price'] = current_price
                        position['pnl'] = pnl
                        
                        # Calculate VaR
                        historical_returns = self._get_historical_returns(asset)
                        position['var_95'] = self._calculate_var(historical_returns, size, 0.95)
                        position['var_99'] = self._calculate_var(historical_returns, size, 0.99)
                        
                        status[asset] = position.copy()
                
                return status
                
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return {}
    
    def check_risk(self, user_id: int, asset: str) -> Dict:
        """Check current risk level for a position"""
        try:
            with self.lock:
                if (user_id not in self.active_positions or 
                    asset not in self.active_positions[user_id]):
                    return {"VaR": 0, "alert": False}
                
                position = self.active_positions[user_id][asset]
                
                # Calculate current risk metrics
                current_price = self._get_current_price(asset)
                entry_price = position['entry_price']
                size = position['size']
                threshold = position['threshold']
                
                # Calculate VaR
                historical_returns = self._get_historical_returns(asset)
                var_95 = self._calculate_var(historical_returns, size, 0.95)
                var_99 = self._calculate_var(historical_returns, size, 0.99)
                
                # Check if threshold is breached
                risk_ratio = abs(var_95) / size if size > 0 else 0
                alert = risk_ratio > threshold
                
                # Calculate additional metrics
                volatility = self._calculate_volatility(historical_returns)
                correlation_risk = self._calculate_correlation_risk(user_id, asset)
                
                return {
                    "VaR": var_95,
                    "VaR_99": var_99,
                    "alert": alert,
                    "risk_ratio": risk_ratio,
                    "threshold": threshold,
                    "volatility": volatility,
                    "correlation_risk": correlation_risk,
                    "current_price": current_price,
                    "entry_price": entry_price,
                    "pnl": (current_price - entry_price) * size / entry_price,
                    "risk_level": "HIGH" if alert else "NORMAL"
                }
                
        except Exception as e:
            logger.error(f"Error checking risk: {e}")
            return {"VaR": 0, "alert": False}
    
    def calculate_hedge_recommendation(self, user_id: int, asset: str) -> Dict:
        """Calculate optimal hedge recommendation"""
        try:
            with self.lock:
                if (user_id not in self.active_positions or 
                    asset not in self.active_positions[user_id]):
                    return {}
                
                position = self.active_positions[user_id][asset]
                risk_data = self.check_risk(user_id, asset)
                
                # Determine optimal hedge strategy
                strategy = position.get('strategy', 'delta_neutral')
                current_price = risk_data['current_price']
                position_size = position['size']
                var_95 = risk_data['VaR']
                
                # Calculate hedge size based on strategy
                if strategy == 'delta_neutral':
                    hedge_size = position_size * 0.8  # 80% hedge ratio
                    hedge_instrument = 'PERPETUAL'
                elif strategy == 'protective_put':
                    hedge_size = position_size * 0.5  # 50% hedge ratio
                    hedge_instrument = 'PUT_OPTION'
                elif strategy == 'collar':
                    hedge_size = position_size * 0.6  # 60% hedge ratio
                    hedge_instrument = 'COLLAR'
                else:  # dynamic_hedge
                    volatility = risk_data['volatility']
                    hedge_size = position_size * min(0.9, volatility * 10)  # Volatility-based sizing
                    hedge_instrument = 'DYNAMIC'
                
                # Calculate expected risk reduction
                current_risk = abs(var_95) / position_size if position_size > 0 else 0
                expected_risk_reduction = min(0.8, hedge_size / position_size * 0.7)  # Simplified calculation
                
                recommendation = {
                    'asset': asset,
                    'action': 'HEDGE' if risk_data['alert'] else 'MONITOR',
                    'strategy': strategy,
                    'hedge_size': hedge_size,
                    'hedge_instrument': hedge_instrument,
                    'position_size': position_size,
                    'current_risk': current_risk,
                    'expected_risk_reduction': expected_risk_reduction,
                    'execution_price': current_price,
                    'estimated_cost': hedge_size * 0.001,  # 0.1% estimated cost
                    'confidence': 0.85,  # Confidence in recommendation
                    'urgency': 'HIGH' if risk_data['alert'] else 'NORMAL'
                }
                
                return recommendation
                
        except Exception as e:
            logger.error(f"Error calculating hedge recommendation: {e}")
            return {}
    
    def execute_hedge(self, user_id: int, asset: str) -> Dict:
        """Execute hedge for a position"""
        try:
            with self.lock:
                recommendation = self.calculate_hedge_recommendation(user_id, asset)
                
                if not recommendation:
                    return {"success": False, "error": "No recommendation available"}
                
                # Simulate hedge execution
                execution_id = str(uuid.uuid4())
                execution_time = datetime.now()
                
                # Update position with hedge information
                if (user_id in self.active_positions and 
                    asset in self.active_positions[user_id]):
                    
                    position = self.active_positions[user_id][asset]
                    position['active_hedges'] += 1
                    position['total_hedge_size'] += recommendation['hedge_size']
                    position['last_hedge_time'] = execution_time.isoformat()
                    position['hedge_effectiveness'] = min(0.95, position['hedge_effectiveness'] + 0.2)
                
                # Record hedge in history
                hedge_record = {
                    'id': execution_id,
                    'date': execution_time.isoformat(),
                    'action': 'HEDGE_OPEN',
                    'strategy': recommendation['strategy'],
                    'size': recommendation['hedge_size'],
                    'price': recommendation['execution_price'],
                    'cost': recommendation['estimated_cost'],
                    'pnl': 0.0,  # Initial PnL
                    'status': 'ACTIVE',
                    'risk_reduction': recommendation['expected_risk_reduction']
                }
                
                if user_id not in self.hedge_history:
                    self.hedge_history[user_id] = {}
                if asset not in self.hedge_history[user_id]:
                    self.hedge_history[user_id][asset] = []
                
                self.hedge_history[user_id][asset].append(hedge_record)
                
                # Calculate new risk metrics
                new_risk = self.check_risk(user_id, asset)
                
                result = {
                    "success": True,
                    "execution_id": execution_id,
                    "strategy": recommendation['strategy'],
                    "hedge_size": recommendation['hedge_size'],
                    "execution_price": recommendation['execution_price'],
                    "transaction_cost": recommendation['estimated_cost'],
                    "risk_reduction": recommendation['expected_risk_reduction'],
                    "new_var": new_risk['VaR'],
                    "effectiveness": recommendation['expected_risk_reduction'],
                    "timestamp": execution_time.isoformat()
                }
                
                logger.info(f"Hedge executed for user {user_id}, asset {asset}: {execution_id}")
                return result
                
        except Exception as e:
            logger.error(f"Error executing hedge: {e}")
            return {"success": False, "error": str(e)}
    
    def get_hedge_history(self, user_id: int, asset: str, days: int = 30) -> List[Dict]:
        """Get hedge history for an asset"""
        try:
            with self.lock:
                if (user_id not in self.hedge_history or 
                    asset not in self.hedge_history[user_id]):
                    return []
                
                # Filter by date range
                cutoff_date = datetime.now() - timedelta(days=days)
                history = []
                
                for record in self.hedge_history[user_id][asset]:
                    record_date = datetime.fromisoformat(record['date'])
                    if record_date >= cutoff_date:
                        # Update PnL for active hedges (simplified)
                        if record['status'] == 'ACTIVE':
                            current_price = self._get_current_price(asset)
                            entry_price = record['price']
                            size = record['size']
                            
                            # Simplified PnL calculation
                            pnl = (current_price - entry_price) * size / entry_price * 0.1  # Hedge PnL approximation
                            record['pnl'] = pnl
                        
                        history.append(record)
                
                return sorted(history, key=lambda x: x['date'], reverse=True)
                
        except Exception as e:
            logger.error(f"Error getting hedge history: {e}")
            return []
    
    def get_portfolio_analytics(self, user_id: int) -> Dict:
        """Get comprehensive portfolio analytics"""
        try:
            with self.lock:
                if user_id not in self.active_positions:
                    return {}
                
                positions = self.active_positions[user_id]
                total_value = 0.0
                total_pnl = 0.0
                total_var = 0.0
                position_count = 0
                active_hedges = 0
                hedge_pnl = 0.0
                
                correlations = []
                
                for asset, position in positions.items():
                    if position['active']:
                        position_count += 1
                        
                        # Update current metrics
                        current_price = self._get_current_price(asset)
                        entry_price = position['entry_price']
                        size = position['size']
                        
                        # Calculate position value and PnL
                        market_value = size * current_price / entry_price
                        pnl = (current_price - entry_price) * size / entry_price
                        
                        total_value += market_value
                        total_pnl += pnl
                        
                        # Calculate VaR for position
                        historical_returns = self._get_historical_returns(asset)
                        var_95 = self._calculate_var(historical_returns, size, 0.95)
                        total_var += var_95 ** 2  # Portfolio VaR calculation (simplified)
                        
                        # Hedge metrics
                        active_hedges += position.get('active_hedges', 0)
                        
                        # Calculate hedge PnL
                        if asset in self.hedge_history.get(user_id, {}):
                            for hedge in self.hedge_history[user_id][asset]:
                                if hedge['status'] == 'ACTIVE':
                                    hedge_pnl += hedge.get('pnl', 0)
                
                # Portfolio-level calculations
                portfolio_var = np.sqrt(total_var) if total_var > 0 else 0
                portfolio_var_99 = portfolio_var * 1.3  # Approximate 99% VaR
                
                # Calculate correlation metrics
                if position_count > 1:
                    avg_correlation = self._calculate_portfolio_correlation(user_id)
                    diversification_ratio = 1 - abs(avg_correlation)
                    risk_concentration = max(0, abs(avg_correlation) - 0.3)
                else:
                    avg_correlation = 0
                    diversification_ratio = 1
                    risk_concentration = 0
                
                # Calculate expected shortfall
                expected_shortfall = portfolio_var * 1.5  # Simplified ES calculation
                
                # Calculate maximum drawdown (simplified)
                max_drawdown = min(0, total_pnl / total_value) if total_value > 0 else 0
                
                # Hedge effectiveness
                hedge_effectiveness = min(0.95, active_hedges * 0.15) if active_hedges > 0 else 0
                
                analytics = {
                    'total_value': total_value,
                    'total_pnl': total_pnl,
                    'position_count': position_count,
                    'portfolio_var': portfolio_var,
                    'portfolio_var_99': portfolio_var_99,
                    'expected_shortfall': expected_shortfall,
                    'max_drawdown': max_drawdown,
                    'avg_correlation': avg_correlation,
                    'diversification_ratio': diversification_ratio,
                    'risk_concentration': risk_concentration,
                    'total_hedges': active_hedges,
                    'hedge_effectiveness': hedge_effectiveness,
                    'hedge_pnl': hedge_pnl,
                    'sharpe_ratio': total_pnl / (portfolio_var if portfolio_var > 0 else 1),
                    'last_updated': datetime.now().isoformat()
                }
                
                return analytics
                
        except Exception as e:
            logger.error(f"Error getting portfolio analytics: {e}")
            return {}
    
    def configure_risk_params(self, user_id: int, asset: str, params: Dict) -> bool:
        """Configure risk parameters for a position"""
        try:
            with self.lock:
                if user_id not in self.risk_params:
                    self.risk_params[user_id] = {}
                
                if asset not in self.risk_params[user_id]:
                    self.risk_params[user_id][asset] = self.default_risk_params.copy()
                
                # Update parameters
                self.risk_params[user_id][asset].update(params)
                
                logger.info(f"Risk parameters updated for user {user_id}, asset {asset}")
                return True
                
        except Exception as e:
            logger.error(f"Error configuring risk parameters: {e}")
            return False
    
    def setup_auto_hedge(self, user_id: int, asset: str, strategy: str, threshold: float) -> bool:
        """Setup automatic hedging for a position"""
        try:
            with self.lock:
                if user_id not in self.auto_hedge_config:
                    self.auto_hedge_config[user_id] = {}
                
                auto_config = {
                    'strategy': strategy,
                    'threshold': threshold,
                    'enabled': True,
                    'max_hedge_size': 10000,  # USD
                    'min_interval': 300,  # 5 minutes minimum between auto-hedges
                    'last_execution': None,
                    'execution_count': 0
                }
                
                self.auto_hedge_config[user_id][asset] = auto_config
                
                # Update position with auto-hedge status
                if (user_id in self.active_positions and 
                    asset in self.active_positions[user_id]):
                    self.active_positions[user_id][asset]['auto_hedge'] = True
                
                logger.info(f"Auto-hedge setup for user {user_id}, asset {asset}")
                return True
                
        except Exception as e:
            logger.error(f"Error setting up auto-hedge: {e}")
            return False
    
    def get_all_active_positions(self) -> Dict:
        """Get all active positions across all users"""
        try:
            with self.lock:
                active_positions = {}
                
                for user_id, user_positions in self.active_positions.items():
                    active_user_positions = {}
                    
                    for asset, position in user_positions.items():
                        if position.get('active', False):
                            active_user_positions[asset] = position
                    
                    if active_user_positions:
                        active_positions[user_id] = active_user_positions
                
                return active_positions
                
        except Exception as e:
            logger.error(f"Error getting all active positions: {e}")
            return {}
    
    # Helper methods
    def _get_current_price(self, asset: str) -> float:
        """Get current price for an asset (mock implementation)"""
        # In production, this would connect to real market data
        mock_prices = {
            'BTCUSD': 50000.0,
            'ETHUSD': 3000.0,
            'ADAUSD': 1.5,
            'SOLUSD': 100.0,
            'DOTUSD': 25.0,
            'LINKUSD': 20.0,
            'MATICUSD': 1.0,
            'AVAXUSD': 40.0,
            'UNIUSD': 15.0,
            'BNBUSD': 300.0,
            'XRPUSD': 0.8,
            'LTCUSD': 150.0
        }
        
        base_price = mock_prices.get(asset, 1000.0)
        # Add some random variation
        variation = np.random.normal(0, 0.01)  # 1% standard deviation
        return base_price * (1 + variation)
    
    def _get_historical_returns(self, asset: str, days: int = 30) -> List[float]:
        """Get historical returns for an asset (mock implementation)"""
        # In production, this would fetch real historical data
        # Generate mock returns with realistic volatility
        volatilities = {
            'BTCUSD': 0.04,
            'ETHUSD': 0.05,
            'ADAUSD': 0.06,
            'SOLUSD': 0.07,
            'DOTUSD': 0.06,
            'LINKUSD': 0.05,
            'MATICUSD': 0.08,
            'AVAXUSD': 0.07,
            'UNIUSD': 0.06,
            'BNBUSD': 0.04,
            'XRPUSD': 0.05,
            'LTCUSD': 0.04
        }
        
        vol = volatilities.get(asset, 0.05)
        returns = np.random.normal(0, vol, days).tolist()
        return returns
    
    def _calculate_var(self, returns: List[float], position_size: float, confidence: float) -> float:
        """Calculate Value at Risk"""
        if not returns:
            return 0.0
        
        returns_array = np.array(returns)
        var_percentile = np.percentile(returns_array, (1 - confidence) * 100)
        return var_percentile * position_size
    
    def _calculate_volatility(self, returns: List[float]) -> float:
        """Calculate volatility from returns"""
        if not returns:
            return 0.0
        
        returns_array = np.array(returns)
        return np.std(returns_array)
    
    def _calculate_correlation_risk(self, user_id: int, asset: str) -> float:
        """Calculate correlation risk for a position"""
        try:
            if user_id not in self.active_positions:
                return 0.0
            
            positions = self.active_positions[user_id]
            if len(positions) < 2:
                return 0.0
            
            # Simplified correlation calculation
            # In production, this would use real correlation matrices
            correlations = []
            for other_asset in positions:
                if other_asset != asset and positions[other_asset]['active']:
                    # Mock correlation based on asset types
                    if asset.startswith('BTC') and other_asset.startswith('ETH'):
                        corr = 0.6
                    elif asset.startswith('ETH') and other_asset.startswith('BTC'):
                        corr = 0.6
                    else:
                        corr = np.random.uniform(0.3, 0.8)
                    
                    correlations.append(corr)
            
            return np.mean(correlations) if correlations else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating correlation risk: {e}")
            return 0.0
    
    def _calculate_portfolio_correlation(self, user_id: int) -> float:
        """Calculate average portfolio correlation"""
        try:
            if user_id not in self.active_positions:
                return 0.0
            
            positions = list(self.active_positions[user_id].keys())
            if len(positions) < 2:
                return 0.0
            
            correlations = []
            for i in range(len(positions)):
                for j in range(i + 1, len(positions)):
                    # Mock correlation calculation
                    corr = np.random.uniform(0.3, 0.8)
                    correlations.append(corr)
            
            return np.mean(correlations) if correlations else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating portfolio correlation: {e}")
            return 0.0

# Create global instance
risk_monitor = RiskMonitor()

# Export for imports
__all__ = ['risk_monitor', 'RiskMonitor']