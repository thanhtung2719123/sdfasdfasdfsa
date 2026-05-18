import pandas as pd
import numpy as np

class Backtester:
    def __init__(self, data, rsi_period=14, buy_threshold=30, sell_threshold=70, 
                 initial_capital=100000000, stop_loss_pct=None, take_profit_pct=None, position_size_pct=100.0):
        self.df = data.copy().sort_values('time').reset_index(drop=True)
        self.rsi_period = rsi_period
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
        self.initial_capital = initial_capital
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.position_size_pct = position_size_pct
        self.trades = []
        self.metrics = {}
        self.equity_curve = []
        self.benchmark_curve = []

    def calculate_rsi(self):
        delta = self.df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        
        rs = gain / loss
        self.df['rsi'] = 100 - (100 / (1 + rs))

    def run(self):
        self.calculate_rsi()
        self.df = self.df.dropna(subset=['rsi']).sort_values('time').reset_index(drop=True)
        
        if self.df.empty:
            self.calculate_metrics()
            return self.trades, self.metrics
            
        cash = self.initial_capital
        shares = 0
        in_position = False
        entry_time = None
        entry_price = 0
        
        self.equity_curve = []
        
        # Calculate Buy & Hold Benchmark
        initial_price = self.df['close'].iloc[0]
        self.benchmark_curve = []
        for i in range(len(self.df)):
            row = self.df.iloc[i]
            bench_equity = self.initial_capital * (row['close'] / initial_price)
            self.benchmark_curve.append({
                'time': row['time'],
                'equity': bench_equity
            })
            
        for i in range(len(self.df)):
            row = self.df.iloc[i]
            current_price = row['close']
            
            # Track daily equity at start of day
            daily_market_value = shares * current_price
            self.equity_curve.append({
                'time': row['time'],
                'equity': cash + daily_market_value
            })

            # Check exits first
            if in_position:
                # 1. Stop Loss check
                if self.stop_loss_pct is not None:
                    sl_level = entry_price * (1.0 - self.stop_loss_pct / 100.0)
                    if row['low'] <= sl_level:
                        exit_price = min(row['open'], sl_level)
                        exit_time = row['time']
                        in_position = False
                        
                        cash += shares * exit_price
                        profit = (exit_price - entry_price) * shares
                        self.trades.append({
                            'entry_time': entry_time,
                            'entry_price': entry_price,
                            'exit_time': exit_time,
                            'exit_price': exit_price,
                            'profit': profit,
                            'profit_pct': ((exit_price / entry_price) - 1) * 100,
                            'duration': (exit_time - entry_time).days,
                            'exit_reason': 'Stop Loss'
                        })
                        shares = 0
                        continue
                
                # 2. Take Profit check
                if self.take_profit_pct is not None:
                    tp_level = entry_price * (1.0 + self.take_profit_pct / 100.0)
                    if row['high'] >= tp_level:
                        exit_price = max(row['open'], tp_level)
                        exit_time = row['time']
                        in_position = False
                        
                        cash += shares * exit_price
                        profit = (exit_price - entry_price) * shares
                        self.trades.append({
                            'entry_time': entry_time,
                            'entry_price': entry_price,
                            'exit_time': exit_time,
                            'exit_price': exit_price,
                            'profit': profit,
                            'profit_pct': ((exit_price / entry_price) - 1) * 100,
                            'duration': (exit_time - entry_time).days,
                            'exit_reason': 'Take Profit'
                        })
                        shares = 0
                        continue
                
                # 3. Regular RSI signal exit (triggered previous session)
                if i > 0:
                    prev_row = self.df.iloc[i-1]
                    if prev_row['rsi'] > self.sell_threshold:
                        exit_price = row['open']
                        exit_time = row['time']
                        in_position = False
                        
                        cash += shares * exit_price
                        profit = (exit_price - entry_price) * shares
                        self.trades.append({
                            'entry_time': entry_time,
                            'entry_price': entry_price,
                            'exit_time': exit_time,
                            'exit_price': exit_price,
                            'profit': profit,
                            'profit_pct': ((exit_price / entry_price) - 1) * 100,
                            'duration': (exit_time - entry_time).days,
                            'exit_reason': 'RSI Exit'
                        })
                        shares = 0
                        continue
            else:
                # Regular RSI signal buy (triggered previous session)
                if i > 0:
                    prev_row = self.df.iloc[i-1]
                    if prev_row['rsi'] < self.buy_threshold:
                        in_position = True
                        entry_price = row['open']
                        entry_time = row['time']
                        
                        allocation = cash * (self.position_size_pct / 100.0)
                        shares = allocation // entry_price
                        cash -= shares * entry_price

        self.calculate_metrics()
        return self.trades, self.metrics

    def calculate_metrics(self):
        if not self.equity_curve:
            self.metrics = self.empty_metrics()
            return

        equity_df = pd.DataFrame(self.equity_curve)
        final_equity = equity_df['equity'].iloc[-1]
        net_profit = final_equity - self.initial_capital
        
        # Max Drawdown
        equity_df['peak'] = equity_df['equity'].cummax()
        equity_df['drawdown'] = (equity_df['peak'] - equity_df['equity']) / equity_df['peak']
        max_drawdown = equity_df['drawdown'].max() * 100
        
        # Max Drawdown Duration (in Days)
        equity_df['is_drawdown'] = equity_df['equity'] < equity_df['peak']
        drawdown_duration = 0
        current_dd_len = 0
        for val in equity_df['is_drawdown'].values:
            if val:
                current_dd_len += 1
                if current_dd_len > drawdown_duration:
                    drawdown_duration = current_dd_len
            else:
                current_dd_len = 0

        if not self.trades:
            self.metrics = self.empty_metrics()
            self.metrics['max_drawdown'] = max_drawdown
            self.metrics['drawdown_duration'] = drawdown_duration
            self.metrics['net_profit'] = net_profit
            return

        trade_df = pd.DataFrame(self.trades)
        win_rate = (trade_df['profit'] > 0).mean() * 100
        
        gross_profit = trade_df[trade_df['profit'] > 0]['profit'].sum()
        gross_loss = abs(trade_df[trade_df['profit'] < 0]['profit'].sum())
        profit_factor = gross_profit / gross_loss if gross_loss != 0 else float('inf')
        
        returns = trade_df['profit_pct'] / 100
        sharpe = returns.mean() / returns.std() * np.sqrt(252) if len(returns) > 1 and returns.std() != 0 else 0
        
        # Sortino Ratio
        downside_returns = returns[returns < 0]
        sortino = returns.mean() / downside_returns.std() * np.sqrt(252) if len(returns) > 1 and len(downside_returns) > 0 and downside_returns.std() != 0 else 0
        
        expectancy = (win_rate/100 * trade_df[trade_df['profit'] > 0]['profit'].mean() if win_rate > 0 else 0) + \
                     ((1 - win_rate/100) * trade_df[trade_df['profit'] < 0]['profit'].mean() if win_rate < 100 else 0)
        
        self.metrics = {
            'net_profit': net_profit,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown,
            'drawdown_duration': drawdown_duration,
            'sharpe_ratio': sharpe,
            'sortino_ratio': sortino,
            'expectancy': expectancy,
            'avg_duration': trade_df['duration'].mean(),
            'total_trades': len(self.trades)
        }

    def empty_metrics(self):
        return {
            'net_profit': 0, 'win_rate': 0, 'profit_factor': 0, 'max_drawdown': 0, 'drawdown_duration': 0,
            'sharpe_ratio': 0, 'sortino_ratio': 0, 'expectancy': 0, 'avg_duration': 0, 'total_trades': 0
        }
