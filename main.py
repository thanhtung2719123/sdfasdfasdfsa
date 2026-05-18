import sys
try:
    from vnstock import register_user
    register_user(api_key='vnstock_74f708b54d2a500d9fc23da9967a4cf5')
except Exception as e:
    print(f"Error registering vnstock API key: {e}")
from PySide6.QtWidgets import QApplication, QMessageBox, QFileDialog, QTableWidgetItem
from PySide6.QtGui import QColor
from ui_main import MainWindow
from data_engine import DataEngine
from backtester import Backtester
from scanner import ScannerThread, AntigravityThread, WatchlistThread
import pandas as pd

class Controller:
    def __init__(self):
        self.window = MainWindow()
        self.engine = DataEngine(source='KBS')
        self.current_trades = []
        self.scanner_thread = None
        
        # Connect signals
        self.window.run_btn.clicked.connect(self.on_run_clicked)
        self.window.export_btn.clicked.connect(self.on_export_clicked)
        self.window.source_input.currentTextChanged.connect(self.on_source_changed)
        
        # Scanner signals
        self.window.start_scan_btn.clicked.connect(self.on_start_scan)
        self.window.stop_scan_btn.clicked.connect(self.on_stop_scan)
        self.window.export_scan_btn.clicked.connect(self.on_export_scan_clicked)
        self.window.export_market_btn.clicked.connect(self.on_export_market_clicked)
        self.window.scanner_table.cellDoubleClicked.connect(self.on_scanner_row_double_clicked)
        self.window.industry_table.itemSelectionChanged.connect(self.on_industry_selection_changed)
        self.window.filter_industry.currentIndexChanged.connect(self.apply_scanner_filters)
        self.window.filter_rsi.currentIndexChanged.connect(self.apply_scanner_filters)
        self.window.filter_macd.currentIndexChanged.connect(self.apply_scanner_filters)
        
        # Antigravity signals
        self.window.start_anti_btn.clicked.connect(self.on_start_anti_scan)
        self.window.stop_anti_btn.clicked.connect(self.on_stop_anti_scan)
        self.window.export_anti_btn.clicked.connect(self.on_export_anti_clicked)
        self.anti_thread = None
        self.anti_results = []
        
        # Watchlist
        self.window.start_watch_btn.clicked.connect(self.on_start_watch_scan)
        self.window.stop_watch_btn.clicked.connect(self.on_stop_watch_scan)
        self.window.export_watch_btn.clicked.connect(self.on_export_watch_clicked)
        self.watch_thread = None
        self.watch_results = []
        
        # Initialize tickers
        self.load_tickers()

    def on_source_changed(self, source):
        self.engine = DataEngine(source=source)
        self.load_tickers()

    def load_tickers(self):
        self.window.ticker_input.clear()
        from scanner import VN302
        self.window.ticker_input.addItems(VN302)
        # Default to a well-known stock like VCI or HPG
        if 'VCI' in VN302:
            self.window.ticker_input.setCurrentText('VCI')
        elif 'HPG' in VN302:
            self.window.ticker_input.setCurrentText('HPG')

    def on_run_clicked(self):
        symbol = self.window.ticker_input.currentText().upper()
        if not symbol:
            QMessageBox.warning(self.window, "Error", "Please select a ticker.")
            return

        try:
            rsi_period = int(self.window.rsi_period.text())
            buy_threshold = float(self.window.buy_threshold.text())
            sell_threshold = float(self.window.sell_threshold.text())
            initial_capital = float(self.window.initial_capital.text())
            
            # SL / TP / Position Size inputs parsing
            sl_txt = self.window.stop_loss_input.text().strip()
            stop_loss = float(sl_txt) if sl_txt and sl_txt.lower() != 'none' and float(sl_txt) > 0 else None
            
            tp_txt = self.window.take_profit_input.text().strip()
            take_profit = float(tp_txt) if tp_txt and tp_txt.lower() != 'none' and float(tp_txt) > 0 else None
            
            ps_txt = self.window.position_size_input.text().strip()
            position_size = float(ps_txt) if ps_txt else 100.0
        except ValueError:
            QMessageBox.warning(self.window, "Error", "Invalid parameters.")
            return

        start_date = self.window.start_date.date().toString("yyyy-MM-dd")
        end_date = self.window.end_date.date().toString("yyyy-MM-dd")

        self.window.run_btn.setEnabled(False)
        self.window.run_btn.setText("Fetching Data...")
        QApplication.processEvents()

        # Fetch Data
        df = self.engine.get_history(symbol, start=start_date, end=end_date)
        
        if df.empty:
            QMessageBox.critical(self.window, "Error", f"No data found for {symbol}")
            self.window.run_btn.setEnabled(True)
            self.window.run_btn.setText("Run Backtest")
            return

        # Run Backtest
        self.window.run_btn.setText("Running Strategy...")
        QApplication.processEvents()
        
        bt = Backtester(df, rsi_period, buy_threshold, sell_threshold, initial_capital,
                        stop_loss_pct=stop_loss, take_profit_pct=take_profit, position_size_pct=position_size)
        trades, metrics = bt.run()
        self.current_trades = trades
        
        # Update UI
        self.window.plot_data(bt.df, trades, equity_curve=bt.equity_curve, benchmark_curve=bt.benchmark_curve)
        self.window.update_metrics(metrics)
        self.window.update_trades_table(trades)
        
        self.window.run_btn.setEnabled(True)
        self.window.export_btn.setEnabled(len(trades) > 0)
        self.window.run_btn.setText("Run Backtest")

    def on_export_clicked(self):
        if not self.current_trades:
            return
        
        file_path, _ = QFileDialog.getSaveFileName(self.window, "Save Trades", "trades.csv", "CSV Files (*.csv)")
        if file_path:
            df = pd.DataFrame(self.current_trades)
            df.to_csv(file_path, index=False)
            QMessageBox.information(self.window, "Success", f"Trades exported to {file_path}")

    # --- Scanner Methods ---
    def on_start_scan(self):
        self.window.scanner_table.setRowCount(0)
        self.window.scan_progress.setValue(0)
        self.window.start_scan_btn.setEnabled(False)
        self.window.stop_scan_btn.setEnabled(True)
        self.window.export_scan_btn.setEnabled(False)
        self.window.export_market_btn.setEnabled(False)
        self.scan_results = []
        
        self.scanner_thread = ScannerThread(self.engine)
        self.scanner_thread.progress_update.connect(self.on_scan_progress)
        self.scanner_thread.row_result.connect(self.on_scan_result)
        self.scanner_thread.finished_scan.connect(self.on_scan_finished)
        self.scanner_thread.error_signal.connect(self.on_scan_error)
        self.scanner_thread.start()

    def on_stop_scan(self):
        if self.scanner_thread and self.scanner_thread.isRunning():
            self.scanner_thread.stop()
            self.window.stop_scan_btn.setEnabled(False)

    def on_scan_progress(self, current, total):
        self.window.scan_progress.setMaximum(total)
        self.window.scan_progress.setValue(current)

    def on_scan_result(self, res):
        self.scan_results.append(res)
        row = self.window.scanner_table.rowCount()
        self.window.scanner_table.insertRow(row)
        
        def create_item(val, fg_color=None):
            item = QTableWidgetItem(str(val))
            if fg_color:
                item.setForeground(QColor(fg_color))
            return item

        price = res['price']
        ret = res['return_23_03']
        c_ret = '#4caf50' if ret > 0 else '#f44336'
        
        # Colors for MAs
        c_ma20 = '#4caf50' if price > res['ma20'] else '#f44336'
        c_ma50 = '#4caf50' if price > res['ma50'] else '#f44336'
        c_ma100 = '#4caf50' if price > res['ma100'] else '#f44336'
        c_ma200 = '#4caf50' if price > res['ma200'] else '#f44336'
        
        # Color for 52w high/low
        # If price is within 1% of 52w high, highlight green
        c_high = '#4caf50' if price >= res['high_52w'] * 0.99 else '#ffffff'
        c_low = '#f44336' if price <= res['low_52w'] * 1.01 else '#ffffff'
        
        c_rsi = '#4caf50' if res['rsi'] < 30 else ('#f44336' if res['rsi'] > 70 else '#ffffff')
        c_rsi_div = '#4caf50' if res['rsi_div'] == 'Bullish' else ('#f44336' if res['rsi_div'] == 'Bearish' else '#aaaaaa')
        
        macd_val = res['macd']
        c_macd = '#4caf50' if macd_val in ['Cross Up', 'Positive'] else '#f44336'
        c_macd_div = '#4caf50' if res['macd_div'] == 'Bullish' else ('#f44336' if res['macd_div'] == 'Bearish' else '#aaaaaa')

        # 'Ticker', 'Price', 'Return 23/03', 'MA20', 'MA50', 'MA100', 'MA200', 
        # '52w High', '52w Low', 'Breakout', 'RSI', 'RSI Div', 'MACD', 'MACD Div', 'Industry'
        self.window.scanner_table.setItem(row, 0, create_item(res['symbol'], '#90caf9'))
        self.window.scanner_table.setItem(row, 1, create_item(f"{price:,.2f}"))
        self.window.scanner_table.setItem(row, 2, create_item(f"{ret:,.2f}%", c_ret))
        self.window.scanner_table.setItem(row, 3, create_item("Above" if price > res['ma20'] else "Below", c_ma20))
        self.window.scanner_table.setItem(row, 4, create_item("Above" if price > res['ma50'] else "Below", c_ma50))
        self.window.scanner_table.setItem(row, 5, create_item("Above" if price > res['ma100'] else "Below", c_ma100))
        self.window.scanner_table.setItem(row, 6, create_item("Above" if price > res['ma200'] else "Below", c_ma200))
        self.window.scanner_table.setItem(row, 7, create_item(f"{res['high_52w']:,.2f}", c_high))
        self.window.scanner_table.setItem(row, 8, create_item(f"{res['low_52w']:,.2f}", c_low))
        self.window.scanner_table.setItem(row, 9, create_item(res['breakout_date']))
        self.window.scanner_table.setItem(row, 10, create_item(f"{res['rsi']:.2f}", c_rsi))
        self.window.scanner_table.setItem(row, 11, create_item(res['rsi_div'], c_rsi_div))
        self.window.scanner_table.setItem(row, 12, create_item(macd_val, c_macd))
        self.window.scanner_table.setItem(row, 13, create_item(res['macd_div'], c_macd_div))
        self.window.scanner_table.setItem(row, 14, create_item(res['industry']))
        self.apply_scanner_filters()

    def on_scan_finished(self):
        self.window.start_scan_btn.setEnabled(True)
        self.window.stop_scan_btn.setEnabled(False)
        self.window.export_scan_btn.setEnabled(True)
        self.window.export_market_btn.setEnabled(True)
        self.calculate_market_analysis()
        self.apply_scanner_filters()

    def apply_scanner_filters(self):
        industry_filter = self.window.filter_industry.currentText()
        rsi_filter = self.window.filter_rsi.currentText()
        macd_filter = self.window.filter_macd.currentText()
        
        for i in range(self.window.scanner_table.rowCount()):
            row_hidden = False
            
            # Check Industry
            ind_item = self.window.scanner_table.item(i, 14)
            if ind_item and industry_filter != "All Sectors":
                if ind_item.text() != industry_filter:
                    row_hidden = True
                    
            # Check RSI
            rsi_item = self.window.scanner_table.item(i, 10)
            if rsi_item and rsi_filter != "All RSI" and not row_hidden:
                try:
                    rsi_val = float(rsi_item.text())
                    if rsi_filter == "Oversold (<30)" and rsi_val >= 30:
                        row_hidden = True
                    elif rsi_filter == "Overbought (>70)" and rsi_val <= 70:
                        row_hidden = True
                    elif rsi_filter == "Bullish (>50)" and rsi_val <= 50:
                        row_hidden = True
                    elif rsi_filter == "Bearish (<50)" and rsi_val >= 50:
                        row_hidden = True
                except ValueError:
                    pass
                    
            # Check MACD
            macd_item = self.window.scanner_table.item(i, 12)
            if macd_item and macd_filter != "All MACD" and not row_hidden:
                if macd_filter == "Cross Up" and macd_item.text() != "Cross Up":
                    row_hidden = True
                elif macd_filter == "Cross Down" and macd_item.text() != "Cross Down":
                    row_hidden = True
                elif macd_filter == "Positive" and macd_item.text() not in ["Cross Up", "Positive"]:
                    row_hidden = True
                elif macd_filter == "Negative" and macd_item.text() not in ["Cross Down", "Negative"]:
                    row_hidden = True
                    
            self.window.scanner_table.setRowHidden(i, row_hidden)

    def on_export_scan_clicked(self):
        if not hasattr(self, 'scan_results') or not self.scan_results:
            return
        file_path, _ = QFileDialog.getSaveFileName(self.window, "Save Scan Results", "scan_results.csv", "CSV Files (*.csv)")
        if file_path:
            pd.DataFrame(self.scan_results).to_csv(file_path, index=False, encoding='utf-8-sig')
            QMessageBox.information(self.window, "Success", f"Scan results exported to {file_path}")

    def on_export_market_clicked(self):
        if not hasattr(self, 'scan_results') or not self.scan_results:
            return
        
        file_path, _ = QFileDialog.getSaveFileName(self.window, "Save Market Analysis", "market_analysis.xlsx", "Excel Files (*.xlsx)")
        if not file_path:
            return
            
        try:
            from scanner import VN302_INDUSTRIES
            df = pd.DataFrame(self.scan_results)
            stocks_df = df[df['symbol'] != 'VNINDEX']
            vnindex_ret = df[df['symbol'] == 'VNINDEX']['return_23_03'].iloc[0] if 'VNINDEX' in df['symbol'].values else 0
            
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                # 1. Summary Sheet
                industry_perf = stocks_df.groupby('industry')['return_23_03'].mean().reset_index()
                industry_perf['Relative_to_VNINDEX'] = industry_perf['return_23_03'] - vnindex_ret
                
                breadth = []
                for ma in ['ma20', 'ma50', 'ma100', 'ma200']:
                    above_pct = (stocks_df['price'] > stocks_df[ma]).mean() * 100
                    breadth.append({'Metric': f'Above {ma.upper()}', 'Percentage': f'{above_pct:.1f}%'})
                
                industry_perf.to_excel(writer, sheet_name='Industry_Summary', index=False)
                pd.DataFrame(breadth).to_excel(writer, sheet_name='Market_Breadth', index=False)
                
                # 2. Industry-specific Sheets
                for industry in VN302_INDUSTRIES.keys():
                    ind_df = stocks_df[stocks_df['industry'] == industry].copy()
                    if not ind_df.empty:
                        # Clean up for export
                        export_cols = ['symbol', 'price', 'return_23_03', 'ma20', 'ma50', 'ma100', 'ma200', 'high_52w', 'low_52w', 'breakout_date', 'rsi', 'macd']
                        # Use only existing columns
                        ind_df = ind_df[[c for c in export_cols if c in ind_df.columns]]
                        # Shorten sheet name if too long (Excel limit 31 chars)
                        sheet_name = (industry[:25] + '...') if len(industry) > 28 else industry
                        ind_df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # 3. All Tickers Sheet
                stocks_df.to_excel(writer, sheet_name='All_Tickers', index=False)
                
            QMessageBox.information(self.window, "Success", f"Market analysis exported to {file_path}")
        except Exception as e:
            QMessageBox.critical(self.window, "Error", f"Failed to export: {e}")

    def calculate_market_analysis(self):
        if not self.scan_results:
            return
            
        df = pd.DataFrame(self.scan_results)
        
        # 1. Market Breadth
        stocks_df = df[df['symbol'] != 'VNINDEX']
        if not stocks_df.empty:
            for ma in ['ma20', 'ma50', 'ma100', 'ma200']:
                above_pct = (stocks_df['price'] > stocks_df[ma]).mean() * 100
                self.window.breadth_widgets[ma.upper()].setText(f"{above_pct:.1f}%")
        
        # 2. Industry Analysis
        vnindex_ret = df[df['symbol'] == 'VNINDEX']['return_23_03'].iloc[0] if 'VNINDEX' in df['symbol'].values else 0
        
        # Group by industry and calculate mean return
        industry_perf = stocks_df.groupby('industry')['return_23_03'].mean().reset_index()
        
        # Get list of tickers for each industry
        # We use the VN302_INDUSTRIES mapping for this
        from scanner import VN302_INDUSTRIES
        
        industry_perf['tickers'] = industry_perf['industry'].apply(lambda x: ", ".join(VN302_INDUSTRIES.get(x, [])))
        industry_perf = industry_perf.sort_values('return_23_03', ascending=False)
        
        self.window.industry_table.setRowCount(len(industry_perf))
        for i, row in industry_perf.iterrows():
            ind_name = row['industry']
            tickers = row['tickers']
            ind_ret = row['return_23_03']
            rel_ret = ind_ret - vnindex_ret
            status = "Stronger" if rel_ret > 0 else "Weaker"
            
            c_ret = '#4caf50' if ind_ret > 0 else '#f44336'
            c_rel = '#4caf50' if rel_ret > 0 else '#f44336'
            
            def create_item(val, fg_color=None):
                item = QTableWidgetItem(str(val))
                if fg_color:
                    item.setForeground(QColor(fg_color))
                return item

            self.window.industry_table.setItem(i, 0, create_item(ind_name))
            self.window.industry_table.setItem(i, 1, create_item(tickers))
            self.window.industry_table.setItem(i, 2, create_item(f"{ind_ret:.2f}%", c_ret))
            self.window.industry_table.setItem(i, 3, create_item(f"{rel_ret:+.2f}%", c_rel))
            self.window.industry_table.setItem(i, 4, create_item(status, c_rel))
            
        # 3. Update Sector Heatmap Cards
        for ind_name in VN302_INDUSTRIES.keys():
            if ind_name in self.window.heatmap_cards:
                card_data = self.window.heatmap_cards[ind_name]
                
                # Filter tickers for this industry in scan_results
                ind_stocks = stocks_df[stocks_df['industry'] == ind_name]
                if not ind_stocks.empty:
                    mean_ret = ind_stocks['return_23_03'].mean()
                    above_ma50 = (ind_stocks['price'] > ind_stocks['ma50']).mean() * 100
                    
                    # Update texts
                    card_data['ret'].setText(f"{mean_ret:+.2f}%")
                    card_data['breadth'].setText(f"Above MA50: {above_ma50:.0f}%")
                    
                    # Determine background color based on return
                    if mean_ret >= 3.0:
                        bg_color = "#1b5e20" # Strong Green
                        text_color = "#a5d6a7"
                    elif mean_ret >= 1.0:
                        bg_color = "#2e7d32" # Mild Green
                        text_color = "#c8e6c9"
                    elif mean_ret >= 0.2:
                        bg_color = "#4caf50" # Light Green
                        text_color = "#e8f5e9"
                    elif mean_ret <= -3.0:
                        bg_color = "#b71c1c" # Strong Red
                        text_color = "#ef9a9a"
                    elif mean_ret <= -1.0:
                        bg_color = "#c62828" # Mild Red
                        text_color = "#ffcdd2"
                    elif mean_ret <= -0.2:
                        bg_color = "#e53935" # Light Red
                        text_color = "#ffebee"
                    else:
                        bg_color = "#424242" # Neutral Grey
                        text_color = "#e0e0e0"
                        
                    card_data['frame'].setStyleSheet(f"""
                        QFrame#HeatmapCard {{
                            background-color: {bg_color};
                            border: 2px solid #555;
                            border-radius: 12px;
                        }}
                    """)
                    card_data['ret'].setStyleSheet(f"font-size: 24px; font-weight: bold; color: {text_color};")

    def on_industry_selection_changed(self):
        selected_items = self.window.industry_table.selectedItems()
        if not selected_items:
            return
            
        industry = self.window.industry_table.item(selected_items[0].row(), 0).text()
        self.show_industry_details(industry)

    def show_industry_details(self, industry):
        if not hasattr(self, 'scan_results') or not self.scan_results:
            return
            
        df = pd.DataFrame(self.scan_results)
        vnindex_ret = df[df['symbol'] == 'VNINDEX']['return_23_03'].iloc[0] if 'VNINDEX' in df['symbol'].values else 0
        
        industry_df = df[df['industry'] == industry].copy()
        industry_df = industry_df.sort_values('return_23_03', ascending=False)
        
        self.window.detail_label.setText(f"Details for {industry}")
        self.window.industry_detail_table.setRowCount(len(industry_df))
        
        for i, (_, row) in enumerate(industry_df.iterrows()):
            ticker = row['symbol']
            ret = row['return_23_03']
            rel_ret = ret - vnindex_ret
            
            c_ret = '#4caf50' if ret > 0 else '#f44336'
            c_rel = '#4caf50' if rel_ret > 0 else '#f44336'
            
            def create_item(val, fg_color=None):
                item = QTableWidgetItem(str(val))
                if fg_color:
                    item.setForeground(QColor(fg_color))
                return item

            self.window.industry_detail_table.setItem(i, 0, create_item(ticker, '#90caf9'))
            self.window.industry_detail_table.setItem(i, 1, create_item(f"{ret:.2f}%", c_ret))
            self.window.industry_detail_table.setItem(i, 2, create_item(f"{rel_ret:+.2f}%", c_rel))

    def on_scan_error(self, err_msg):
        print(err_msg)

    def on_scanner_row_double_clicked(self, row, col):
        ticker_item = self.window.scanner_table.item(row, 0)
        if ticker_item:
            ticker = ticker_item.text()
            self.window.ticker_input.setCurrentText(ticker)
            self.window.tabs.setCurrentWidget(self.window.tab_backtester)
            self.on_run_clicked()

    # --- Antigravity Methods ---
    def on_start_anti_scan(self):
        self.window.anti_table.setRowCount(0)
        self.window.anti_progress.setValue(0)
        self.window.start_anti_btn.setEnabled(False)
        self.window.stop_anti_btn.setEnabled(True)
        self.window.export_anti_btn.setEnabled(False)
        self.anti_results = []
        
        self.anti_thread = AntigravityThread(self.engine)
        self.anti_thread.progress_update.connect(lambda c, t: self.window.anti_progress.setValue(c))
        self.anti_thread.progress_update.connect(lambda c, t: self.window.anti_progress.setMaximum(t))
        self.anti_thread.signal_found.connect(self.on_anti_signal_found)
        self.anti_thread.finished_scan.connect(self.on_anti_scan_finished)
        self.anti_thread.error_signal.connect(self.on_scan_error)
        self.anti_thread.start()

    def on_stop_anti_scan(self):
        if self.anti_thread and self.anti_thread.isRunning():
            self.anti_thread.stop()
            self.window.stop_anti_btn.setEnabled(False)

    def on_anti_signal_found(self, sig):
        self.anti_results.append(sig)
        row = self.window.anti_table.rowCount()
        self.window.anti_table.insertRow(row)
        
        def create_item(val, color=None):
            item = QTableWidgetItem(str(val))
            if color: item.setForeground(QColor(color))
            return item

        self.window.anti_table.setItem(row, 0, create_item(sig['symbol'], '#90caf9'))
        self.window.anti_table.setItem(row, 1, create_item(str(sig['date'].date())))
        self.window.anti_table.setItem(row, 2, create_item(sig['days_in_setup']))
        
        for i, k in enumerate(['ret5', 'ret10', 'ret20']):
            val = sig[k]
            if val is not None:
                color = '#4caf50' if val > 0 else '#f44336'
                self.window.anti_table.setItem(row, 3 + i, create_item(f"{val:.2f}%", color))
            else:
                self.window.anti_table.setItem(row, 3 + i, create_item("N/A"))
        
        self.window.anti_table.setItem(row, 6, create_item(f"{sig['rr']:.2f}"))

    def on_anti_scan_finished(self, summary):
        self.window.start_anti_btn.setEnabled(True)
        self.window.stop_anti_btn.setEnabled(False)
        self.window.export_anti_btn.setEnabled(len(self.anti_results) > 0)
        
        if summary:
            self.window.anti_metric_widgets['Avg Days Setup'].setText(f"{summary['avg_days']:.1f}")
            self.window.anti_metric_widgets['Win Rate 5D'].setText(f"{summary['win5']:.1f}%")
            self.window.anti_metric_widgets['Win Rate 10D'].setText(f"{summary['win10']:.1f}%")
            self.window.anti_metric_widgets['Win Rate 20D'].setText(f"{summary['win20']:.1f}%")
            self.window.anti_metric_widgets['Avg R/R'].setText(f"{summary['avg_rr']:.2f}")

    def on_export_anti_clicked(self):
        if not self.anti_results: return
        file_path, _ = QFileDialog.getSaveFileName(self.window, "Save Antigravity Results", "antigravity_signals.xlsx", "Excel Files (*.xlsx)")
        if file_path:
            pd.DataFrame(self.anti_results).to_excel(file_path, index=False)
            QMessageBox.information(self.window, "Success", f"Results exported to {file_path}")

    # --- Watchlist Methods ---
    def on_start_watch_scan(self):
        self.window.watch_table.setRowCount(0)
        self.window.watch_progress.setValue(0)
        self.window.start_watch_btn.setEnabled(False)
        self.window.stop_watch_btn.setEnabled(True)
        self.window.export_watch_btn.setEnabled(False)
        self.watch_results = []
        
        self.watch_thread = WatchlistThread(self.engine)
        self.watch_thread.progress_update.connect(lambda c, t: self.window.watch_progress.setValue(c))
        self.watch_thread.progress_update.connect(lambda c, t: self.window.watch_progress.setMaximum(t))
        self.watch_thread.stock_found.connect(self.on_watch_stock_found)
        self.watch_thread.finished_scan.connect(self.on_watch_scan_finished)
        self.watch_thread.error_signal.connect(self.on_scan_error)
        self.watch_thread.start()

    def on_stop_watch_scan(self):
        if self.watch_thread and self.watch_thread.isRunning():
            self.watch_thread.stop()
            self.window.stop_watch_btn.setEnabled(False)

    def on_watch_stock_found(self, data):
        self.watch_results.append(data)
        row = self.window.watch_table.rowCount()
        self.window.watch_table.insertRow(row)
        
        def create_item(val, color=None):
            item = QTableWidgetItem(str(val))
            if color: item.setForeground(QColor(color))
            return item

        self.window.watch_table.setItem(row, 0, create_item(data['symbol'], '#90caf9'))
        self.window.watch_table.setItem(row, 1, create_item(f"{data['price']:,.2f}"))
        self.window.watch_table.setItem(row, 2, create_item(data['streak']))
        self.window.watch_table.setItem(row, 3, create_item(f"{data['vol_ratio']:.2f}"))
        self.window.watch_table.setItem(row, 4, create_item(f"{data['range_pct']:.2f}%"))

    def on_watch_scan_finished(self):
        self.window.start_watch_btn.setEnabled(True)
        self.window.stop_watch_btn.setEnabled(False)
        self.window.export_watch_btn.setEnabled(len(self.watch_results) > 0)

    def on_export_watch_clicked(self):
        if not self.watch_results: return
        file_path, _ = QFileDialog.getSaveFileName(self.window, "Save Watchlist", "antigravity_watchlist.xlsx", "Excel Files (*.xlsx)")
        if file_path:
            pd.DataFrame(self.watch_results).to_excel(file_path, index=False)
            QMessageBox.information(self.window, "Success", f"Watchlist exported to {file_path}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    controller = Controller()
    controller.window.show()
    sys.exit(app.exec())
