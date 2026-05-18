import pandas as pd
import numpy as np
import time
from data_engine import DataEngine
from scanner import VN302

class AntigravityScanner:
    def __init__(self, data_engine):
        self.engine = data_engine
        self.results = []

    def analyze_symbol(self, symbol):
        print(f"Analyzing {symbol}...")
        # Fetch long history for backtesting
        df = self.engine.get_history(symbol, start='2024-01-01')
        
        if df.empty or len(df) < 50:
            return None

        df = df.sort_values('time').reset_index(drop=True)
        
        # Calculate Indicators
        df['vol_ma20'] = df['volume'].rolling(window=20).mean()
        
        # Setup conditions
        # 1. Volume < MA20 for at least 5 sessions
        df['vol_below_ma'] = df['volume'] < df['vol_ma20']
        df['consecutive_vol_low'] = df['vol_below_ma'].rolling(window=5).apply(lambda x: x.all(), raw=True)
        
        # 2. Sideways (+/- 2%) over 5 sessions
        def is_sideways(window_closes):
            if len(window_closes) < 5: return 0
            price_min = window_closes.min()
            price_max = window_closes.max()
            # Range within 4% total (which is +/- 2% from center approximately)
            if price_min == 0: return 0
            return 1 if (price_max - price_min) / price_min <= 0.04 else 0

        df['sideways'] = df['close'].rolling(window=5).apply(is_sideways, raw=True)
        
        # Setup met at day i-1
        df['setup_met'] = (df['consecutive_vol_low'].shift(1) == 1) & (df['sideways'].shift(1) == 1)
        
        # Trigger conditions at day i
        # 1. Volume >= 1.5 * MA20
        # 2. Price increase >= 3%
        df['vol_spike'] = df['volume'] >= (1.5 * df['vol_ma20'])
        df['price_spike'] = (df['close'] / df['close'].shift(1) - 1) >= 0.03
        
        df['trigger'] = df['setup_met'] & df['vol_spike'] & df['price_spike']
        
        signals = df[df['trigger'] == True].index.tolist()
        
        symbol_stats = []
        for idx in signals:
            trigger_row = df.iloc[idx]
            
            # 1. Days from start of vol depletion
            # Look back to find when vol first went below MA20 continuously
            setup_start_idx = idx - 1
            while setup_start_idx > 0 and df.iloc[setup_start_idx]['vol_below_ma']:
                setup_start_idx -= 1
            days_in_setup = idx - (setup_start_idx + 1)
            
            # 2. Forward returns
            def get_ret(n):
                if idx + n < len(df):
                    return (df.iloc[idx + n]['close'] / trigger_row['close'] - 1) * 100
                return None
            
            ret5 = get_ret(5)
            ret10 = get_ret(10)
            ret20 = get_ret(20)
            
            # 3. Risk/Reward
            # Risk = Entry - low of sideways period (prev 5 days)
            sideways_period = df.iloc[idx-5:idx]
            risk = trigger_row['close'] - sideways_period['low'].min()
            
            # Reward = max high in next 20 days - Entry
            forward_period = df.iloc[idx:min(idx+21, len(df))]
            reward = forward_period['high'].max() - trigger_row['close']
            
            rr_ratio = reward / risk if risk > 0 else 0
            
            symbol_stats.append({
                'date': trigger_row['time'],
                'days_in_setup': days_in_setup,
                'ret5': ret5,
                'ret10': ret10,
                'ret20': ret20,
                'rr': rr_ratio
            })
            
        return symbol_stats

    def run_all(self):
        all_signals = []
        for symbol in VN302:
            stats = self.analyze_symbol(symbol)
            if stats:
                for s in stats:
                    s['symbol'] = symbol
                    all_signals.append(s)
            time.sleep(4.0) # Anti rate-limit
            
        if not all_signals:
            print("No signals found.")
            return

        report_df = pd.DataFrame(all_signals)
        
        # Overall Stats
        avg_days_setup = report_df['days_in_setup'].mean()
        
        prob_win_5 = (report_df['ret5'] > 0).mean() * 100
        prob_win_10 = (report_df['ret10'] > 0).mean() * 100
        prob_win_20 = (report_df['ret20'] > 0).mean() * 100
        
        avg_rr = report_df['rr'].mean()
        
        print("\n=== ANTIGRAVITY VOLATILITY STRATEGY REPORT ===")
        print(f"Total Signals Found: {len(report_df)}")
        print(f"Average days in setup: {avg_days_setup:.1f} days")
        print(f"Win Probability (5 sessions): {prob_win_5:.1f}%")
        print(f"Win Probability (10 sessions): {prob_win_10:.1f}%")
        print(f"Win Probability (20 sessions): {prob_win_20:.1f}%")
        print(f"Average Risk/Reward: {avg_rr:.2f}")
        print("==============================================\n")
        
        # Show top signals by return
        print("Latest Signals:")
        print(report_df.sort_values('date', ascending=False).head(10)[['date', 'symbol', 'ret20', 'rr']])
        
        return report_df

if __name__ == "__main__":
    engine = DataEngine(source='KBS')
    scanner = AntigravityScanner(engine)
    scanner.run_all()
