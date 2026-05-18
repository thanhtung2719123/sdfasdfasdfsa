from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QComboBox, QDateEdit, 
                             QGroupBox, QFormLayout, QFrame, QScrollArea, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QFileDialog, QTabWidget, QProgressBar,
                             QGridLayout)
from PySide6.QtCore import Qt, QDate, QPointF, QRectF
from PySide6.QtGui import QPainter, QPicture, QBrush, QPen, QColor
import pyqtgraph as pg
import pandas as pd
import numpy as np

class CandlestickItem(pg.GraphicsObject):
    def __init__(self, data):
        pg.GraphicsObject.__init__(self)
        self.data = data  # list of (t, open, close, min, max)
        self.generatePicture()

    def generatePicture(self):
        self.picture = QPicture()
        p = QPainter(self.picture)
        w = 0.8  # Thicker bodies for visibility
        for (t, open, close, min, max) in self.data:
            bullish = close >= open
            body_color = QColor('#26a69a') if bullish else QColor('#ef5350')
            wick_color = QColor('#757575') # Neutral gray wicks for better focus
            
            # Draw wick (Thin line)
            p.setPen(QPen(wick_color, 0)) 
            p.drawLine(QPointF(t, min), QPointF(t, max))
            
            # Draw body (Solid rectangle)
            p.setPen(QPen(body_color, 0))
            p.setBrush(QBrush(body_color))
            
            # Draw body
            if abs(open - close) < 0.0001: # Avoid invisible body for flat days
                p.drawLine(QPointF(t-w/2, open), QPointF(t+w/2, open))
            else:
                p.drawRect(QRectF(t-w/2, open, w, close-open))
        p.end()

    def paint(self, p, *args):
        p.drawPicture(0, 0, self.picture)

    def boundingRect(self):
        return QRectF(self.picture.boundingRect())

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VNStock RSI Backtester - Premium Suite")
        self.resize(1200, 800)
        self.setStyleSheet("""
            QMainWindow { background-color: #0b0c10; color: #c5c6c7; }
            QWidget { background-color: #0b0c10; color: #c5c6c7; font-family: 'Segoe UI', -apple-system, Roboto, sans-serif; }
            QGroupBox { border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; margin-top: 15px; padding: 15px; font-weight: bold; background-color: rgba(30, 30, 30, 0.4); }
            QPushButton { 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1f4068, stop:1 #162447); 
                color: #ffffff; 
                border: 1px solid rgba(255, 255, 255, 0.15); 
                padding: 10px 15px; 
                border-radius: 8px; 
                font-weight: bold; 
                font-size: 12px;
            }
            QPushButton:hover { 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #00e5ff, stop:1 #0083b0); 
                border: 1px solid #00e5ff;
            }
            QPushButton:pressed {
                background: #0083b0;
            }
            QPushButton:disabled { 
                background-color: #242526; 
                color: #5f6368; 
                border: 1px solid #1a1a1a;
            }
            QLineEdit, QComboBox, QDateEdit { 
                background-color: rgba(40, 40, 40, 0.6); 
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 0.1); 
                padding: 6px; 
                border-radius: 6px; 
                selection-background-color: #00b4db;
            }
            QLineEdit:focus, QComboBox:focus, QDateEdit:focus {
                border: 1px solid #00e5ff;
                background-color: rgba(50, 50, 50, 0.8);
            }
            QLabel#MetricLabel { font-size: 13px; font-weight: bold; color: #00e5ff; text-transform: uppercase; letter-spacing: 0.5px; }
            QLabel#MetricValue { font-size: 22px; font-weight: bold; color: #ffffff; }
            QFrame#Card { 
                background-color: rgba(30, 30, 30, 0.65); 
                border: 1px solid rgba(255, 255, 255, 0.12); 
                border-radius: 12px; 
                padding: 12px; 
            }
            QFrame#Card:hover {
                border: 1px solid rgba(0, 229, 255, 0.5);
                background-color: rgba(35, 35, 35, 0.8);
            }
            QTabWidget::pane { border: 1px solid rgba(255, 255, 255, 0.08); background: #0b0c10; border-radius: 8px; }
            QTabBar::tab { 
                background: rgba(25, 25, 25, 0.5); 
                color: #a8a8a8; 
                padding: 12px 24px; 
                border: 1px solid rgba(255, 255, 255, 0.05); 
                border-bottom: none; 
                border-top-left-radius: 8px; 
                border-top-right-radius: 8px; 
                margin-right: 2px;
            }
            QTabBar::tab:hover {
                background: rgba(35, 35, 35, 0.7);
                color: #ffffff;
            }
            QTabBar::tab:selected { 
                background: rgba(45, 45, 45, 0.95); 
                color: #00e5ff; 
                font-weight: bold; 
                border-top: 3px solid #00e5ff; 
            }
            QProgressBar { border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 6px; text-align: center; background-color: rgba(40, 40, 40, 0.5); color: #ffffff; font-weight: bold; }
            QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00e5ff, stop:1 #0083b0); border-radius: 5px; }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_app_layout = QVBoxLayout(central_widget)
        
        self.tabs = QTabWidget()
        main_app_layout.addWidget(self.tabs)
        
        # --- TAB 1: BACKTESTER ---
        self.tab_backtester = QWidget()
        main_layout = QHBoxLayout(self.tab_backtester)


        # Sidebar
        sidebar = QWidget()
        sidebar.setFixedWidth(300)
        sidebar_layout = QVBoxLayout(sidebar)
        
        config_group = QGroupBox("Configuration")
        config_form = QFormLayout()
        
        self.ticker_input = QComboBox()
        self.ticker_input.setEditable(True)
        
        self.rsi_period = QLineEdit("14")
        self.buy_threshold = QLineEdit("30")
        self.sell_threshold = QLineEdit("70")
        
        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addYears(-1))
        self.start_date.setCalendarPopup(True)
        
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        
        self.initial_capital = QLineEdit("100000000") # 100M VND default
        self.stop_loss_input = QLineEdit("5.0")
        self.take_profit_input = QLineEdit("10.0")
        self.position_size_input = QLineEdit("100.0")
        
        config_form.addRow("Ticker:", self.ticker_input)
        config_form.addRow("RSI Period:", self.rsi_period)
        config_form.addRow("Buy RSI <:", self.buy_threshold)
        config_form.addRow("Sell RSI >:", self.sell_threshold)
        config_form.addRow("Start Date:", self.start_date)
        config_form.addRow("End Date:", self.end_date)
        config_form.addRow("Initial Capital:", self.initial_capital)
        config_form.addRow("Stop Loss (%):", self.stop_loss_input)
        config_form.addRow("Take Profit (%):", self.take_profit_input)
        config_form.addRow("Position Size (%):", self.position_size_input)
        
        config_group.setLayout(config_form)
        sidebar_layout.addWidget(config_group)
        
        self.run_btn = QPushButton("Run Backtest")
        sidebar_layout.addWidget(self.run_btn)
        
        self.export_btn = QPushButton("Export Trades")
        self.export_btn.setEnabled(False)
        sidebar_layout.addWidget(self.export_btn)
        
        # Source Selection
        self.source_input = QComboBox()
        self.source_input.addItems(['KBS', 'VCI'])
        config_form.addRow("Data Source:", self.source_input)
        
        sidebar_layout.addStretch()
        main_layout.addWidget(sidebar)

        # Content Area
        content = QWidget()
        content_layout = QVBoxLayout(content)
        
        # Info label
        self.df_chart_data = pd.DataFrame()
        self.label_info = QLabel("Hover over chart to see details")
        self.label_info.setStyleSheet("font-size: 13px; font-weight: bold; color: #90caf9; padding: 5px;")
        content_layout.addWidget(self.label_info)
        
        # Chart Tabs (Toggle between Price/Volume/RSI and Equity Curve)
        self.chart_tabs = QTabWidget()
        
        # Tab 1: Technical Analysis (Price, Vol, RSI)
        ta_widget = QWidget()
        ta_layout = QVBoxLayout(ta_widget)
        ta_layout.setContentsMargins(0, 0, 0, 0)
        
        self.plot_widget = pg.PlotWidget(title="Price Chart")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        
        self.volume_widget = pg.PlotWidget(title="Volume")
        self.volume_widget.showGrid(x=True, y=True, alpha=0.3)
        self.volume_widget.setXLink(self.plot_widget)
        
        self.rsi_widget = pg.PlotWidget(title="RSI")
        self.rsi_widget.showGrid(x=True, y=True, alpha=0.3)
        self.rsi_widget.setYRange(0, 100)
        self.rsi_widget.setXLink(self.plot_widget)
        
        ta_layout.addWidget(self.plot_widget, stretch=4)
        ta_layout.addWidget(self.volume_widget, stretch=1.5)
        ta_layout.addWidget(self.rsi_widget, stretch=1.5)
        
        # Tab 2: Performance (Equity Curve vs Benchmark)
        self.equity_widget = pg.PlotWidget(title="Equity Curve vs Benchmark (Buy & Hold)")
        self.equity_widget.showGrid(x=True, y=True, alpha=0.3)
        
        self.chart_tabs.addTab(ta_widget, "📊 Price & Indicators")
        self.chart_tabs.addTab(self.equity_widget, "📈 Equity & Benchmark")
        
        content_layout.addWidget(self.chart_tabs, stretch=7)
        
        # Metrics Panel
        metrics_scroll = QScrollArea()
        metrics_scroll.setWidgetResizable(True)
        metrics_scroll.setFixedHeight(150)
        metrics_container = QWidget()
        self.metrics_layout = QHBoxLayout(metrics_container)
        
        self.metric_widgets = {}
        for metric in ['Net Profit', 'Win Rate', 'Profit Factor', 'Max Drawdown', 'Sharpe Ratio', 'Sortino Ratio', 'DD Duration (Days)', 'Avg Duration']:
            card = QFrame()
            card.setObjectName("Card")
            card.setMinimumWidth(150)
            vbox = QVBoxLayout(card)
            lbl = QLabel(metric)
            lbl.setObjectName("MetricLabel")
            val = QLabel("0.00")
            val.setObjectName("MetricValue")
            vbox.addWidget(lbl)
            vbox.addWidget(val)
            self.metric_widgets[metric] = val
            self.metrics_layout.addWidget(card)
        
        metrics_scroll.setWidget(metrics_container)
        content_layout.addWidget(metrics_scroll)
        
        # Trade Table
        self.trade_table = QTableWidget()
        self.trade_table.setColumnCount(6)
        self.trade_table.setHorizontalHeaderLabels(['Entry', 'Exit', 'Entry Price', 'Exit Price', 'Profit', 'Profit %'])
        self.trade_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.trade_table.setStyleSheet("QTableWidget { background-color: #1e1e1e; color: #fff; }")
        self.trade_table.setFixedHeight(200)
        self.trade_table.setFixedHeight(200)
        content_layout.addWidget(self.trade_table)
        
        main_layout.addWidget(content)
        self.tabs.addTab(self.tab_backtester, "Backtester")

        # --- TAB 2: SCANNER ---
        self.tab_scanner = QWidget()
        scanner_layout = QVBoxLayout(self.tab_scanner)

        # Scanner controls
        scan_controls = QHBoxLayout()
        self.start_scan_btn = QPushButton("Start VN273 Scan")
        self.stop_scan_btn = QPushButton("Stop Scan")
        self.stop_scan_btn.setEnabled(False)
        self.stop_scan_btn.setStyleSheet("background-color: #ef5350;")
        
        self.scan_progress = QProgressBar()
        self.scan_progress.setValue(0)
        self.scan_progress.setTextVisible(True)
        
        self.export_scan_btn = QPushButton("Export Scan CSV")
        self.export_scan_btn.setEnabled(False)
        
        scan_controls.addWidget(self.start_scan_btn)
        scan_controls.addWidget(self.stop_scan_btn)
        scan_controls.addWidget(self.export_scan_btn)
        scan_controls.addWidget(self.scan_progress)
        scanner_layout.addLayout(scan_controls)

        # Import VN302_INDUSTRIES for sector list
        from scanner import VN302_INDUSTRIES
        
        # Filter controls
        filter_bar = QHBoxLayout()
        
        self.filter_industry = QComboBox()
        self.filter_industry.addItems(["All Sectors"] + list(VN302_INDUSTRIES.keys()))
        self.filter_industry.setStyleSheet("QComboBox { background-color: #2c2c2c; color: #fff; padding: 4px; border: 1px solid #555; border-radius: 4px; }")
        
        self.filter_rsi = QComboBox()
        self.filter_rsi.addItems(["All RSI", "Oversold (<30)", "Overbought (>70)", "Bullish (>50)", "Bearish (<50)"])
        self.filter_rsi.setStyleSheet("QComboBox { background-color: #2c2c2c; color: #fff; padding: 4px; border: 1px solid #555; border-radius: 4px; }")
        
        self.filter_macd = QComboBox()
        self.filter_macd.addItems(["All MACD", "Cross Up", "Cross Down", "Positive", "Negative"])
        self.filter_macd.setStyleSheet("QComboBox { background-color: #2c2c2c; color: #fff; padding: 4px; border: 1px solid #555; border-radius: 4px; }")
        
        lbl_sec = QLabel("Filter Sector:")
        lbl_sec.setStyleSheet("font-weight: bold; color: #90caf9;")
        lbl_rsi = QLabel("RSI:")
        lbl_rsi.setStyleSheet("font-weight: bold; color: #90caf9;")
        lbl_macd = QLabel("MACD:")
        lbl_macd.setStyleSheet("font-weight: bold; color: #90caf9;")
        
        filter_bar.addWidget(lbl_sec)
        filter_bar.addWidget(self.filter_industry)
        filter_bar.addWidget(lbl_rsi)
        filter_bar.addWidget(self.filter_rsi)
        filter_bar.addWidget(lbl_macd)
        filter_bar.addWidget(self.filter_macd)
        filter_bar.addStretch()
        
        scanner_layout.addLayout(filter_bar)

        # Scanner Table
        self.scanner_table = QTableWidget()
        self.scanner_table.setColumnCount(15)
        self.scanner_table.setHorizontalHeaderLabels([
            'Ticker', 'Price', 'Return 23/03/26', 'MA20', 'MA50', 'MA100', 'MA200', 
            '52w High', '52w Low', 'Breakout', 'RSI', 'RSI Div', 'MACD', 'MACD Div', 'Industry'
        ])
        self.scanner_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.scanner_table.setStyleSheet("QTableWidget { background-color: #1e1e1e; color: #fff; gridline-color: #333; } QHeaderView::section { background-color: #2c2c2c; padding: 4px; border: 1px solid #444; font-weight: bold; }")
        self.scanner_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.scanner_table.setSelectionBehavior(QTableWidget.SelectRows)
        scanner_layout.addWidget(self.scanner_table)
        self.tabs.addTab(self.tab_scanner, "VN273 Scanner")

        # --- TAB 3: SECTOR HEATMAP ---
        self.tab_heatmap = QWidget()
        heatmap_layout = QVBoxLayout(self.tab_heatmap)
        
        # Add scroll area for the cards
        heatmap_scroll = QScrollArea()
        heatmap_scroll.setWidgetResizable(True)
        heatmap_container = QWidget()
        self.heatmap_grid = QGridLayout(heatmap_container)
        self.heatmap_grid.setSpacing(15)
        
        self.heatmap_cards = {}
        
        for idx, ind in enumerate(VN302_INDUSTRIES.keys()):
            card = QFrame()
            card.setFrameShape(QFrame.StyledPanel)
            card.setObjectName("HeatmapCard")
            card.setMinimumSize(180, 150)
            card.setStyleSheet("""
                QFrame#HeatmapCard {
                    background-color: #2c2c2c;
                    border: 2px solid #444;
                    border-radius: 12px;
                }
            """)
            
            card_layout = QVBoxLayout(card)
            
            lbl_title = QLabel(ind)
            lbl_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #fff;")
            lbl_title.setWordWrap(True)
            
            lbl_ret = QLabel("0.00%")
            lbl_ret.setStyleSheet("font-size: 24px; font-weight: bold; color: #757575;")
            
            lbl_breadth = QLabel("Above MA50: N/A")
            lbl_breadth.setStyleSheet("font-size: 11px; color: #b0bec5;")
            
            card_layout.addWidget(lbl_title)
            card_layout.addWidget(lbl_ret)
            card_layout.addWidget(lbl_breadth)
            card_layout.addStretch()
            
            self.heatmap_cards[ind] = {
                'frame': card,
                'ret': lbl_ret,
                'breadth': lbl_breadth
            }
            
            row = idx // 4
            col = idx % 4
            self.heatmap_grid.addWidget(card, row, col)
            
        heatmap_scroll.setWidget(heatmap_container)
        heatmap_layout.addWidget(heatmap_scroll)
        self.tabs.addTab(self.tab_heatmap, "🔥 Sector Heatmap")

        # --- TAB 4: MARKET ANALYSIS ---
        self.tab_market = QWidget()
        market_layout = QVBoxLayout(self.tab_market)
        
        # Breadth Metrics
        breadth_group = QGroupBox("Market Breadth (% Stocks Above MA)")
        breadth_layout = QHBoxLayout()
        self.breadth_widgets = {}
        for ma in ['MA20', 'MA50', 'MA100', 'MA200']:
            card = QFrame()
            card.setObjectName("Card")
            card.setMinimumWidth(120)
            vbox = QVBoxLayout(card)
            lbl = QLabel(f"Above {ma}")
            lbl.setObjectName("MetricLabel")
            val = QLabel("0.0%")
            val.setObjectName("MetricValue")
            vbox.addWidget(lbl)
            vbox.addWidget(val)
            self.breadth_widgets[ma] = val
            breadth_layout.addWidget(card)
        
        self.export_market_btn = QPushButton("Export Market Excel")
        self.export_market_btn.setEnabled(False)
        self.export_market_btn.setFixedWidth(150)
        breadth_layout.addWidget(self.export_market_btn)
        
        breadth_group.setLayout(breadth_layout)
        market_layout.addWidget(breadth_group)
        
        # Industry Table
        self.industry_table = QTableWidget()
        self.industry_table.setColumnCount(5)
        self.industry_table.setHorizontalHeaderLabels(['Industry', 'Tickers', 'Return (23/03/26)', 'Relative to VNINDEX', 'Status'])
        self.industry_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.industry_table.setStyleSheet("QTableWidget { background-color: #1e1e1e; color: #fff; }")
        market_layout.addWidget(self.industry_table)

        # Industry Detail Title
        self.detail_label = QLabel("Industry Details (Select an industry above)")
        self.detail_label.setObjectName("MetricLabel")
        market_layout.addWidget(self.detail_label)
        
        # Industry Detail Table
        self.industry_detail_table = QTableWidget()
        self.industry_detail_table.setColumnCount(3)
        self.industry_detail_table.setHorizontalHeaderLabels(['Ticker', 'Return (23/03/26)', 'Relative to VNINDEX'])
        self.industry_detail_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.industry_detail_table.setStyleSheet("QTableWidget { background-color: #1e1e1e; color: #fff; }")
        market_layout.addWidget(self.industry_detail_table)
        
        self.tabs.addTab(self.tab_market, "Market Analysis")

        # --- TAB 4: ANTIGRAVITY VOLATILITY ---
        self.tab_antigravity = QWidget()
        antigravity_layout = QVBoxLayout(self.tab_antigravity)

        # Controls
        anti_controls = QHBoxLayout()
        self.start_anti_btn = QPushButton("Start Antigravity Scan")
        self.stop_anti_btn = QPushButton("Stop Scan")
        self.stop_anti_btn.setEnabled(False)
        self.stop_anti_btn.setStyleSheet("background-color: #ef5350;")
        
        self.export_anti_btn = QPushButton("Export Excel")
        self.export_anti_btn.setEnabled(False)
        self.export_anti_btn.setStyleSheet("background-color: #4caf50;")
        
        self.anti_progress = QProgressBar()
        self.anti_progress.setValue(0)
        
        anti_controls.addWidget(self.start_anti_btn)
        anti_controls.addWidget(self.stop_anti_btn)
        anti_controls.addWidget(self.export_anti_btn)
        anti_controls.addWidget(self.anti_progress)
        antigravity_layout.addLayout(anti_controls)

        # Stats Cards
        self.anti_stats_layout = QHBoxLayout()
        self.anti_metric_widgets = {}
        for metric in ['Avg Days Setup', 'Win Rate 5D', 'Win Rate 10D', 'Win Rate 20D', 'Avg R/R']:
            card = QFrame()
            card.setObjectName("Card")
            vbox = QVBoxLayout(card)
            lbl = QLabel(metric)
            lbl.setObjectName("MetricLabel")
            val = QLabel("0.0")
            val.setObjectName("MetricValue")
            vbox.addWidget(lbl)
            vbox.addWidget(val)
            self.anti_metric_widgets[metric] = val
            self.anti_stats_layout.addWidget(card)
        antigravity_layout.addLayout(self.anti_stats_layout)

        # Signals Table
        self.anti_table = QTableWidget()
        self.anti_table.setColumnCount(7)
        self.anti_table.setHorizontalHeaderLabels([
            'Ticker', 'Date', 'Days in Setup', 'Return 5D', 'Return 10D', 'Return 20D', 'R/R'
        ])
        self.anti_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.anti_table.setStyleSheet("QTableWidget { background-color: #1e1e1e; color: #fff; }")
        antigravity_layout.addWidget(self.anti_table)

        self.tabs.addTab(self.tab_antigravity, "Antigravity Vol")

        # --- TAB 5: ANTIGRAVITY WATCHLIST ---
        self.tab_watchlist = QWidget()
        watchlist_layout = QVBoxLayout(self.tab_watchlist)

        # Controls
        watch_controls = QHBoxLayout()
        self.start_watch_btn = QPushButton("Start Watchlist Scan")
        self.stop_watch_btn = QPushButton("Stop Scan")
        self.stop_watch_btn.setEnabled(False)
        self.stop_watch_btn.setStyleSheet("background-color: #ef5350;")
        
        self.export_watch_btn = QPushButton("Export Excel")
        self.export_watch_btn.setEnabled(False)
        
        self.watch_progress = QProgressBar()
        self.watch_progress.setValue(0)
        
        watch_controls.addWidget(self.start_watch_btn)
        watch_controls.addWidget(self.stop_watch_btn)
        watch_controls.addWidget(self.export_watch_btn)
        watch_controls.addWidget(self.watch_progress)
        watchlist_layout.addLayout(watch_controls)

        # Watchlist Table
        self.watch_table = QTableWidget()
        self.watch_table.setColumnCount(5)
        self.watch_table.setHorizontalHeaderLabels([
            'Ticker', 'Current Price', 'Days in Consolidation', 'Current Vol/MA20', '5-Day Range %'
        ])
        self.watch_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.watch_table.setStyleSheet("QTableWidget { background-color: #1e1e1e; color: #fff; }")
        watchlist_layout.addWidget(self.watch_table)

        self.tabs.addTab(self.tab_watchlist, "Antigravity Watchlist")

    def update_trades_table(self, trades):
        self.trade_table.setRowCount(len(trades))
        for i, trade in enumerate(trades):
            self.trade_table.setItem(i, 0, QTableWidgetItem(str(trade['entry_time'].date())))
            self.trade_table.setItem(i, 1, QTableWidgetItem(str(trade['exit_time'].date())))
            self.trade_table.setItem(i, 2, QTableWidgetItem(f"{trade['entry_price']:,.2f}"))
            self.trade_table.setItem(i, 3, QTableWidgetItem(f"{trade['exit_price']:,.2f}"))
            
            p_item = QTableWidgetItem(f"{trade['profit']:,.2f}")
            p_item.setForeground(pg.mkBrush('g') if trade['profit'] > 0 else pg.mkBrush('r'))
            self.trade_table.setItem(i, 4, p_item)
            
            p_pct_item = QTableWidgetItem(f"{trade['profit_pct']:.2f}%")
            p_pct_item.setForeground(pg.mkBrush('g') if trade['profit_pct'] > 0 else pg.mkBrush('r'))
            self.trade_table.setItem(i, 5, p_pct_item)

    def update_metrics(self, metrics):
        self.metric_widgets['Net Profit'].setText(f"{metrics['net_profit']:,.2f} Đ")
        self.metric_widgets['Win Rate'].setText(f"{metrics['win_rate']:.2f}%")
        self.metric_widgets['Profit Factor'].setText(f"{metrics['profit_factor']:.2f}")
        self.metric_widgets['Max Drawdown'].setText(f"{metrics['max_drawdown']:.1f}%")
        self.metric_widgets['Sharpe Ratio'].setText(f"{metrics['sharpe_ratio']:.2f}")
        self.metric_widgets['Sortino Ratio'].setText(f"{metrics.get('sortino_ratio', 0.0):.2f}")
        self.metric_widgets['DD Duration (Days)'].setText(f"{metrics.get('drawdown_duration', 0.0):.0f}")
        self.metric_widgets['Avg Duration'].setText(f"{metrics['avg_duration']:.1f} Days")

    def plot_data(self, df, trades, equity_curve=None, benchmark_curve=None):
        self.plot_widget.clear()
        self.volume_widget.clear()
        self.rsi_widget.clear()
        self.equity_widget.clear()
        
        if df.empty or 'rsi' not in df.columns:
            return
            
        self.df_chart_data = df.copy()
        t = np.arange(len(df))
        
        # Plot Equity & Benchmark Curves
        if equity_curve and benchmark_curve:
            eq_t = np.arange(len(equity_curve))
            eq_vals = [x['equity'] for x in equity_curve]
            bm_vals = [x['equity'] for x in benchmark_curve]
            
            self.equity_widget.plot(eq_t, eq_vals, pen=pg.mkPen('#00e5ff', width=2.0), name="Strategy")
            self.equity_widget.plot(eq_t, bm_vals, pen=pg.mkPen('#757575', width=1.5, style=Qt.DashLine), name="Benchmark (Buy & Hold)")
            
            # Ensure Legend exists
            if not self.equity_widget.plotItem.legend:
                self.equity_widget.addLegend(offset=(30, 30))
            
        self.df_chart_data = df.copy()
        t = np.arange(len(df))
        
        # 1. Candlestick Chart
        candles = []
        for i, row in df.iterrows():
            candles.append((i, row['open'], row['close'], row['low'], row['high']))
        item = CandlestickItem(candles)
        self.plot_widget.addItem(item)
        
        # 2. Moving Averages
        df_ma20 = df['close'].rolling(20).mean()
        df_ma50 = df['close'].rolling(50).mean()
        df_ma100 = df['close'].rolling(100).mean()
        df_ma200 = df['close'].rolling(200).mean()
        
        if len(df) >= 20:
            self.plot_widget.plot(t, df_ma20.values, pen=pg.mkPen('#e57373', width=1.2), name="MA20")
        if len(df) >= 50:
            self.plot_widget.plot(t, df_ma50.values, pen=pg.mkPen('#ffb74d', width=1.2), name="MA50")
        if len(df) >= 100:
            self.plot_widget.plot(t, df_ma100.values, pen=pg.mkPen('#4db6ac', width=1.2), name="MA100")
        if len(df) >= 200:
            self.plot_widget.plot(t, df_ma200.values, pen=pg.mkPen('#7986cb', width=1.2), name="MA200")
            
        # 3. Bollinger Bands
        if len(df) >= 20:
            std20 = df['close'].rolling(20).std()
            upper_bb = df_ma20 + 2 * std20
            lower_bb = df_ma20 - 2 * std20
            
            self.plot_widget.plot(t, upper_bb.values, pen=pg.mkPen('#42a5f5', style=Qt.DashLine, width=1.0))
            self.plot_widget.plot(t, lower_bb.values, pen=pg.mkPen('#42a5f5', style=Qt.DashLine, width=1.0))
            
            curve_upper = pg.PlotDataItem(t, upper_bb.values)
            curve_lower = pg.PlotDataItem(t, lower_bb.values)
            fill = pg.FillBetweenItem(curve_upper, curve_lower, brush=QColor(66, 165, 245, 15))
            self.plot_widget.addItem(fill)

        # 4. Volume Chart
        vols = df['volume'].values
        bullish = (df['close'] >= df['open']).values
        green_brush = QColor('#26a69a')
        red_brush = QColor('#ef5350')
        
        t_green = t[bullish]
        vol_green = vols[bullish]
        if len(t_green) > 0:
            bg_green = pg.BarGraphItem(x=t_green, height=vol_green, width=0.7, brush=green_brush, pen=pg.mkPen(color='#26a69a', width=0))
            self.volume_widget.addItem(bg_green)
            
        t_red = t[~bullish]
        vol_red = vols[~bullish]
        if len(t_red) > 0:
            bg_red = pg.BarGraphItem(x=t_red, height=vol_red, width=0.7, brush=red_brush, pen=pg.mkPen(color='#ef5350', width=0))
            self.volume_widget.addItem(bg_red)
            
        # 5. RSI Chart
        self.rsi_widget.plot(t, df['rsi'].values, pen=pg.mkPen('c', width=1.5))
        self.rsi_widget.addLine(y=30, pen=pg.mkPen('g', style=Qt.DashLine))
        self.rsi_widget.addLine(y=70, pen=pg.mkPen('r', style=Qt.DashLine))
        
        # 6. Signals
        for trade in trades:
            entry_matches = np.where(df['time'] == trade['entry_time'])[0]
            exit_matches = np.where(df['time'] == trade['exit_time'])[0]
            
            if len(entry_matches) == 0 or len(exit_matches) == 0:
                continue
                
            entry_idx = int(entry_matches[0])
            exit_idx = int(exit_matches[0])
            
            arrow_buy = pg.ArrowItem(pos=(entry_idx, df.iloc[entry_idx]['low']), angle=90, brush='g')
            self.plot_widget.addItem(arrow_buy)
            
            arrow_sell = pg.ArrowItem(pos=(exit_idx, df.iloc[exit_idx]['high']), angle=-90, brush='r')
            self.plot_widget.addItem(arrow_sell)

        # 7. Interactive Crosshair Lines
        self.vLine = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('#757575', width=1.0, style=Qt.DashLine))
        self.hLine = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen('#757575', width=1.0, style=Qt.DashLine))
        self.plot_widget.addItem(self.vLine, ignoreBounds=True)
        self.plot_widget.addItem(self.hLine, ignoreBounds=True)
        
        self.vLine_vol = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('#757575', width=1.0, style=Qt.DashLine))
        self.vLine_rsi = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('#757575', width=1.0, style=Qt.DashLine))
        self.volume_widget.addItem(self.vLine_vol, ignoreBounds=True)
        self.rsi_widget.addItem(self.vLine_rsi, ignoreBounds=True)

        # 8. Mouse movement callback
        def mouseMoved(evt):
            pos = evt[0]
            if self.plot_widget.sceneBoundingRect().contains(pos):
                mousePoint = self.plot_widget.plotItem.vb.mapSceneToView(pos)
                index = int(mousePoint.x())
                if index >= 0 and index < len(self.df_chart_data):
                    row = self.df_chart_data.iloc[index]
                    date_str = str(row['time'].date()) if hasattr(row['time'], 'date') else str(row['time'])[:10]
                    
                    info_text = (
                        f"📅 {date_str} | "
                        f"O: <span style='color:#fff;'>{row['open']:,.1f}</span> | "
                        f"H: <span style='color:#ef5350;'>{row['high']:,.1f}</span> | "
                        f"L: <span style='color:#26a69a;'>{row['low']:,.1f}</span> | "
                        f"C: <span style='color:#90caf9;'>{row['close']:,.1f}</span> | "
                        f"Vol: <span style='color:#ffb74d;'>{row['volume']:,}</span>"
                    )
                    if 'rsi' in row and pd.notna(row['rsi']):
                        info_text += f" | RSI: <span style='color:#4db6ac;'>{row['rsi']:.1f}</span>"
                    self.label_info.setText(info_text)
                    
                    # Update line positions
                    self.vLine.setPos(mousePoint.x())
                    self.hLine.setPos(mousePoint.y())
                    self.vLine_vol.setPos(mousePoint.x())
                    self.vLine_rsi.setPos(mousePoint.x())

        self.proxy = pg.SignalProxy(self.plot_widget.scene().sigMouseMoved, rateLimit=60, slot=mouseMoved)
