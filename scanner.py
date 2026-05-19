import pandas as pd
import numpy as np
import time
import queue
import threading
try:
    from PySide6.QtCore import QThread, Signal
except ImportError:
    class QThread:
        def __init__(self, *args, **kwargs):
            pass

    class _NoopSignal:
        def __init__(self, *args, **kwargs):
            pass

        def emit(self, *args, **kwargs):
            pass

        def connect(self, *args, **kwargs):
            pass

    def Signal(*args, **kwargs):
        return _NoopSignal()

VN302_INDUSTRIES = {
    'Họ Vingroup': [
        'VIC', 'VHM', 'VRE'
    ],
    'Ngân hàng': [
        'VCB', 'BID', 'CTG', 'VPB', 'TCB', 'MBB', 'ACB', 'STB', 'HDB', 'VIB',
        'SHB', 'TPB', 'SSB', 'LPB', 'EIB', 'MSB', 'OCB', 'NAB', 'BAB', 'KLB',
        'NVB', 'BVB', 'SGB', 'PGB', 'ABB', 'VAB'
    ],
    'Bất động sản & KCN': [
        'NVL', 'KDH', 'NLG', 'DXG', 'DIG', 'PDR', 'KBC',
        'IDC', 'VGC', 'SZC', 'CEO', 'HDG', 'BCM', 'NTL', 'IJC', 'TDC', 'SCR',
        'CRE', 'KHG', 'HQC', 'TCH', 'DXS', 'NBB', 'SJS', 'SIP', 'NTC', 'SNZ',
        'TIG', 'IDV', 'DTD', 'L14', 'HDC', 'VPI', 'TIP', 'D2D', 'ITA', 'QCG',
        'SZL', 'LHG', 'KOS', 'CSC', 'SGR', 'IDJ', 'NVT', 'AGG', 'CKG', 'LDG',
        'ITC'
    ],
    'Thực phẩm & Nông nghiệp': [
        'VNM', 'MSN', 'SAB', 'KDC', 'QNS', 'SBT', 'DBC', 'PAN', 'BAF', 'VHC',
        'ANV', 'IDI', 'FMC', 'MPC', 'ASM', 'LSS', 'SLS', 'MCH', 'HAG', 'HNG',
        'TAR', 'LTG', 'MML', 'VOC', 'MCM', 'VCF', 'NSC', 'VLC', 'VSN', 'ACL',
        'CMX', 'APF'
    ],
    'Tài nguyên Cơ bản': [
        'HPG', 'HSG', 'NKG', 'SMC', 'TLH', 'KSB', 'DHA', 'VLB', 'HT1', 'BCC',
        'BMP', 'NTP', 'PTB', 'TTF', 'VGS', 'POM', 'TIS', 'DTL', 'VCS', 'ACG',
        'MSR', 'DHC', 'VPG', 'TVD', 'CST', 'NBC'
    ],
    'Dịch vụ Tài chính': [
        'SSI', 'VND', 'VCI', 'HCM', 'SHS', 'MBS', 'FTS', 'BSI', 'CTS', 'VIX',
        'AGR', 'ORS', 'VDS', 'APS', 'TVS', 'DSC', 'APG', 'SBS', 'BVH', 'BMI',
        'MIG', 'BIC', 'PVI', 'VNR', 'PTI', 'BVS', 'EVS', 'TCI', 'ABI', 'VIG',
        'EVF'
    ],
    'Năng lượng & Tiện ích': [
        'GAS', 'PLX', 'PVD', 'PVS', 'BSR', 'POW', 'NT2', 'PC1', 'REE', 'BWE',
        'TDM', 'GEG', 'QTP', 'HND', 'VSH', 'CHP', 'SBA', 'OIL', 'PVC', 'PVB',
        'CNG', 'PGC', 'PGS', 'TTA', 'DNW', 'TMP', 'SHP', 'PSH', 'TV2', 'GEX',
        'PPC'
    ],
    'Xây dựng & Đầu tư công': [
        'VCG', 'LCG', 'HHV', 'CII', 'CTD', 'HBC', 'FCN', 'C4G', 'DPG', 'HUT',
        'G36', 'TCD', 'CTI', 'HTN', 'VNE', 'C32', 'PLC', 'CC1', 'THD', 'HAN',
        'VC7', 'LIG'
    ],
    'Hóa chất & Nhựa': [
        'DGC', 'DPM', 'DCM', 'PHR', 'GVR', 'DPR', 'TRC', 'DRI', 'BFC', 'CSV',
        'LAS', 'DDV', 'AAA', 'APH', 'BRC', 'DRC', 'CSM', 'SRC', 'NHH', 'SFG',
        'DAG', 'PAT'
    ],
    'Vận tải & Logistics': [
        'HVN', 'VJC', 'HAH', 'GMD', 'SGN', 'ACV', 'VOS', 'VTO', 'VIP', 'PVT',
        'TCL', 'PHP', 'SKG', 'MVN', 'SGP', 'ILB', 'TMS', 'STG', 'VSC', 'SCS'
    ],
    'Bán lẻ & Tiêu dùng': [
        'MWG', 'PNJ', 'FRT', 'DGW', 'PET', 'HAX', 'SVC', 'CTF', 'AST', 'TMT',
        'VEA', 'TLG', 'RAL'
    ],
    'Y tế & Dược phẩm': [
        'DHG', 'IMP', 'DBD', 'TRA', 'DVN', 'TNH', 'OPC', 'DHT', 'DCL', 'JVC'
    ],
    'Công nghệ & Viễn thông': [
        'FPT', 'CMG', 'ELC', 'FOX', 'VGI', 'ITD', 'SAM', 'VNZ', 'VTP', 'CTR'
    ],
    'Dệt may': [
        'TCM', 'TNG', 'MSH', 'VGT', 'STK', 'GIL', 'VGG', 'M10'
    ]
}


# Flat list for scanning
VN302 = [symbol for symbols in VN302_INDUSTRIES.values() for symbol in symbols]
# Add VNINDEX for benchmark comparison
SCAN_LIST = ['VNINDEX'] + VN302

def find_pivots(series, window=5):
    """Finds local peaks and troughs"""
    peaks = []
    troughs = []
    # Ensure index is integer based for easier manipulation if needed
    for i in range(window, len(series) - window):
        is_peak = True
        is_trough = True
        for j in range(1, window + 1):
            if series.iloc[i] <= series.iloc[i - j] or series.iloc[i] <= series.iloc[i + j]:
                is_peak = False
            if series.iloc[i] >= series.iloc[i - j] or series.iloc[i] >= series.iloc[i + j]:
                is_trough = False
        if is_peak:
            peaks.append((i, series.iloc[i]))
        if is_trough:
            troughs.append((i, series.iloc[i]))
    return peaks, troughs

def check_divergence(price_series, ind_series, window=5, lookback=60):
    # Slice to lookback
    if len(price_series) < lookback:
        return "None"
    
    p_recent = price_series.iloc[-lookback:].reset_index(drop=True)
    i_recent = ind_series.iloc[-lookback:].reset_index(drop=True)
    
    p_peaks, p_troughs = find_pivots(p_recent, window)
    
    # Bearish Divergence: Price higher high, Indicator lower high
    if len(p_peaks) >= 2:
        idx1, p1 = p_peaks[-2]
        idx2, p2 = p_peaks[-1]
        if p2 > p1: # Price higher high
            # Check corresponding indicator values
            i1 = i_recent.iloc[idx1]
            i2 = i_recent.iloc[idx2]
            if i2 < i1:
                return "Bearish"
                
    # Bullish Divergence: Price lower low, Indicator higher low
    if len(p_troughs) >= 2:
        idx1, p1 = p_troughs[-2]
        idx2, p2 = p_troughs[-1]
        if p2 < p1: # Price lower low
            i1 = i_recent.iloc[idx1]
            i2 = i_recent.iloc[idx2]
            if i2 > i1:
                return "Bullish"
                
    return "None"

class ScannerThread(QThread):
    progress_update = Signal(int, int) # current, total
    row_result = Signal(dict)
    finished_scan = Signal()
    error_signal = Signal(str)

    def __init__(self, data_engine, parent=None):
        super().__init__(parent)
        self.engine = data_engine
        self.is_running = True

    def stop(self):
        self.is_running = False

    def run(self):
        total = len(SCAN_LIST)
        fetch_start_date = '2025-01-01'
        return_ref_date = '2026-03-23'
        
        q = queue.Queue()
        for symbol in SCAN_LIST:
            q.put(symbol)
            
        progress_lock = threading.Lock()
        completed = 0
        
        def worker():
            nonlocal completed
            while self.is_running:
                try:
                    symbol = q.get_nowait()
                except queue.Empty:
                    break
                
                try:
                    df_long = self.engine.get_history(symbol, start=fetch_start_date)
                    
                    if df_long.empty or len(df_long) < 10:
                        q.task_done()
                        with progress_lock:
                            completed += 1
                            self.progress_update.emit(completed, total)
                        continue

                    close = df_long['close']
                    current_price = close.iloc[-1]
                    
                    df_since_ref = df_long[df_long['time'] >= return_ref_date]
                    if not df_since_ref.empty:
                        price_start = df_since_ref['close'].iloc[0]
                        return_since_ref = (current_price / price_start - 1) * 100
                    else:
                        return_since_ref = 0
                    
                    ma20 = close.rolling(20).mean().iloc[-1] if len(close) >= 20 else 0
                    ma50 = close.rolling(50).mean().iloc[-1] if len(close) >= 50 else 0
                    ma100 = close.rolling(100).mean().iloc[-1] if len(close) >= 100 else 0
                    ma200 = close.rolling(200).mean().iloc[-1] if len(close) >= 200 else 0
                    
                    window_52w = 252
                    if len(close) >= window_52w:
                        rolling_52w = close.iloc[-window_52w:]
                        high_52w = rolling_52w.max()
                        low_52w = rolling_52w.min()
                        high_idx = rolling_52w.idxmax()
                        breakout_date = df_long.loc[high_idx, 'time'].strftime('%Y-%m-%d')
                    else:
                        high_52w = close.max()
                        low_52w = close.min()
                        high_idx = close.idxmax()
                        breakout_date = df_long.loc[high_idx, 'time'].strftime('%Y-%m-%d')

                    delta = close.diff()
                    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                    rs = gain / loss
                    rsi = 100 - (100 / (1 + rs))
                    current_rsi = rsi.iloc[-1] if pd.notna(rsi.iloc[-1]) else 50
                    
                    ema12 = close.ewm(span=12, adjust=False).mean()
                    ema26 = close.ewm(span=26, adjust=False).mean()
                    macd = ema12 - ema26
                    macd_signal = macd.ewm(span=9, adjust=False).mean()
                    macd_hist = macd - macd_signal
                    
                    rsi_div = check_divergence(close, rsi)
                    macd_div = check_divergence(close, macd_hist)
                    
                    if len(macd_hist) > 1:
                        macd_status = "Cross Up" if macd_hist.iloc[-1] > 0 and macd_hist.iloc[-2] <= 0 else \
                                      "Cross Down" if macd_hist.iloc[-1] < 0 and macd_hist.iloc[-2] >= 0 else \
                                      "Positive" if macd_hist.iloc[-1] > 0 else "Negative"
                    else:
                        macd_status = "N/A"

                    industry = "Index"
                    if symbol != 'VNINDEX':
                        for ind, symbols in VN302_INDUSTRIES.items():
                            if symbol in symbols:
                                industry = ind
                                break

                    result = {
                        'symbol': symbol,
                        'industry': industry,
                        'price': current_price,
                        'return_23_03': return_since_ref,
                        'ma20': ma20,
                        'ma50': ma50,
                        'ma100': ma100,
                        'ma200': ma200,
                        'high_52w': high_52w,
                        'low_52w': low_52w,
                        'breakout_date': breakout_date,
                        'rsi': current_rsi,
                        'rsi_div': rsi_div,
                        'macd': macd_status,
                        'macd_div': macd_div
                    }
                    self.row_result.emit(result)
                    
                except Exception as e:
                    self.error_signal.emit(f"Error scanning {symbol}: {e}")
                    
                q.task_done()
                with progress_lock:
                    completed += 1
                    self.progress_update.emit(completed, total)

        num_workers = 8
        threads = []
        for _ in range(num_workers):
            t = threading.Thread(target=worker)
            t.start()
            threads.append(t)
            
        for t in threads:
            t.join()
            
        self.progress_update.emit(total, total)
        self.finished_scan.emit()


class AntigravityThread(QThread):
    progress_update = Signal(int, int)
    signal_found = Signal(dict)
    finished_scan = Signal(dict) # Returns summary metrics
    error_signal = Signal(str)

    def __init__(self, data_engine, parent=None):
        super().__init__(parent)
        self.engine = data_engine
        self.is_running = True

    def stop(self):
        self.is_running = False

    def run(self):
        total = len(SCAN_LIST)
        all_signals = []
        all_signals_lock = threading.Lock()
        
        q = queue.Queue()
        for symbol in SCAN_LIST:
            q.put(symbol)
            
        progress_lock = threading.Lock()
        completed = 0
        
        def worker():
            nonlocal completed
            while self.is_running:
                try:
                    symbol = q.get_nowait()
                except queue.Empty:
                    break
                
                try:
                    df = self.engine.get_history(symbol, start='2024-01-01')
                    if df.empty or len(df) < 50:
                        q.task_done()
                        with progress_lock:
                            completed += 1
                            self.progress_update.emit(completed, total)
                        continue

                    df = df.sort_values('time').reset_index(drop=True)
                    df['vol_ma20'] = df['volume'].rolling(window=20).mean()
                    df['vol_below_ma'] = df['volume'] < df['vol_ma20']
                    df['consecutive_vol_low'] = df['vol_below_ma'].rolling(window=5).apply(lambda x: x.all(), raw=True)
                    
                    def is_sideways(window_closes):
                        if len(window_closes) < 5: return 0
                        p_min, p_max = window_closes.min(), window_closes.max()
                        return 1 if p_min > 0 and (p_max - p_min) / p_min <= 0.04 else 0

                    df['sideways'] = df['close'].rolling(window=5).apply(is_sideways, raw=True)
                    df['setup_met'] = (df['consecutive_vol_low'].shift(1) == 1) & (df['sideways'].shift(1) == 1)
                    df['vol_spike'] = df['volume'] >= (1.5 * df['vol_ma20'])
                    df['price_spike'] = (df['close'] / df['close'].shift(1) - 1) >= 0.03
                    df['trigger'] = df['setup_met'] & df['vol_spike'] & df['price_spike']
                    
                    signals_idx = df[df['trigger'] == True].index.tolist()
                    
                    for idx in signals_idx:
                        row = df.iloc[idx]
                        s_idx = idx - 1
                        while s_idx > 0 and df.iloc[s_idx]['vol_below_ma']: s_idx -= 1
                        days_in_setup = idx - (s_idx + 1)
                        
                        def get_ret(n):
                            if idx + n < len(df): return (df.iloc[idx + n]['close'] / row['close'] - 1) * 100
                            return None
                        
                        ret5, ret10, ret20 = get_ret(5), get_ret(10), get_ret(20)
                        risk = row['close'] - df.iloc[idx-5:idx]['low'].min()
                        reward = df.iloc[idx:min(idx+21, len(df))]['high'].max() - row['close']
                        rr = reward / risk if risk > 0 else 0
                        
                        sig_data = {
                            'symbol': symbol, 'date': row['time'], 'days_in_setup': days_in_setup,
                            'ret5': ret5, 'ret10': ret10, 'ret20': ret20, 'rr': rr
                        }
                        with all_signals_lock:
                            all_signals.append(sig_data)
                        self.signal_found.emit(sig_data)
                        
                except Exception as e:
                    self.error_signal.emit(f"Error {symbol}: {e}")
                    
                q.task_done()
                with progress_lock:
                    completed += 1
                    self.progress_update.emit(completed, total)
        
        num_workers = 8
        threads = []
        for _ in range(num_workers):
            t = threading.Thread(target=worker)
            t.start()
            threads.append(t)
            
        for t in threads:
            t.join()
            
        if all_signals:
            rdf = pd.DataFrame(all_signals)
            summary = {
                'avg_days': rdf['days_in_setup'].mean(),
                'win5': (rdf['ret5'] > 0).mean() * 100,
                'win10': (rdf['ret10'] > 0).mean() * 100,
                'win20': (rdf['ret20'] > 0).mean() * 100,
                'avg_rr': rdf['rr'].mean()
            }
            self.finished_scan.emit(summary)
        else:
            self.finished_scan.emit({})
        
        self.progress_update.emit(total, total)


class WatchlistThread(QThread):
    progress_update = Signal(int, int)
    stock_found = Signal(dict)
    finished_scan = Signal()
    error_signal = Signal(str)

    def __init__(self, data_engine, parent=None):
        super().__init__(parent)
        self.engine = data_engine
        self.is_running = True

    def stop(self):
        self.is_running = False

    def run(self):
        total = len(SCAN_LIST)
        
        q = queue.Queue()
        for symbol in SCAN_LIST:
            q.put(symbol)
            
        progress_lock = threading.Lock()
        completed = 0
        
        def worker():
            nonlocal completed
            while self.is_running:
                try:
                    symbol = q.get_nowait()
                except queue.Empty:
                    break
                
                try:
                    df = self.engine.get_history(symbol, length=50)
                    if df.empty or len(df) < 25:
                        q.task_done()
                        with progress_lock:
                            completed += 1
                            self.progress_update.emit(completed, total)
                        continue

                    df = df.sort_values('time').reset_index(drop=True)
                    df['vol_ma20'] = df['volume'].rolling(window=20).mean()
                    
                    recent_5 = df.iloc[-5:]
                    
                    if recent_5['vol_ma20'].isnull().any():
                        q.task_done()
                        with progress_lock:
                            completed += 1
                            self.progress_update.emit(completed, total)
                        continue

                    vol_below = (recent_5['volume'] < recent_5['vol_ma20']).all()
                    
                    if vol_below:
                        p_min = recent_5['low'].min()
                        p_max = recent_5['high'].max()
                        p_range_pct = (p_max - p_min) / p_min * 100 if p_min > 0 else 100
                        
                        if p_range_pct <= 6.0:
                            streak = 0
                            idx = len(df) - 1
                            while idx >= 0 and pd.notna(df.iloc[idx]['vol_ma20']) and \
                                  df.iloc[idx]['volume'] < df.iloc[idx]['vol_ma20']:
                                streak += 1
                                idx -= 1
                            
                            current_row = df.iloc[-1]
                            self.stock_found.emit({
                                'symbol': symbol,
                                'price': current_row['close'],
                                'streak': streak,
                                'vol_ratio': current_row['volume'] / current_row['vol_ma20'] if current_row['vol_ma20'] > 0 else 0,
                                'range_pct': p_range_pct
                            })
                except Exception as e:
                    self.error_signal.emit(f"Error {symbol}: {e}")
                    
                q.task_done()
                with progress_lock:
                    completed += 1
                    self.progress_update.emit(completed, total)

        num_workers = 8
        threads = []
        for _ in range(num_workers):
            t = threading.Thread(target=worker)
            t.start()
            threads.append(t)
            
        for t in threads:
            t.join()
            
        self.progress_update.emit(total, total)
        self.finished_scan.emit()

