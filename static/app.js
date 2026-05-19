// --- VNStock Premium SPA Client Controller ---

document.addEventListener("DOMContentLoaded", () => {
    // Application State
    const state = {
        tickers: [],
        scanInterval: null,
        antiInterval: null,
        watchInterval: null,
        charts: {
            equity: null,
            liquidity: null,
            modal: null,
            marketCap: null
        },
        currentHeatmapData: null,
        currentMarketData: null,
        currentScannerResults: [],
        sectorFlowData: null,
        sectorFlowCache: {},
        sectorFlowHistory: null,
        priceReturnHistory: null,
        notableStocks: null,
        moneyFlowPeriod: "1d"
    };

    // DOM Selectors
    const navItems = document.querySelectorAll(".nav-item");
    const tabPanels = document.querySelectorAll(".tab-panel");
    const pageTitle = document.getElementById("page-title");
    const pageSubtitle = document.getElementById("page-subtitle");
    const appSource = document.getElementById("app-source");

    // Top Header details mapping
    const headerDetails = {
        "tab-heatmap": { title: "Sơ Đồ Hiệu Suất Ngành", subtitle: "Bản đồ nhiệt sức mạnh dòng tiền và độ rộng thị trường" },
        "tab-sector-gtgd": { title: "GTGD Ngành", subtitle: "Tổng tiền giao dịch của toàn bộ cổ phiếu trong từng ngành, kèm percentile 3 năm" },
        "tab-sector-cap": { title: "Vốn hóa Ngành", subtitle: "Tổng vốn hóa theo giá đóng cửa của toàn bộ cổ phiếu trong từng ngành" },
        "tab-sector-ratio": { title: "GTGD / Vốn hóa Ngành", subtitle: "Đo độ sôi động của dòng tiền so với quy mô vốn hóa ngành" },
        "tab-sector-share": { title: "Tỷ trọng Ngành", subtitle: "Tỷ lệ GTGD của từng ngành so với tổng GTGD toàn thị trường trong ngày" },
        "tab-sector-ma": { title: "So với MA20 / MA60", subtitle: "So sánh trạng thái hiện tại của dòng tiền ngành với trung bình 20 và 60 phiên" },
        "tab-money-flow": { title: "Dịch chuyển Dòng tiền", subtitle: "Nhìn nhanh dòng tiền đang tăng tỷ trọng ở đâu và rút bớt khỏi đâu" },
        "tab-return-matrix": { title: "Return % 3 năm", subtitle: "Matrix tỷ suất sinh lời theo ngày của toàn bộ mã trong database" },
        "tab-close-matrix": { title: "Giá Close 3 năm", subtitle: "Matrix giá đóng cửa của toàn bộ mã trong database" },
        "tab-ohlc": { title: "Biểu đồ nến OHLC", subtitle: "Chọn bất kỳ mã nào để xem nến 3 năm gần nhất từ database" },
        "tab-notable-stocks": { title: "Cổ phiếu nổi bật hôm nay", subtitle: "Kết hợp dòng tiền, return, Vol/MA20 và tín hiệu kỹ thuật để lọc mã đáng chú ý" },
        "tab-export-all": { title: "Xuất Toàn Bộ", subtitle: "Gộp tất cả sheet Excel riêng lẻ của các tab vào một workbook" },
        "tab-market": { title: "Phân Tích Sức Mạnh Thị Trường", subtitle: "So sánh hiệu suất các ngành so với chỉ số VNINDEX" },
        "tab-scanner": { title: "Bộ Quét Kỹ Thuật VN302", subtitle: "Theo dõi thời gian thực tín hiệu xu hướng MA, RSI và MACD" },
        "tab-antigravity": { title: "Hệ Thống Antigravity Volatility", subtitle: "Phát hiện điểm xoay chiều cực đại khi khối lượng cạn kiệt" },
        "tab-watchlist": { title: "Danh Sách Cổ Phiếu Tích Lũy", subtitle: "Theo dõi các mã nén chặt Darvas biên độ hẹp với vol cạn" },
        "tab-backtester": { title: "RSI Backtester & Optimizer", subtitle: "Thử nghiệm chiến lược giao dịch định lượng trên dữ liệu lịch sử" },
        "tab-liquidity": { title: "Phân Tích Thanh Khoản & Dòng Tiền", subtitle: "Truy vấn giá trị giao dịch khớp lệnh thực tế từ sở giao dịch HOSE" },
        "tab-market-cap": { title: "Phân Tích Vốn Hóa Doanh Nghiệp", subtitle: "Quét và phân loại vốn hóa Mega, Large, Mid, Small Cap cho 302 doanh nghiệp VN302" },
        "tab-vol-cap": { title: "Tỷ Lệ GTGD / Vốn Hóa (Vol/Cap)", subtitle: "Theo dõi tỷ lệ thanh khoản khớp lệnh trên tổng quy mô vốn hóa của 302 doanh nghiệp VN302" }
    };

    // --- 1. SPA ROUTING & NAVIGATION ---
    navItems.forEach(item => {
        item.addEventListener("click", (e) => {
            e.preventDefault();
            const tabId = item.getAttribute("data-tab");
            
            // Toggle active classes on sidebar
            navItems.forEach(n => n.classList.remove("active"));
            item.classList.add("active");
            
            // Toggle active classes on content panels
            tabPanels.forEach(panel => {
                panel.classList.remove("active");
                if (panel.id === tabId) {
                    panel.classList.add("active");
                }
            });

            // Update top header description
            if (headerDetails[tabId]) {
                pageTitle.textContent = headerDetails[tabId].title;
                pageSubtitle.textContent = headerDetails[tabId].subtitle;
            }

            // Trigger tab-specific loads
            onTabActivated(tabId);
        });
    });

    function onTabActivated(tabId) {
        if (tabId === "tab-backtester") {
            loadTickersDropdown();
        } else if (tabId === "tab-heatmap") {
            fetchHeatmapData();
        } else if (tabId.startsWith("tab-sector-")) {
            const panel = document.getElementById(tabId);
            loadSectorFlowData(panel ? panel.dataset.flowView : "gtgd");
        } else if (tabId === "tab-money-flow") {
            loadSectorFlowData("dashboard");
        } else if (tabId === "tab-return-matrix") {
            loadPriceMatrix("return");
        } else if (tabId === "tab-close-matrix") {
            loadPriceMatrix("close");
        } else if (tabId === "tab-ohlc") {
            initializeOhlcTab();
        } else if (tabId === "tab-notable-stocks") {
            loadNotableStocks();
        } else if (tabId === "tab-market") {
            fetchMarketData();
        } else if (tabId === "tab-liquidity") {
            // Auto trigger liquidity load for default date if empty
            if (document.getElementById("liq-total-value").textContent === "0 VND") {
                loadLiquidityData();
            }
        } else if (tabId === "tab-market-cap") {
            // Auto trigger market cap load for default date if empty
            if (document.getElementById("cap-total-value").textContent === "0 tỷ VND") {
                loadMarketCapData();
            }
        } else if (tabId === "tab-vol-cap") {
            // Auto trigger vol cap load for default date if empty
            if (document.getElementById("vol-cap-total-value").textContent === "0 tỷ VND") {
                loadVolCapData();
            }
        }
    }

    // --- 2. GLOBAL TICKERS PRE-LOADING ---
    async function loadTickersDropdown() {
        if (state.tickers.length > 0) return; // Already loaded
        
        try {
            const res = await fetch("/api/tickers");
            const data = await res.json();
            state.tickers = data.tickers || [];
            
            const btSelect = document.getElementById("bt-ticker");
            btSelect.innerHTML = "";
            state.tickers.forEach(t => {
                const opt = document.createElement("option");
                opt.value = t;
                opt.textContent = t;
                btSelect.appendChild(opt);
            });
            
            // Default select VCI or HPG if exists
            if (state.tickers.includes("VCI")) {
                btSelect.value = "VCI";
            } else if (state.tickers.includes("HPG")) {
                btSelect.value = "HPG";
            }
        } catch (err) {
            console.error("Error fetching tickers list:", err);
        }
    }

    // Load available sectors for filters
    async function loadSectorFilters(sectors) {
        const secFilter = document.getElementById("filter-sec");
        // Keep first option "Tất cả ngành"
        secFilter.innerHTML = '<option value="All">Tất cả ngành</option>';
        sectors.forEach(s => {
            const opt = document.createElement("option");
            opt.value = s;
            opt.textContent = s;
            secFilter.appendChild(opt);
        });
    }

    // Change data source handler
    appSource.addEventListener("change", async () => {
        try {
            await fetch(`/api/source?source=${appSource.value}`, { method: "POST" });
            // Invalidate cached tickers
            state.tickers = [];
            onTabActivated(document.querySelector(".nav-item.active").getAttribute("data-tab"));
            showNotification(`Đã chuyển đổi nguồn dữ liệu sang ${appSource.value}!`, "cyan");
        } catch (err) {
            console.error("Error setting source:", err);
        }
    });

    // --- 3. SECTOR HEATMAP LOGIC ---
    async function fetchHeatmapData() {
        const container = document.getElementById("heatmap-cards-container");
        try {
            const res = await fetch("/api/heatmap");
            const data = await res.json();
            state.currentHeatmapData = data.sectors || {};
            
            container.innerHTML = "";
            const sectorKeys = Object.keys(state.currentHeatmapData);
            
            // Load sectors to filter combobox as well
            loadSectorFilters(sectorKeys);

            if (sectorKeys.length === 0) {
                container.innerHTML = `
                    <div class="loading-state">
                        <i class="fa-solid fa-triangle-exclamation text-red" style="font-size: 32px;"></i>
                        <p>Chưa có dữ liệu. Vui lòng chạy Quét bộ lọc ở tab "Bộ Quét VN302" trước.</p>
                    </div>`;
                return;
            }

            sectorKeys.forEach(secName => {
                const sec = state.currentHeatmapData[secName];
                const card = document.createElement("div");
                card.className = "heatmap-card glass";
                
                const returnVal = sec.avg_return || 0;
                const isPositive = returnVal >= 0;
                const retColor = isPositive ? "text-green" : "text-red";
                const borderGlow = isPositive ? "rgba(38, 166, 154, 0.2)" : "rgba(239, 83, 80, 0.2)";
                
                card.style.borderColor = isPositive ? "rgba(38, 166, 154, 0.15)" : "rgba(239, 83, 80, 0.15)";
                card.addEventListener("mouseenter", () => {
                    card.style.borderColor = isPositive ? "var(--accent-emerald)" : "var(--accent-red)";
                    card.style.boxShadow = `0 0 15px ${borderGlow}`;
                });
                card.addEventListener("mouseleave", () => {
                    card.style.borderColor = isPositive ? "rgba(38, 166, 154, 0.15)" : "rgba(239, 83, 80, 0.15)";
                    card.style.boxShadow = "none";
                });

                // Clicking sector card routes to market tab to show details
                card.addEventListener("click", () => {
                    const marketTabItem = document.querySelector('[data-tab="tab-market"]');
                    marketTabItem.click();
                    // Delay slightly to allow tab render, then select sector
                    setTimeout(() => {
                        selectMarketIndustry(secName);
                    }, 100);
                });

                card.innerHTML = `
                    <span class="heatmap-card-title">${secName}</span>
                    <span class="heatmap-card-ret ${retColor}">${isPositive ? "+" : ""}${returnVal.toFixed(2)}%</span>
                    <span class="heatmap-card-breadth">Vượt MA50: <strong class="text-cyan">${(sec.above_ma50_pct * 100).toFixed(0)}%</strong> (${sec.above_ma50_count}/${sec.total_count} CP)</span>
                `;
                container.appendChild(card);
            });
        } catch (err) {
            console.error("Error fetching heatmap:", err);
            container.innerHTML = `<div class="loading-state text-red"><p>Lỗi tải bản đồ nhiệt: ${err.message}</p></div>`;
        }
    }

    const sectorFlowConfig = {
        gtgd: {
            sortKey: "GTGDBillion",
            headers: ["Hạng", "Ngành", "GTGD ngành", "Tỷ trọng thị trường", "Percentile 3 năm", "Số mã"],
            row: item => [
                item.Rank,
                item.Industry,
                `${formatNumber(item.GTGDBillion, 1)} tỷ`,
                `${formatNumber(item.MarketSharePct, 2)}%`,
                `${formatNumber(item.GTGDPercentile, 1)}%`,
                item.TickerCount
            ]
        },
        cap: {
            sortKey: "CapBillion",
            headers: ["Hạng", "Ngành", "Vốn hóa ngành", "GTGD/Vốn hóa", "Percentile 3 năm", "Số mã"],
            row: item => [
                item.Rank,
                item.Industry,
                `${formatNumber(item.CapBillion, 0)} tỷ`,
                `${formatNumber(item.GTGDCapPct, 2)}%`,
                `${formatNumber(item.CapPercentile, 1)}%`,
                item.TickerCount
            ]
        },
        ratio: {
            sortKey: "GTGDCapPct",
            headers: ["Hạng", "Ngành", "GTGD/Vốn hóa", "GTGD ngành", "Percentile 3 năm", "So với MA60"],
            row: item => [
                item.Rank,
                item.Industry,
                `${formatNumber(item.GTGDCapPct, 2)}%`,
                `${formatNumber(item.GTGDBillion, 1)} tỷ`,
                `${formatNumber(item.GTGDCapPercentile, 1)}%`,
                `${formatSigned(item.RatioVsMA60Pct, 1)}%`
            ]
        },
        share: {
            sortKey: "MarketSharePct",
            headers: ["Hạng", "Ngành", "Tỷ trọng GTGD", "GTGD ngành", "Percentile 3 năm", "Lệch MA60"],
            row: item => [
                item.Rank,
                item.Industry,
                `${formatNumber(item.MarketSharePct, 2)}%`,
                `${formatNumber(item.GTGDBillion, 1)} tỷ`,
                `${formatNumber(item.MarketSharePercentile, 1)}%`,
                `${formatSigned(item.ShareVsMA60Pct, 2)} điểm %`
            ]
        },
        ma: {
            sortKey: "ShareVsMA60Pct",
            headers: ["Hạng", "Ngành", "GTGD/VH hiện tại", "MA20", "MA60", "Lệch MA20", "Lệch MA60"],
            row: item => [
                item.Rank,
                item.Industry,
                `${formatNumber(item.GTGDCapPct, 2)}%`,
                `${formatNumber(item.RatioMA20, 2)}%`,
                `${formatNumber(item.RatioMA60, 2)}%`,
                `${formatSigned(item.RatioVsMA20Pct, 1)}%`,
                `${formatSigned(item.RatioVsMA60Pct, 1)}%`
            ]
        }
    };

    function formatNumber(value, digits = 1) {
        if (value === null || value === undefined || Number.isNaN(Number(value))) return "N/A";
        return Number(value).toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits });
    }

    function formatSigned(value, digits = 1) {
        if (value === null || value === undefined || Number.isNaN(Number(value))) return "N/A";
        const num = Number(value);
        return `${num >= 0 ? "+" : ""}${formatNumber(num, digits)}`;
    }

    function getMoneyFlowPeriod() {
        const active = document.querySelector(".flow-period-btn.active");
        return active ? active.dataset.period : state.moneyFlowPeriod;
    }

    function getFlowChange(item) {
        return item.PeriodShareChangePct ?? item.ShareVsMA60Pct ?? 0;
    }

    function getFlowPeriodLabel() {
        return state.sectorFlowData?.period_label || getMoneyFlowPeriod();
    }

    async function loadSectorFlowHistory(force = false) {
        if (state.sectorFlowHistory && !force) return state.sectorFlowHistory;
        const res = await fetch("/api/sector-flow/history?years=3");
        const data = await res.json();
        if (!res.ok || data.error || data.detail) throw new Error(data.error || data.detail || `HTTP ${res.status}`);
        state.sectorFlowHistory = data;
        return data;
    }

    async function loadSectorFlowData(targetView = "gtgd", force = false, period = null) {
        if (["gtgd", "cap", "ratio", "share"].includes(targetView)) {
            const activePanel = document.querySelector(`.sector-flow-panel[data-flow-view="${targetView}"]`);
            const table = activePanel ? activePanel.querySelector(".sector-flow-table") : null;
            if (table) table.innerHTML = `<tbody><tr><td class="text-center text-muted"><i class="fa-solid fa-circle-notch fa-spin"></i> Đang dựng matrix 3 năm từ database...</td></tr></tbody>`;
            try {
                await loadSectorFlowHistory(force);
                renderSectorMatrixTable(targetView);
            } catch (err) {
                showNotification(`Lỗi matrix ngành: ${err.message}`, "red");
            }
            return;
        }

        const selectedPeriod = period || (targetView === "dashboard" ? getMoneyFlowPeriod() : "60d");
        const cacheKey = `3:${selectedPeriod}`;
        const activePanel = targetView === "dashboard"
            ? document.getElementById("tab-money-flow")
            : document.querySelector(`.sector-flow-panel[data-flow-view="${targetView}"]`);

        if (state.sectorFlowCache[cacheKey] && !force) {
            state.sectorFlowData = state.sectorFlowCache[cacheKey];
            if (targetView === "dashboard") {
                renderMoneyFlowDashboard();
            } else {
                renderSectorFlowTable(targetView);
            }
            return;
        }
        if (activePanel) {
            const table = activePanel.querySelector(".sector-flow-table");
            if (table) table.innerHTML = `<tbody><tr><td class="text-center text-muted"><i class="fa-solid fa-circle-notch fa-spin"></i> Đang đọc dữ liệu 3 năm từ database...</td></tr></tbody>`;
        }

        try {
            const res = await fetch(`/api/sector-flow/results?years=3&period=${encodeURIComponent(selectedPeriod)}`);
            const data = await res.json();
            if (!res.ok || data.error || data.detail) throw new Error(data.error || data.detail || `HTTP ${res.status}`);
            state.sectorFlowData = data;
            state.sectorFlowCache[cacheKey] = data;
            document.querySelectorAll(".btn-load-sector-flow").forEach(btn => {
                btn.innerHTML = '<i class="fa-solid fa-database"></i> Nạp lại dữ liệu 3 năm';
            });
            if (targetView === "dashboard") {
                renderMoneyFlowDashboard();
            } else {
                renderSectorFlowTable(targetView);
            }
        } catch (err) {
            showNotification(`Lỗi dữ liệu ngành: ${err.message}`, "red");
        }
    }

    function renderSectorFlowTable(view) {
        if (!state.sectorFlowData) return;
        const panel = document.querySelector(`.sector-flow-panel[data-flow-view="${view}"]`);
        const table = panel ? panel.querySelector(".sector-flow-table") : null;
        const meta = panel ? panel.querySelector(".sector-flow-meta") : null;
        const config = sectorFlowConfig[view] || sectorFlowConfig.gtgd;
        if (!table) return;

        const rows = [...(state.sectorFlowData.rows || [])].sort((a, b) => {
            const av = a[config.sortKey] ?? -Infinity;
            const bv = b[config.sortKey] ?? -Infinity;
            return bv - av;
        });
        rows.forEach((item, index) => item.DisplayRank = index + 1);

        table.innerHTML = `
            <thead><tr>${config.headers.map(h => `<th>${h}</th>`).join("")}</tr></thead>
            <tbody>
                ${rows.map(item => {
                    const cells = config.row({ ...item, Rank: item.DisplayRank });
                    return `<tr>${cells.map((cell, idx) => `<td class="${idx === 1 ? "font-weight-bold text-white" : "text-right"}">${cell}</td>`).join("")}</tr>`;
                }).join("")}
            </tbody>`;
        if (meta) {
            meta.textContent = `Nguồn: database | Kỳ dữ liệu: ${state.sectorFlowData.start_date} đến ${state.sectorFlowData.end_date} | ${state.sectorFlowData.history_points} phiên`;
        }
    }

    const sectorMatrixConfig = {
        gtgd: {
            key: "GTGDBillion",
            title: "Giá trị giao dịch (tỷ đồng)",
            summary: ["Average 20 phiên", "Average 60 phiên", "Average 250 phiên"],
            digits: 0,
            percent: false,
            heat: false
        },
        cap: {
            key: "CapBillion",
            title: "Vốn hóa ngành (tỷ đồng)",
            summary: [],
            digits: 0,
            percent: false,
            heat: false
        },
        ratio: {
            key: "GTGDCapPct",
            title: "GTGD / Vốn hóa ngành",
            summary: [],
            digits: 2,
            percent: true,
            heat: true
        },
        share: {
            key: "MarketSharePct",
            title: "Giá trị giao dịch theo ngày (khớp lệnh)",
            summary: ["Min 52 tuần", "Max 52 tuần", "Average 1 tuần", "Average 52 tuần", "Average 60 phiên", "Average 20 phiên", "5%", "50%", "95%"],
            digits: 2,
            percent: true,
            heat: true
        }
    };

    function normalizeStatLabel(label) {
        return label
            .replace("phiên", "phiÃªn")
            .replace("tuần", "tuáº§n");
    }

    function formatMatrixValue(value, config) {
        if (value === null || value === undefined || Number.isNaN(Number(value))) return "";
        return config.percent ? `${formatNumber(value, config.digits)}%` : formatNumber(value, config.digits);
    }

    function heatClass(value, values) {
        if (value === null || value === undefined || Number.isNaN(Number(value)) || values.length === 0) return "";
        const sorted = [...values].sort((a, b) => a - b);
        const low = sorted[Math.floor(sorted.length * 0.25)] ?? sorted[0];
        const high = sorted[Math.floor(sorted.length * 0.75)] ?? sorted[sorted.length - 1];
        if (Number(value) >= high) return "heat-high";
        if (Number(value) <= low) return "heat-low";
        return "";
    }

    function renderSectorMatrixTable(view) {
        const history = state.sectorFlowHistory;
        const config = sectorMatrixConfig[view];
        if (!history || !config) return;

        const panel = document.querySelector(`.sector-flow-panel[data-flow-view="${view}"]`);
        const table = panel ? panel.querySelector(".sector-flow-table") : null;
        const meta = panel ? panel.querySelector(".sector-flow-meta") : null;
        if (!table) return;

        const industries = history.industries || [];
        const metricValuesByIndustry = {};
        industries.forEach(industry => {
            metricValuesByIndustry[industry] = (history.rows || [])
                .map(day => day.values?.[industry]?.[config.key])
                .filter(value => value !== null && value !== undefined && !Number.isNaN(Number(value)))
                .map(Number);
        });

        const summaryRows = config.summary.map(label => {
            const statKey = normalizeStatLabel(label);
            return `
                <tr class="sector-matrix-summary-row">
                    <th>${label}</th>
                    ${industries.map(industry => `<td>${formatMatrixValue(history.stats?.[view]?.[statKey]?.[industry], config)}</td>`).join("")}
                </tr>`;
        }).join("");

        const spacer = config.summary.length > 0
            ? `<tr class="sector-matrix-spacer"><td colspan="${industries.length + 1}"></td></tr>`
            : "";

        table.classList.add("sector-matrix-table");
        table.innerHTML = `
            <tbody>
                ${summaryRows}
                ${spacer}
                <tr class="sector-matrix-title"><th colspan="${industries.length + 1}">${config.title}</th></tr>
                <tr class="sector-matrix-header">
                    <th>Dates</th>
                    ${industries.map(industry => `<th>${industry}</th>`).join("")}
                </tr>
                ${(history.rows || []).map(day => `
                    <tr>
                        <th>${day.Date}</th>
                        ${industries.map(industry => {
                            const value = day.values?.[industry]?.[config.key];
                            const cls = config.heat ? heatClass(value, metricValuesByIndustry[industry]) : "";
                            return `<td class="${cls}">${formatMatrixValue(value, config)}</td>`;
                        }).join("")}
                    </tr>
                `).join("")}
            </tbody>`;

        if (meta) {
            meta.textContent = `Nguồn: database | ${history.start_date} đến ${history.end_date} | ${history.rows.length} phiên | ${industries.length} ngành`;
        }
    }

    function renderFlowList(containerId, rows, positive = true) {
        const container = document.getElementById(containerId);
        if (!container) return;
        const maxAbs = Math.max(...rows.map(item => Math.abs(item.ShareVsMA60Pct || 0)), 1);
        container.innerHTML = rows.map(item => {
            const width = Math.max(6, Math.abs(item.ShareVsMA60Pct || 0) / maxAbs * 100);
            return `
                <div class="flow-row ${positive ? "flow-in" : "flow-out"}">
                    <div class="flow-row-top">
                        <strong>${item.Industry}</strong>
                        <span>${formatSigned(item.ShareVsMA60Pct, 2)} điểm %</span>
                    </div>
                    <div class="flow-bar-track">
                        <div class="flow-bar" style="width: ${width}%"></div>
                    </div>
                    <div class="flow-row-sub">Tỷ trọng: ${formatNumber(item.MarketSharePct, 2)}% | Percentile: ${formatNumber(item.MarketSharePercentile, 1)}%</div>
                </div>`;
        }).join("");
    }

    function renderHighlightTickers(item) {
        const tickers = item.HighlightTickers || [];
        if (tickers.length === 0) return "";
        return `
            <div class="flow-tickers">
                ${tickers.map(ticker => `
                    <span class="flow-ticker-chip">
                        <strong>${ticker.Ticker}</strong>
                        <span>${formatSigned(ticker.ChangeBillion, 1)} tỷ</span>
                    </span>
                `).join("")}
            </div>`;
    }

    function renderFlowListByPeriod(containerId, rows, positive = true) {
        const container = document.getElementById(containerId);
        if (!container) return;
        const maxAbs = Math.max(...rows.map(item => Math.abs(getFlowChange(item))), 1);
        container.innerHTML = rows.map(item => {
            const change = getFlowChange(item);
            const width = Math.max(6, Math.abs(change) / maxAbs * 100);
            return `
                <div class="flow-row ${positive ? "flow-in" : "flow-out"}">
                    <div class="flow-row-top">
                        <strong>${item.Industry}</strong>
                        <span>${formatSigned(change, 2)} điểm %</span>
                    </div>
                    <div class="flow-bar-track">
                        <div class="flow-bar" style="width: ${width}%"></div>
                    </div>
                    <div class="flow-row-sub">
                        Tỷ trọng: ${formatNumber(item.MarketSharePct, 2)}% | GTGD: ${formatNumber(item.GTGDBillion, 1)} tỷ | GTGD đổi: ${formatSigned(item.PeriodGTGDChangeBillion, 1)} tỷ
                    </div>
                    ${renderHighlightTickers(item)}
                </div>`;
        }).join("");
    }

    function renderMoneyFlowDashboard() {
        if (!state.sectorFlowData) return;
        const rows = state.sectorFlowData.rows || [];
        const inflows = [...rows].filter(item => getFlowChange(item) > 0).sort((a, b) => getFlowChange(b) - getFlowChange(a)).slice(0, 6);
        const outflows = [...rows].filter(item => getFlowChange(item) < 0).sort((a, b) => getFlowChange(a) - getFlowChange(b)).slice(0, 6);
        renderFlowListByPeriod("flow-in-list", inflows, true);
        renderFlowListByPeriod("flow-out-list", outflows, false);

        const arrowBoard = document.getElementById("flow-arrow-board");
        if (arrowBoard) {
            const pairs = inflows.slice(0, 4).map((item, idx) => ({ to: item, from: outflows[idx] })).filter(pair => pair.from);
            arrowBoard.innerHTML = pairs.map(pair => `
                <div class="flow-transfer">
                    <span class="flow-chip flow-out-chip">${pair.from.Industry}</span>
                    <span class="flow-arrow"><i class="fa-solid fa-arrow-right-long"></i></span>
                    <span class="flow-chip flow-in-chip">${pair.to.Industry}</span>
                </div>`).join("");
        }

        if (arrowBoard) {
            const pairs = inflows.slice(0, 4).map((item, idx) => ({ to: item, from: outflows[idx] })).filter(pair => pair.from);
            arrowBoard.innerHTML = pairs.map(pair => `
                <div class="flow-transfer flow-transfer-rich">
                    <span class="flow-chip flow-out-chip">${pair.from.Industry}<small>${formatSigned(getFlowChange(pair.from), 2)}đ</small></span>
                    <span class="flow-arrow"><i class="fa-solid fa-arrow-right-long"></i></span>
                    <span class="flow-chip flow-in-chip">${pair.to.Industry}<small>${formatSigned(getFlowChange(pair.to), 2)}đ</small></span>
                    <span class="flow-transfer-note">Mã nổi bật: ${(pair.to.HighlightTickers || []).slice(0, 2).map(t => t.Ticker).join(", ") || "N/A"}</span>
                </div>`).join("");
        }

        const summary = document.getElementById("money-flow-summary");
        if (summary) {
            const leadIn = inflows[0];
            const leadOut = outflows[0];
            summary.innerHTML = `
                <div><span>Kỳ so sánh</span><strong>${getFlowPeriodLabel()}</strong></div>
                <div><span>Vào mạnh nhất</span><strong>${leadIn ? `${leadIn.Industry} ${formatSigned(getFlowChange(leadIn), 2)}đ` : "N/A"}</strong></div>
                <div><span>Rút mạnh nhất</span><strong>${leadOut ? `${leadOut.Industry} ${formatSigned(getFlowChange(leadOut), 2)}đ` : "N/A"}</strong></div>
                <div><span>Ngày so</span><strong>${state.sectorFlowData.compare_date} → ${state.sectorFlowData.end_date}</strong></div>`;
        }

        const meta = document.getElementById("money-flow-meta");
        if (meta) {
            meta.textContent = `Đọc từ database, so tỷ trọng GTGD kỳ ${getFlowPeriodLabel()} từ ${state.sectorFlowData.compare_date} đến ${state.sectorFlowData.end_date}.`;
        }

        renderDailyMoneyLeaders();
    }

    function renderDailyMoneyLeaders() {
        const tableBody = document.querySelector("#flow-daily-leaders-table tbody");
        if (!tableBody || !state.sectorFlowData) return;
        const rows = state.sectorFlowData.daily_leaders || [];
        tableBody.innerHTML = rows.slice(0, 30).map(day => {
            const topIn = day.TopInTicker || {};
            const topOut = day.TopOutTicker || {};
            return `
                <tr>
                    <td><strong>${day.Date}</strong></td>
                    <td class="text-green font-weight-bold">${topIn.Ticker || "N/A"}</td>
                    <td>${topIn.Industry || "N/A"}</td>
                    <td class="text-green">${formatSigned(topIn.ChangeBillion, 1)} tỷ</td>
                    <td class="text-red font-weight-bold">${topOut.Ticker || "N/A"}</td>
                    <td>${topOut.Industry || "N/A"}</td>
                    <td class="text-red">${formatSigned(topOut.ChangeBillion, 1)} tỷ</td>
                </tr>`;
        }).join("");
    }

    async function loadAllSectorFlowTabs() {
        const btn = document.getElementById("btn-load-sector-flow-all");
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Äang náº¡p database...';
        }

        try {
            state.sectorFlowData = null;
            await loadSectorFlowData("dashboard");
            if (!state.sectorFlowData) return;
            ["gtgd", "cap", "ratio", "share", "ma"].forEach(view => renderSectorFlowTable(view));
            renderMoneyFlowDashboard();
            showNotification("ÄÃ£ náº¡p xong dá»¯ liá»‡u ngÃ nh 3 nÄƒm cho táº¥t cáº£ tab.", "emerald");
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = '<i class="fa-solid fa-database"></i> Náº¡p láº¡i táº¥t cáº£ tab ngÃ nh 3 nÄƒm';
            }
        }
    }

    function setSectorFlowAllButtonLabel(mode = "idle") {
        const btn = document.getElementById("btn-load-sector-flow-all");
        if (!btn) return;
        const icon = mode === "loading"
            ? '<i class="fa-solid fa-circle-notch fa-spin"></i>'
            : '<i class="fa-solid fa-database"></i>';
        const text = mode === "loading"
            ? "\u0110ang n\u1ea1p database..."
            : "N\u1ea1p t\u1ea5t c\u1ea3 tab ng\u00e0nh 3 n\u0103m";
        btn.innerHTML = `${icon} ${text}`;
    }

    function normalizeSectorFlowAllHeader() {
        const btn = document.getElementById("btn-load-sector-flow-all");
        const title = btn ? btn.closest(".card-header")?.querySelector("h2") : null;
        if (title) title.textContent = "B\u1ea3n \u0110\u1ed3 Nhi\u1ec7t";
        setSectorFlowAllButtonLabel("idle");
    }

    async function loadAllSectorFlowTabsFromDatabase() {
        const btn = document.getElementById("btn-load-sector-flow-all");
        if (btn) {
            btn.disabled = true;
            setSectorFlowAllButtonLabel("loading");
        }

        try {
            state.sectorFlowData = null;
            await loadSectorFlowHistory(true);
            ["gtgd", "cap", "ratio", "share", "ma"].forEach(view => renderSectorFlowTable(view));
            ["gtgd", "cap", "ratio", "share"].forEach(view => renderSectorMatrixTable(view));
            await loadSectorFlowData("dashboard", true, getMoneyFlowPeriod());
            renderMoneyFlowDashboard();
            showNotification("\u0110\u00e3 n\u1ea1p xong d\u1eef li\u1ec7u ng\u00e0nh 3 n\u0103m cho t\u1ea5t c\u1ea3 tab.", "emerald");
        } finally {
            if (btn) {
                btn.disabled = false;
                setSectorFlowAllButtonLabel("idle");
            }
        }
    }

    normalizeSectorFlowAllHeader();

    document.querySelectorAll('.sector-flow-panel[data-flow-view="gtgd"], .sector-flow-panel[data-flow-view="cap"], .sector-flow-panel[data-flow-view="ratio"], .sector-flow-panel[data-flow-view="share"]').forEach(panel => {
        const header = panel.querySelector(".card-header");
        if (!header || header.querySelector(".btn-export-sector-matrix")) return;
        const btn = document.createElement("button");
        btn.className = "btn btn-emerald btn-export-sector-matrix";
        btn.innerHTML = '<i class="fa-solid fa-file-excel"></i> Xuất Excel matrix';
        btn.addEventListener("click", () => {
            window.location.href = "/api/export/sector-flow-matrix?years=3";
            showNotification("Đang xuất Excel 4 sheet ngành dạng matrix...", "emerald");
        });
        header.appendChild(btn);
    });

    document.querySelectorAll(".btn-load-sector-flow").forEach(btn => {
        btn.addEventListener("click", () => {
            const panel = btn.closest(".sector-flow-panel");
            loadSectorFlowData(panel ? panel.dataset.flowView : "gtgd", true);
        });
    });

    const btnLoadMoneyFlow = document.getElementById("btn-load-money-flow");
    if (btnLoadMoneyFlow) {
        btnLoadMoneyFlow.addEventListener("click", () => loadSectorFlowData("dashboard", true, getMoneyFlowPeriod()));
    }

    document.querySelectorAll(".flow-period-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".flow-period-btn").forEach(item => item.classList.remove("active"));
            btn.classList.add("active");
            state.moneyFlowPeriod = btn.dataset.period || "1d";
            loadSectorFlowData("dashboard", true, state.moneyFlowPeriod);
        });
    });

    const btnLoadSectorFlowAll = document.getElementById("btn-load-sector-flow-all");
    if (btnLoadSectorFlowAll) {
        btnLoadSectorFlowAll.addEventListener("click", loadAllSectorFlowTabsFromDatabase);
    }

    const btnExportAllMarketData = document.getElementById("btn-export-all-market-data");
    if (btnExportAllMarketData) {
        btnExportAllMarketData.addEventListener("click", () => {
            window.location.href = "/api/export/all-market-data?years=3";
            showNotification("Đang xuất Excel tổng hợp nhiều sheet...", "emerald");
        });
    }

    const priceMatrixConfig = {
        close: { key: "Close", title: "Giá đóng cửa (VND)", summary: ["Average 20 phiên", "Average 60 phiên", "Average 250 phiên", "Min 52 tuần", "Max 52 tuần"], digits: 0, percent: false, heat: false },
        return: { key: "ReturnPct", title: "Return theo ngày (%)", summary: ["Average 20 phiên", "Average 60 phiên", "Average 250 phiên", "5%", "50%", "95%"], digits: 2, percent: true, heat: true }
    };

    async function loadPriceReturnHistory(force = false) {
        if (state.priceReturnHistory && !force) return state.priceReturnHistory;
        const res = await fetch("/api/price-return/history?years=3");
        const data = await res.json();
        if (!res.ok || data.error || data.detail) throw new Error(data.error || data.detail || `HTTP ${res.status}`);
        state.priceReturnHistory = data;
        return data;
    }

    async function loadPriceMatrix(view = "return", force = false) {
        const panel = document.querySelector(`.price-matrix-panel[data-price-view="${view}"]`);
        const table = panel ? panel.querySelector(".price-matrix-table") : null;
        if (table) table.innerHTML = `<tbody><tr><td class="text-center text-muted"><i class="fa-solid fa-circle-notch fa-spin"></i> Đang dựng matrix 3 năm từ database...</td></tr></tbody>`;
        try {
            await loadPriceReturnHistory(force);
            renderPriceMatrix(view);
        } catch (err) {
            showNotification(`Lỗi dữ liệu ${view}: ${err.message}`, "red");
        }
    }

    function renderPriceMatrix(view) {
        const history = state.priceReturnHistory;
        const config = priceMatrixConfig[view];
        if (!history || !config) return;
        const panel = document.querySelector(`.price-matrix-panel[data-price-view="${view}"]`);
        const table = panel ? panel.querySelector(".price-matrix-table") : null;
        const meta = panel ? panel.querySelector(".price-matrix-meta") : null;
        if (!table) return;
        const tickers = history.tickers || [];
        const valuesByTicker = {};
        tickers.forEach(ticker => {
            valuesByTicker[ticker] = (history.rows || [])
                .map(day => day.values?.[ticker]?.[config.key])
                .filter(value => value !== null && value !== undefined && !Number.isNaN(Number(value)))
                .map(Number);
        });
        const summaryRows = config.summary.map(label => {
            const statKey = normalizeStatLabel(label);
            return `<tr class="sector-matrix-summary-row"><th>${label}</th>${tickers.map(ticker => `<td>${formatMatrixValue(history.stats?.[view]?.[statKey]?.[ticker], config)}</td>`).join("")}</tr>`;
        }).join("");
        table.classList.add("sector-matrix-table");
        table.innerHTML = `<tbody>${summaryRows}<tr class="sector-matrix-spacer"><td colspan="${tickers.length + 1}"></td></tr><tr class="sector-matrix-title"><th colspan="${tickers.length + 1}">${config.title}</th></tr><tr class="sector-matrix-header"><th>Dates</th>${tickers.map(ticker => `<th>${ticker}</th>`).join("")}</tr>${(history.rows || []).map(day => `<tr><th>${day.Date}</th>${tickers.map(ticker => { const value = day.values?.[ticker]?.[config.key]; const cls = config.heat ? heatClass(value, valuesByTicker[ticker]) : ""; return `<td class="${cls}">${formatMatrixValue(value, config)}</td>`; }).join("")}</tr>`).join("")}</tbody>`;
        if (meta) meta.textContent = `Nguồn: database | ${history.start_date} đến ${history.end_date} | ${history.rows.length} phiên | ${tickers.length} mã`;
    }

    document.querySelectorAll(".btn-load-price-matrix").forEach(btn => {
        btn.addEventListener("click", () => {
            const panel = btn.closest(".price-matrix-panel");
            loadPriceMatrix(panel ? panel.dataset.priceView : "return", true);
        });
    });

    document.querySelectorAll(".btn-export-price-matrix").forEach(btn => {
        btn.addEventListener("click", () => {
            const panel = btn.closest(".price-matrix-panel");
            const view = panel ? panel.dataset.priceView : "return";
            window.location.href = view === "close" ? "/api/export/close-matrix?years=3" : "/api/export/return-matrix?years=3";
            showNotification(view === "close" ? "Đang xuất Excel giá Close 3 năm..." : "Đang xuất Excel Return % 3 năm...", "emerald");
        });
    });

    let fullExportPollTimer = null;

    function updateFullExportProgress(status) {
        const panel = document.getElementById("full-export-progress-panel");
        const bar = document.getElementById("full-export-progress-bar");
        const label = document.getElementById("full-export-progress-label");
        const step = document.getElementById("full-export-step");
        const download = document.getElementById("full-export-download");
        if (!panel || !bar || !label || !step || !download) return;

        const progress = Math.max(0, Math.min(100, Number(status.progress || 0)));
        panel.style.display = "block";
        bar.style.width = `${progress}%`;
        label.textContent = `${progress.toFixed(0)}%`;
        step.textContent = status.error || status.step || "Đang xử lý...";
        download.style.display = status.ready ? "inline-flex" : "none";
        if (status.ready) {
            download.href = `/api/export/full-workbook/download?t=${Date.now()}`;
        }
    }

    async function pollFullExportStatus() {
        try {
            const res = await fetch("/api/export/full-workbook/status");
            const status = await res.json();
            updateFullExportProgress(status);
            if (status.error) {
                clearInterval(fullExportPollTimer);
                fullExportPollTimer = null;
                showNotification(`Lỗi xuất tổng hợp: ${status.error}`, "red");
            } else if (status.ready) {
                clearInterval(fullExportPollTimer);
                fullExportPollTimer = null;
                showNotification("File tổng hợp đã sẵn sàng tải xuống.", "emerald");
                if (!window.__fullExportAutoDownloaded) {
                    window.__fullExportAutoDownloaded = true;
                    window.location.href = `/api/export/full-workbook/download?t=${Date.now()}`;
                }
            }
        } catch (err) {
            clearInterval(fullExportPollTimer);
            fullExportPollTimer = null;
            showNotification(`Không đọc được tiến độ export: ${err.message}`, "red");
        }
    }

    document.getElementById("btn-export-full-workbook")?.addEventListener("click", async () => {
        const btn = document.getElementById("btn-export-full-workbook");
        const download = document.getElementById("full-export-download");
        if (download) download.style.display = "none";
        window.__fullExportAutoDownloaded = false;
        if (btn) btn.disabled = true;
        try {
            const res = await fetch("/api/export/full-workbook/start?years=3", { method: "POST" });
            const data = await res.json();
            if (!res.ok || data.error || data.detail) throw new Error(data.error || data.detail || `HTTP ${res.status}`);
            showNotification("Đã bắt đầu gộp workbook, theo dõi thanh tiến độ bên dưới.", "emerald");
            await pollFullExportStatus();
            if (fullExportPollTimer) clearInterval(fullExportPollTimer);
            fullExportPollTimer = setInterval(pollFullExportStatus, 2000);
        } catch (err) {
            showNotification(`Không khởi động được export tổng hợp: ${err.message}`, "red");
        } finally {
            if (btn) btn.disabled = false;
        }
    });

    async function initializeOhlcTab() {
        const select = document.getElementById("ohlc-ticker-select");
        if (!select) return;
        if (select.options.length === 0) {
            await loadTickersDropdown();
            select.innerHTML = "";
            (state.tickers.length ? state.tickers : ["HPG", "VCI", "FPT"]).forEach(symbol => {
                const opt = document.createElement("option");
                opt.value = symbol;
                opt.textContent = symbol;
                select.appendChild(opt);
            });
            if ([...select.options].some(opt => opt.value === "HPG")) select.value = "HPG";
        }
        loadOhlcChart(select.value);
    }

    async function loadOhlcChart(symbol) {
        if (!symbol) return;
        const meta = document.getElementById("ohlc-meta");
        if (meta) meta.textContent = "Đang tải OHLC 3 năm từ database...";
        try {
            const res = await fetch(`/api/ohlc/${encodeURIComponent(symbol)}?years=3`);
            const data = await res.json();
            if (!res.ok || data.error || data.detail) throw new Error(data.error || data.detail || `HTTP ${res.status}`);
            drawOhlcCanvas(data.history || []);
            renderOhlcSummary(data);
            if (meta) meta.textContent = `${data.symbol} | ${data.industry} | ${data.start_date} đến ${data.end_date} | ${(data.history || []).length} nến`;
        } catch (err) {
            showNotification(`Lỗi OHLC: ${err.message}`, "red");
        }
    }

    function renderOhlcSummary(data) {
        const wrap = document.getElementById("ohlc-summary");
        const history = data.history || [];
        if (!wrap || history.length === 0) return;
        const last = history[history.length - 1];
        const prev = history[history.length - 2] || last;
        const ret = prev.close ? (last.close / prev.close - 1) * 100 : 0;
        wrap.innerHTML = `<div><span>Mã</span><strong>${data.symbol}</strong></div><div><span>Close</span><strong>${formatNumber(last.close, 0)}</strong></div><div><span>Return 1D</span><strong class="${ret >= 0 ? "text-green" : "text-red"}">${formatSigned(ret, 2)}%</strong></div><div><span>Volume</span><strong>${formatNumber(last.volume, 0)}</strong></div>`;
    }

    function drawOhlcCanvas(history) {
        const canvas = document.getElementById("ohlc-canvas");
        if (!canvas || history.length === 0) return;
        const rect = canvas.parentElement.getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;
        canvas.width = Math.max(900, rect.width) * dpr;
        canvas.height = 480 * dpr;
        canvas.style.width = "100%";
        canvas.style.height = "480px";
        const ctx = canvas.getContext("2d");
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        const width = canvas.width / dpr;
        const height = canvas.height / dpr;
        ctx.clearRect(0, 0, width, height);
        const pad = { left: 62, right: 18, top: 18, bottom: 42 };
        const plotW = width - pad.left - pad.right;
        const plotH = height - pad.top - pad.bottom;
        const maxP = Math.max(...history.map(d => d.high));
        const minP = Math.min(...history.map(d => d.low));
        const y = price => pad.top + (maxP - price) / (maxP - minP || 1) * plotH;
        const candleW = Math.max(2, plotW / history.length * 0.62);
        ctx.strokeStyle = "rgba(255,255,255,0.08)";
        ctx.fillStyle = "rgba(255,255,255,0.55)";
        ctx.font = "12px Inter, sans-serif";
        for (let i = 0; i <= 5; i++) {
            const py = pad.top + (plotH / 5) * i;
            const price = maxP - ((maxP - minP) / 5) * i;
            ctx.beginPath(); ctx.moveTo(pad.left, py); ctx.lineTo(width - pad.right, py); ctx.stroke();
            ctx.fillText(formatNumber(price, 0), 8, py + 4);
        }
        history.forEach((d, idx) => {
            const x = pad.left + (idx + 0.5) * (plotW / history.length);
            const color = d.close >= d.open ? "#26a69a" : "#ef5350";
            ctx.strokeStyle = color; ctx.fillStyle = color;
            ctx.beginPath(); ctx.moveTo(x, y(d.high)); ctx.lineTo(x, y(d.low)); ctx.stroke();
            const top = y(Math.max(d.open, d.close));
            const bot = y(Math.min(d.open, d.close));
            ctx.fillRect(x - candleW / 2, top, candleW, Math.max(1, bot - top));
        });
        const step = Math.max(1, Math.floor(history.length / 6));
        ctx.fillStyle = "rgba(255,255,255,0.6)";
        for (let i = 0; i < history.length; i += step) {
            const x = pad.left + (i + 0.5) * (plotW / history.length);
            ctx.fillText(history[i].date.slice(2), x - 24, height - 14);
        }
    }

    document.getElementById("btn-load-ohlc")?.addEventListener("click", () => {
        const select = document.getElementById("ohlc-ticker-select");
        loadOhlcChart(select ? select.value : "HPG");
    });
    document.getElementById("ohlc-ticker-select")?.addEventListener("change", e => loadOhlcChart(e.target.value));

    async function loadNotableStocks() {
        const meta = document.getElementById("notable-stocks-meta");
        if (meta) meta.textContent = "Đang lọc cổ phiếu nổi bật từ database...";
        try {
            const res = await fetch("/api/notable-stocks");
            const data = await res.json();
            if (!res.ok || data.error || data.detail) throw new Error(data.error || data.detail || `HTTP ${res.status}`);
            state.notableStocks = data;
            renderStockSignalList("notable-stock-list", data.notable || [], "notable");
            renderStockSignalList("niche-stock-list", data.niche || [], "niche");
            renderStockSignalList("outflow-stock-list", data.outflow || [], "outflow");
            if (meta) meta.textContent = `Nguồn: database | Ngày ${data.date} | Refresh tự động lúc 17:00 GMT+7 khi server/app đang mở.`;
        } catch (err) {
            showNotification(`Lỗi dashboard cổ phiếu: ${err.message}`, "red");
        }
    }

    function renderStockSignalList(containerId, rows, mode) {
        const container = document.getElementById(containerId);
        if (!container) return;
        container.innerHTML = rows.slice(0, 12).map(item => {
            const isOut = mode === "outflow";
            const cls = isOut ? "text-red" : "text-green";
            return `<div class="stock-signal-card"><div class="stock-signal-top"><strong>${item.Ticker}</strong><span class="${cls}">${formatSigned(item.Return1D, 2)}%</span></div><div class="stock-signal-sub">${item.Industry} | Close ${formatNumber(item.Close, 0)} | GTGD ${formatNumber(item.LiquidityBillion, 1)} tỷ</div><div class="stock-signal-sub">Vol/MA20 ${formatNumber(item.VolRatio, 2)}x | RSI ${formatNumber(item.RSI14, 1)} | Score ${formatNumber(item.Score, 1)}</div><div class="stock-reasons">${(item.Reasons || []).slice(0, 4).map(r => `<span>${r}</span>`).join("")}</div></div>`;
        }).join("");
    }

    document.getElementById("btn-load-notable-stocks")?.addEventListener("click", loadNotableStocks);

    // --- 4. MARKET ANALYSIS LOGIC ---
    async function fetchMarketData() {
        const indTable = document.getElementById("market-industry-table").querySelector("tbody");
        try {
            const res = await fetch("/api/market-analysis");
            const data = await res.json();
            state.currentMarketData = data;
            
            // Set global breadth metrics
            document.getElementById("market-ma20").textContent = `${(data.breadth.ma20 * 100).toFixed(1)}%`;
            document.getElementById("market-ma50").textContent = `${(data.breadth.ma50 * 100).toFixed(1)}%`;
            document.getElementById("market-ma100").textContent = `${(data.breadth.ma100 * 100).toFixed(1)}%`;
            document.getElementById("market-ma200").textContent = `${(data.breadth.ma200 * 100).toFixed(1)}%`;
            
            // Enable exports if scanner finished at least once
            const hasData = data.industries && data.industries.length > 0;
            document.getElementById("btn-export-market").disabled = !hasData;

            if (!hasData) {
                indTable.innerHTML = `<tr><td colspan="5" class="text-center text-muted">Vui lòng khởi động Bộ Quét VN302 ở tab bên cạnh để thu thập dữ liệu thị trường đầu tiên.</td></tr>`;
                return;
            }

            indTable.innerHTML = "";
            data.industries.forEach(ind => {
                const tr = document.createElement("tr");
                tr.className = "clickable-row";
                
                const retColor = ind.avg_return >= 0 ? "text-green" : "text-red";
                const relVal = ind.relative_to_vnindex || 0;
                const relColor = relVal >= 0 ? "text-green" : "text-red";
                
                tr.addEventListener("click", () => selectMarketIndustry(ind.industry));

                tr.innerHTML = `
                    <td><strong>${ind.industry}</strong></td>
                    <td class="text-center">${ind.tickers_count}</td>
                    <td class="${retColor} font-weight-bold">${ind.avg_return >= 0 ? "+" : ""}${ind.avg_return.toFixed(2)}%</td>
                    <td class="${relColor}">${relVal >= 0 ? "+" : ""}${relVal.toFixed(2)}%</td>
                    <td><span class="badge ${relVal >= 0 ? "badge-green" : "badge-red"}">${relVal >= 0 ? "Outperform" : "Underperform"}</span></td>
                `;
                indTable.appendChild(tr);
            });
        } catch (err) {
            console.error("Error fetching market data:", err);
            indTable.innerHTML = `<tr><td colspan="5" class="text-center text-red">Lỗi tải dữ liệu: ${err.message}</td></tr>`;
        }
    }

    // Shows details of a selected sector
    function selectMarketIndustry(industryName) {
        if (!state.currentMarketData || !state.currentMarketData.industries) return;
        
        // Highlight active row in main table
        const rows = document.getElementById("market-industry-table").querySelectorAll("tbody tr");
        rows.forEach(r => {
            if (r.querySelector("td") && r.querySelector("td").textContent === industryName) {
                r.style.backgroundColor = "rgba(0, 229, 255, 0.08)";
                r.style.borderColor = "var(--accent-cyan)";
            } else {
                r.style.backgroundColor = "";
                r.style.borderColor = "";
            }
        });

        document.getElementById("industry-detail-title").textContent = `Chi Tiết Cổ Phiếu Trong Ngành: ${industryName}`;
        
        const detailTable = document.getElementById("market-detail-table").querySelector("tbody");
        detailTable.innerHTML = "";
        
        const constituents = state.currentMarketData.details[industryName] || [];
        const vnindex_ret = state.currentMarketData.vnindex_return || 0;

        constituents.forEach(item => {
            const tr = document.createElement("tr");
            tr.className = "clickable-row";
            
            const retColor = item.return_pct >= 0 ? "text-green" : "text-red";
            const relVal = item.return_pct - vnindex_ret;
            const relColor = relVal >= 0 ? "text-green" : "text-red";
            
            // Double click opens candlestick chart
            tr.addEventListener("click", () => openTickerChart(item.symbol));

            tr.innerHTML = `
                <td><strong>${item.symbol}</strong></td>
                <td class="${retColor}">${item.return_pct >= 0 ? "+" : ""}${item.return_pct.toFixed(2)}%</td>
                <td class="${relColor}">${relVal >= 0 ? "+" : ""}${relVal.toFixed(2)}%</td>
            `;
            detailTable.appendChild(tr);
        });
    }

    // --- 5. VN302 SCANNER MULTI-THREADING LOGIC ---
    const btnStartScan = document.getElementById("btn-start-scan");
    const btnStopScan = document.getElementById("btn-stop-scan");
    const btnExportScan = document.getElementById("btn-export-scan");
    const scanProgress = document.getElementById("scan-progress-bar");
    const scanProgressText = document.getElementById("scan-progress-text");

    btnStartScan.addEventListener("click", async () => {
        try {
            await fetch("/api/scan/start", { method: "POST" });
            
            btnStartScan.disabled = true;
            btnStopScan.disabled = false;
            showNotification("Đã bắt đầu tiến trình quét VN302 trên luồng ngầm...", "cyan");
            
            // Start polling progress
            state.scanInterval = setInterval(pollScanStatus, 1500);
        } catch (err) {
            console.error("Error starting scan:", err);
        }
    });

    btnStopScan.addEventListener("click", async () => {
        try {
            await fetch("/api/scan/stop", { method: "POST" });
            stopScanPolling();
            showNotification("Đã gửi yêu cầu dừng quét.", "red");
        } catch (err) {
            console.error("Error stopping scan:", err);
        }
    });

    function stopScanPolling() {
        if (state.scanInterval) {
            clearInterval(state.scanInterval);
            state.scanInterval = null;
        }
        btnStartScan.disabled = false;
        btnStopScan.disabled = true;
    }

    async function pollScanStatus() {
        try {
            const res = await fetch("/api/scan/status");
            const status = await res.json();
            
            const progress = status.progress || 0;
            scanProgress.style.width = `${progress}%`;
            
            if (status.running) {
                scanProgressText.textContent = `Đang quét: ${progress.toFixed(0)}% (Khớp ${status.current}/${status.total} CP)`;
                // Update table reactively
                loadScannerResults();
            } else {
                scanProgressText.textContent = `Quét hoàn thành 100%! (${status.total}/${status.total} CP)`;
                scanProgress.style.width = "100%";
                stopScanPolling();
                btnExportScan.disabled = false;
                loadScannerResults();
                // Refresh heatmap & market tabs since scan finished
                fetchHeatmapData();
                fetchMarketData();
            }
        } catch (err) {
            console.error("Error polling scan status:", err);
            stopScanPolling();
        }
    }

    async function loadScannerResults() {
        try {
            const res = await fetch("/api/scan/results");
            const data = await res.json();
            state.currentScannerResults = data.results || [];
            applyScannerFilters(); // Filter and render in client side
        } catch (err) {
            console.error("Error loading scan results:", err);
        }
    }

    // Set filter listeners
    document.getElementById("filter-sec").addEventListener("change", applyScannerFilters);
    document.getElementById("filter-rsi").addEventListener("change", applyScannerFilters);
    document.getElementById("filter-macd").addEventListener("change", applyScannerFilters);
    document.getElementById("search-scan").addEventListener("input", applyScannerFilters);

    function applyScannerFilters() {
        const sector = document.getElementById("filter-sec").value;
        const rsiFilter = document.getElementById("filter-rsi").value;
        const macdFilter = document.getElementById("filter-macd").value;
        const query = document.getElementById("search-scan").value.toUpperCase().trim();
        
        const tableBody = document.getElementById("scanner-table").querySelector("tbody");
        
        let filtered = state.currentScannerResults;

        // Apply Sector Filter
        if (sector !== "All") {
            filtered = filtered.filter(item => item.Industry === sector);
        }

        // Apply Search Query
        if (query) {
            filtered = filtered.filter(item => item.Ticker.includes(query));
        }

        // Apply RSI Filter
        if (rsiFilter !== "All") {
            filtered = filtered.filter(item => {
                const rsi = item.RSI;
                if (rsiFilter === "Oversold") return rsi < 30;
                if (rsiFilter === "Overbought") return rsi > 70;
                if (rsiFilter === "Bullish") return rsi > 50;
                if (rsiFilter === "Bearish") return rsi < 50;
                return true;
            });
        }

        // Apply MACD Filter
        if (macdFilter !== "All") {
            filtered = filtered.filter(item => {
                const status = item.MACD || "";
                if (macdFilter === "CrossUp") return status.toLowerCase().includes("cross up");
                if (macdFilter === "CrossDown") return status.toLowerCase().includes("cross down");
                if (macdFilter === "Positive") return status.toLowerCase().includes("positive");
                if (macdFilter === "Negative") return status.toLowerCase().includes("negative");
                return true;
            });
        }

        // Render rows
        if (filtered.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="15" class="text-center text-muted">Không tìm thấy mã cổ phiếu phù hợp bộ lọc.</td></tr>`;
            return;
        }

        tableBody.innerHTML = "";
        filtered.forEach(item => {
            const tr = document.createElement("tr");
            tr.className = "clickable-row";
            tr.addEventListener("click", () => openTickerChart(item.Ticker));

            // Price conversion (API prices in standard or scaled depending on source)
            const price = item.Price || 0;
            const returnVal = item.Return_2026_03_23 || 0;
            const retColor = returnVal >= 0 ? "text-green" : "text-red";
            
            // Helpers for MAs
            const renderMA = (val) => val === 1 ? `<span class="text-green"><i class="fa-solid fa-circle-chevron-up"></i></span>` : `<span class="text-red"><i class="fa-solid fa-circle-chevron-down"></i></span>`;
            
            const rsiVal = item.RSI || 0;
            let rsiColor = "";
            if (rsiVal < 30) rsiColor = "text-green font-weight-bold";
            else if (rsiVal > 70) rsiColor = "text-red font-weight-bold";

            const rsiDiv = item.RSI_Divergence || "";
            const macdDiv = item.MACD_Divergence || "";

            tr.innerHTML = `
                <td><strong>${item.Ticker}</strong></td>
                <td>${price.toLocaleString()}</td>
                <td class="${retColor} font-weight-bold">${returnVal >= 0 ? "+" : ""}${returnVal.toFixed(2)}%</td>
                <td class="text-center">${renderMA(item.MA20)}</td>
                <td class="text-center">${renderMA(item.MA50)}</td>
                <td class="text-center">${renderMA(item.MA100)}</td>
                <td class="text-center">${renderMA(item.MA200)}</td>
                <td>${(item.High_52w || 0).toLocaleString()}</td>
                <td>${(item.Low_52w || 0).toLocaleString()}</td>
                <td><span class="badge ${item.Breakout === 'High Breakout' ? 'badge-green' : item.Breakout === 'Low Breakout' ? 'badge-red' : 'badge-cyan'}">${item.Breakout || "Normal"}</span></td>
                <td class="${rsiColor}">${rsiVal.toFixed(1)}</td>
                <td><span class="${rsiDiv.includes('Bullish') ? 'text-green' : 'text-red'}">${rsiDiv}</span></td>
                <td><span class="${item.MACD.includes('Up') || item.MACD.includes('Positive') ? 'text-green' : 'text-red'}">${item.MACD}</span></td>
                <td><span class="${macdDiv.includes('Bullish') ? 'text-green' : 'text-red'}">${macdDiv}</span></td>
                <td><span class="badge badge-purple">${item.Industry}</span></td>
            `;
            tableBody.appendChild(tr);
        });
    }

    // --- 6. ANTIGRAVITY VOLATILITY SETUP ---
    const btnStartAnti = document.getElementById("btn-start-anti");
    const btnStopAnti = document.getElementById("btn-stop-anti");
    const btnExportAnti = document.getElementById("btn-export-anti");
    const antiProgress = document.getElementById("anti-progress-bar");
    const antiProgressText = document.getElementById("anti-progress-text");

    btnStartAnti.addEventListener("click", async () => {
        try {
            await fetch("/api/antigravity/start", { method: "POST" });
            btnStartAnti.disabled = true;
            btnStopAnti.disabled = false;
            showNotification("Đang chạy quét mô hình nén kiệt vol Antigravity...", "purple");
            state.antiInterval = setInterval(pollAntiStatus, 1500);
        } catch (err) {
            console.error("Error starting Antigravity scan:", err);
        }
    });

    btnStopAnti.addEventListener("click", async () => {
        try {
            await fetch("/api/antigravity/stop", { method: "POST" });
            stopAntiPolling();
            showNotification("Đã dừng quét Antigravity.", "red");
        } catch (err) {
            console.error("Error stopping Antigravity scan:", err);
        }
    });

    function stopAntiPolling() {
        if (state.antiInterval) {
            clearInterval(state.antiInterval);
            state.antiInterval = null;
        }
        btnStartAnti.disabled = false;
        btnStopAnti.disabled = true;
    }

    async function pollAntiStatus() {
        try {
            const res = await fetch("/api/antigravity/status");
            const status = await res.json();
            const progress = status.progress || 0;
            antiProgress.style.width = `${progress}%`;
            
            if (status.running) {
                antiProgressText.textContent = `Đang quét Antigravity: ${progress.toFixed(0)}% (${status.current}/${status.total} CP)`;
                loadAntiResults();
            } else {
                antiProgressText.textContent = `Quét Antigravity hoàn thành 100%!`;
                antiProgress.style.width = "100%";
                stopAntiPolling();
                btnExportAnti.disabled = false;
                loadAntiResults();
            }
        } catch (err) {
            console.error("Error polling Anti status:", err);
            stopAntiPolling();
        }
    }

    async function loadAntiResults() {
        try {
            const res = await fetch("/api/antigravity/results");
            const data = await res.json();
            
            // Set Stats Cards
            document.getElementById("anti-avg-days").textContent = (data.stats.avg_days || 0).toFixed(1);
            document.getElementById("anti-wr-5d").textContent = `${((data.stats.wr_5d || 0) * 100).toFixed(1)}%`;
            document.getElementById("anti-wr-10d").textContent = `${((data.stats.wr_10d || 0) * 100).toFixed(1)}%`;
            document.getElementById("anti-wr-20d").textContent = `${((data.stats.wr_20d || 0) * 100).toFixed(1)}%`;
            document.getElementById("anti-avg-rr").textContent = (data.stats.avg_rr || 0).toFixed(2);
            
            // Fill Signals Table
            const tableBody = document.getElementById("anti-table").querySelector("tbody");
            const signals = data.signals || [];
            
            if (signals.length === 0) {
                tableBody.innerHTML = `<tr><td colspan="7" class="text-center text-muted">Chưa tìm thấy cổ phiếu có mô hình Antigravity Setup.</td></tr>`;
                return;
            }
            
            tableBody.innerHTML = "";
            signals.forEach(sig => {
                const tr = document.createElement("tr");
                tr.className = "clickable-row";
                tr.addEventListener("click", () => openTickerChart(sig.Ticker));

                const renderRet = (val) => {
                    const num = val || 0;
                    const c = num >= 0 ? "text-green" : "text-red";
                    return `<span class="${c}">${num >= 0 ? "+" : ""}${num.toFixed(2)}%</span>`;
                };

                tr.innerHTML = `
                    <td><strong>${sig.Ticker}</strong></td>
                    <td>${sig.Date}</td>
                    <td class="text-center">${sig.Days_Setup}</td>
                    <td>${renderRet(sig.Return_5D)}</td>
                    <td>${renderRet(sig.Return_10D)}</td>
                    <td>${renderRet(sig.Return_20D)}</td>
                    <td class="text-cyan font-weight-bold text-center">${(sig.RR || 0).toFixed(2)}</td>
                `;
                tableBody.appendChild(tr);
            });
        } catch (err) {
            console.error("Error loading Anti results:", err);
        }
    }

    // --- 7. WATCHLIST TÍCH LŨY (CONSOLIDATION WATCHLIST) ---
    const btnStartWatch = document.getElementById("btn-start-watch");
    const btnStopWatch = document.getElementById("btn-stop-watch");
    const btnExportWatch = document.getElementById("btn-export-watch");
    const watchProgress = document.getElementById("watch-progress-bar");
    const watchProgressText = document.getElementById("watch-progress-text");

    btnStartWatch.addEventListener("click", async () => {
        try {
            await fetch("/api/watchlist/start", { method: "POST" });
            btnStartWatch.disabled = true;
            btnStopWatch.disabled = false;
            showNotification("Đang phân tích các vùng tích lũy Darvas biên hẹp...", "cyan");
            state.watchInterval = setInterval(pollWatchStatus, 1500);
        } catch (err) {
            console.error("Error starting Watchlist scan:", err);
        }
    });

    btnStopWatch.addEventListener("click", async () => {
        try {
            await fetch("/api/watchlist/stop", { method: "POST" });
            stopWatchPolling();
            showNotification("Đã dừng quét Watchlist.", "red");
        } catch (err) {
            console.error("Error stopping Watchlist scan:", err);
        }
    });

    function stopWatchPolling() {
        if (state.watchInterval) {
            clearInterval(state.watchInterval);
            state.watchInterval = null;
        }
        btnStartWatch.disabled = false;
        btnStopWatch.disabled = true;
    }

    async function pollWatchStatus() {
        try {
            const res = await fetch("/api/watchlist/status");
            const status = await res.json();
            const progress = status.progress || 0;
            watchProgress.style.width = `${progress}%`;
            
            if (status.running) {
                watchProgressText.textContent = `Đang quét Watchlist: ${progress.toFixed(0)}% (${status.current}/${status.total} CP)`;
                loadWatchResults();
            } else {
                watchProgressText.textContent = `Quét Watchlist hoàn thành 100%!`;
                watchProgress.style.width = "100%";
                stopWatchPolling();
                btnExportWatch.disabled = false;
                loadWatchResults();
            }
        } catch (err) {
            console.error("Error polling Watch status:", err);
            stopWatchPolling();
        }
    }

    async function loadWatchResults() {
        try {
            const res = await fetch("/api/watchlist/results");
            const data = await res.json();
            const tableBody = document.getElementById("watch-table").querySelector("tbody");
            const watchlist = data.watchlist || [];
            
            if (watchlist.length === 0) {
                tableBody.innerHTML = `<tr><td colspan="5" class="text-center text-muted">Hiện tại không có cổ phiếu nào khớp tiêu chí tích lũy biên hẹp và cạn vol.</td></tr>`;
                return;
            }
            
            tableBody.innerHTML = "";
            watchlist.forEach(w => {
                const tr = document.createElement("tr");
                tr.className = "clickable-row";
                tr.addEventListener("click", () => openTickerChart(w.Ticker));

                const volRatio = w.Vol_Ratio || 0;
                const range5d = w.Range_5D || 0;

                tr.innerHTML = `
                    <td><strong>${w.Ticker}</strong></td>
                    <td>${(w.Price || 0).toLocaleString()}</td>
                    <td class="text-center font-weight-bold text-cyan">${w.Consolidation_Days} phiên</td>
                    <td class="text-center text-green font-weight-bold">${(volRatio * 100).toFixed(1)}%</td>
                    <td class="text-center text-green font-weight-bold">±${range5d.toFixed(2)}%</td>
                `;
                tableBody.appendChild(tr);
            });
        } catch (err) {
            console.error("Error loading Watch results:", err);
        }
    }

    // --- 8. RSI BACKTESTER FORM SUBMIT & CHARTS ---
    const backtestForm = document.getElementById("backtest-form");
    const btnRunBacktest = document.getElementById("btn-run-backtest");
    const btnExportBacktest = document.getElementById("btn-export-backtest");

    backtestForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        
        btnRunBacktest.disabled = true;
        btnRunBacktest.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Đang tính toán backtest...';
        
        const params = {
            symbol: document.getElementById("bt-ticker").value,
            start_date: document.getElementById("bt-start").value,
            end_date: document.getElementById("bt-end").value,
            initial_capital: parseFloat(document.getElementById("bt-capital").value),
            position_size: parseFloat(document.getElementById("bt-pos-size").value),
            rsi_period: parseInt(document.getElementById("bt-rsi-period").value),
            buy_threshold: parseFloat(document.getElementById("bt-buy-th").value),
            sell_threshold: parseFloat(document.getElementById("bt-sell-th").value),
            stop_loss: document.getElementById("bt-sl").value.trim(),
            take_profit: document.getElementById("bt-tp").value.trim()
        };

        try {
            const res = await fetch("/api/backtest", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(params)
            });
            const data = await res.json();
            
            if (data.error) {
                showNotification(`Lỗi Backtest: ${data.error}`, "red");
                btnRunBacktest.disabled = false;
                btnRunBacktest.innerHTML = '<i class="fa-solid fa-rotate"></i> Chạy Thử Nghiệm (Backtest)';
                return;
            }

            showNotification(`Backtest hoàn tất cho ${params.symbol}!`, "cyan");
            btnRunBacktest.disabled = false;
            btnRunBacktest.innerHTML = '<i class="fa-solid fa-rotate"></i> Chạy Thử Nghiệm (Backtest)';
            btnExportBacktest.disabled = false;

            // Render Metrics
            const metrics = data.metrics || {};
            document.getElementById("bt-metric-return").textContent = `${(metrics.total_return || 0).toFixed(2)}%`;
            document.getElementById("bt-metric-winrate").textContent = `${(metrics.win_rate || 0).toFixed(2)}%`;
            document.getElementById("bt-metric-trades").textContent = metrics.total_trades || 0;
            document.getElementById("bt-metric-sharpe").textContent = (metrics.sharpe_ratio || 0).toFixed(2);
            document.getElementById("bt-metric-maxdd").textContent = `${(metrics.max_drawdown || 0).toFixed(2)}%`;

            // Style metric values depending on profit
            const metricReturn = document.getElementById("bt-metric-return");
            if (metrics.total_return >= 0) {
                metricReturn.className = "metric-value text-green";
            } else {
                metricReturn.className = "metric-value text-red";
            }

            // Render Trades Table
            const tradesTable = document.getElementById("bt-trades-table").querySelector("tbody");
            const trades = data.trades || [];
            
            if (trades.length === 0) {
                tradesTable.innerHTML = `<tr><td colspan="6" class="text-center text-muted">Không phát sinh giao dịch nào trong khoảng thời gian này.</td></tr>`;
            } else {
                tradesTable.innerHTML = "";
                trades.forEach(t => {
                    const tr = document.createElement("tr");
                    const profit = t.profit || 0;
                    const profitPct = t.profit_pct || 0;
                    const profColor = profitPct >= 0 ? "text-green" : "text-red";
                    
                    tr.innerHTML = `
                        <td>${t.entry_date}</td>
                        <td>${t.exit_date}</td>
                        <td>${(t.entry_price || 0).toLocaleString()}</td>
                        <td>${(t.exit_price || 0).toLocaleString()}</td>
                        <td class="${profColor}">${profit >= 0 ? "+" : ""}${profit.toLocaleString()} VND</td>
                        <td class="${profColor} font-weight-bold">${profitPct >= 0 ? "+" : ""}${profitPct.toFixed(2)}%</td>
                    `;
                    tradesTable.appendChild(tr);
                });
            }

            // Draw Equity Chart
            drawEquityChart(data.equity_curve || []);

        } catch (err) {
            console.error("Error executing backtest:", err);
            btnRunBacktest.disabled = false;
            btnRunBacktest.innerHTML = '<i class="fa-solid fa-rotate"></i> Chạy Thử Nghiệm (Backtest)';
        }
    });

    function drawEquityChart(curve) {
        const ctx = document.getElementById("equity-chart").getContext("2d");
        
        if (state.charts.equity) {
            state.charts.equity.destroy();
        }

        const labels = curve.map(c => c.date);
        const dataValues = curve.map(c => c.value);

        // Customize premium grid styles for Dark theme
        state.charts.equity = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Giá trị Tài Sản (VND)',
                    data: dataValues,
                    borderColor: '#00e5ff',
                    borderWidth: 2,
                    pointRadius: labels.length > 100 ? 0 : 2,
                    pointBackgroundColor: '#00e5ff',
                    backgroundColor: 'rgba(0, 229, 255, 0.05)',
                    fill: true,
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        backgroundColor: 'rgba(15, 18, 23, 0.95)',
                        titleColor: '#00e5ff',
                        bodyColor: '#ffffff',
                        borderColor: 'rgba(255, 255, 255, 0.1)',
                        borderWidth: 1,
                        padding: 10,
                        callbacks: {
                            label: function(context) {
                                return `Tài sản: ${context.parsed.y.toLocaleString()} VND`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { color: 'rgba(255, 255, 255, 0.03)' },
                        ticks: { color: '#a0aec0', maxTicksLimit: 10 }
                    },
                    y: {
                        grid: { color: 'rgba(255, 255, 255, 0.03)' },
                        ticks: {
                            color: '#a0aec0',
                            callback: function(value) {
                                return (value / 1000000).toFixed(0) + 'M';
                            }
                        }
                    }
                }
            }
        });
    }

    // --- 9. NEW THANH KHOẢN (LIQUIDITY) TAB AND CHARTS ---
    
    const liqMode = document.getElementById("liq-mode");
    const liqSingleControls = document.getElementById("liq-single-controls");
    const liqRangeControls = document.getElementById("liq-range-controls");
    const liqRangeVisuals = document.getElementById("liq-range-visuals");
    const liqRangeTableBody = document.getElementById("liq-range-table-body");
    


    const btnLoadLiquidity = document.getElementById("btn-load-liquidity");
    const liqDateInput = document.getElementById("liq-date");
    const searchLiquidity = document.getElementById("search-liquidity");
    
    // Store current liquidity data for local filtering
    let currentLiquidityData = [];

    btnLoadLiquidity.addEventListener("click", () => {
        loadLiquidityData();
    });
    
    liqDateInput.addEventListener("change", () => {
        loadLiquidityData();
    });
    
    document.getElementById("btn-sync-liq").addEventListener("click", startSyncProcess);

    searchLiquidity.addEventListener("input", () => {
        renderLiquidityTable(currentLiquidityData);
    });

    let liquidityInterval = null;

    async function loadLiquidityData() {
        const date = liqDateInput.value;
        const leader = document.getElementById("liq-leader-ticker");
        const totalVal = document.getElementById("liq-total-value");
        const totalVol = document.getElementById("liq-total-volume");
        const avgVal = document.getElementById("liq-avg-value");
        const leaderboard = document.getElementById("liquidity-leaderboard");
        const progressWrapper = document.getElementById("liq-progress-wrapper");
        const progressBar = document.getElementById("liq-progress-bar");
        const progressText = document.getElementById("liq-progress-text");

        if (liquidityInterval) {
            clearInterval(liquidityInterval);
            liquidityInterval = null;
        }

        leaderboard.innerHTML = `
            <div class="loading-state">
                <i class="fa-solid fa-circle-notch fa-spin"></i>
                <p>Đang quét và tính toán giá trị khớp lệnh thực tế trên HOSE...</p>
            </div>`;

        progressWrapper.style.display = "block";
        progressBar.style.width = "0%";
        progressText.textContent = "Khởi tạo tiến trình quét... (0%)";

        btnLoadLiquidity.disabled = true;
        btnLoadLiquidity.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Đang tải...';

        try {
            const startRes = await fetch(`/api/liquidity/start?date=${date}`, { method: "POST" });
            const startData = await startRes.json();

            liquidityInterval = setInterval(async () => {
                try {
                    const statusRes = await fetch("/api/liquidity/status");
                    const status = await statusRes.json();
                    
                    const progress = status.progress || 0;
                    progressBar.style.width = `${progress}%`;
                    
                    if (status.running) {
                        progressText.textContent = `Đang quét: ${progress.toFixed(0)}% (CP ${status.current}/${status.total})`;
                    } else {
                        progressText.textContent = `Hoàn thành 100%!`;
                        progressBar.style.width = "100%";
                        
                        clearInterval(liquidityInterval);
                        liquidityInterval = null;
                        
                        const resultsRes = await fetch("/api/liquidity/results");
                        const data = await resultsRes.json();
                        
                        btnLoadLiquidity.disabled = false;
                        btnLoadLiquidity.innerHTML = '<i class="fa-solid fa-arrows-rotate"></i> Tải Dữ Liệu';
                        progressWrapper.style.display = "none";
                        
                        if (data.error) {
                            showNotification(`Lỗi nạp thanh khoản: ${data.error}`, "red");
                            leaderboard.innerHTML = `<div class="loading-state text-red"><p>${data.error}</p></div>`;
                            return;
                        }
                        
                        currentLiquidityData = data.liquidity || [];
                        showNotification(`Nạp dữ liệu thanh khoản thành công cho ngày ${date}!`, "emerald");
                        
                        totalVal.textContent = `${(data.summary.total_value_vnd || 0).toLocaleString()} VND`;
                        totalVol.textContent = `${(data.summary.total_volume || 0).toLocaleString()} CP`;
                        leader.textContent = data.summary.leader_ticker || "N/A";
                        avgVal.textContent = `${(data.summary.avg_value_vnd || 0).toLocaleString()} VND`;
                        
                        renderLiquidityLeaderboard(currentLiquidityData, leaderboard);
                        drawLiquidityChart(currentLiquidityData.slice(0, 15));
                        renderLiquidityTable(currentLiquidityData);
                    }
                } catch (err) {
                    console.error("Error polling liquidity status:", err);
                    clearInterval(liquidityInterval);
                    liquidityInterval = null;
                    btnLoadLiquidity.disabled = false;
                    btnLoadLiquidity.innerHTML = '<i class="fa-solid fa-arrows-rotate"></i> Tải Dữ Liệu';
                    progressWrapper.style.display = "none";
                    leaderboard.innerHTML = `<div class="loading-state text-red"><p>Lỗi quét thanh khoản.</p></div>`;
                }
            }, 1000);

        } catch (err) {
            console.error("Error loading liquidity:", err);
            btnLoadLiquidity.disabled = false;
            btnLoadLiquidity.innerHTML = '<i class="fa-solid fa-arrows-rotate"></i> Tải Dữ Liệu';
            progressWrapper.style.display = "none";
            leaderboard.innerHTML = `<div class="loading-state text-red"><p>Lỗi tải dữ liệu thanh khoản.</p></div>`;
        }
    }

    function renderLiquidityLeaderboard(list, container) {
        if (list.length === 0) {
            container.innerHTML = `<p class="text-center text-muted">Không có dữ liệu xếp hạng.</p>`;
            return;
        }

        const top10 = list.slice(0, 10);
        const maxVal = top10[0] ? top10[0].Liquidity_VND : 1;

        container.innerHTML = "";
        top10.forEach((item, index) => {
            const row = document.createElement("div");
            row.className = "leaderboard-row";
            row.addEventListener("click", () => openTickerChart(item.Ticker));

            const rank = index + 1;
            const progressPct = (item.Liquidity_VND / maxVal) * 100;

            row.innerHTML = `
                <div class="leaderboard-rank rank-${rank <= 3 ? rank : 'other'}">${rank}</div>
                <div class="leaderboard-ticker">${item.Ticker}</div>
                <div class="leaderboard-bar-area">
                    <div class="leaderboard-label-row">
                        <span class="text-muted">${item.Industry}</span>
                        <span class="leaderboard-value">${(item.Liquidity_VND / 1000000000).toFixed(1)} Tỷ VND</span>
                    </div>
                    <div class="leaderboard-bar-container">
                        <div class="leaderboard-bar" style="width: ${progressPct}%;"></div>
                    </div>
                </div>
            `;
            container.appendChild(row);
        });
    }

    function drawLiquidityChart(top15) {
        const ctx = document.getElementById("liquidity-chart").getContext("2d");
        
        if (state.charts.liquidity) {
            state.charts.liquidity.destroy();
        }

        if (top15.length === 0) return;

        const labels = top15.map(item => item.Ticker);
        const valuesInBillion = top15.map(item => item.Liquidity_VND / 1000000000); // Scale to billions

        // Modern horizontal bar chart with Chart.js
        state.charts.liquidity = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Giá trị giao dịch (Tỷ VND)',
                    data: valuesInBillion,
                    backgroundColor: 'rgba(38, 166, 154, 0.45)',
                    borderColor: '#26a69a',
                    borderWidth: 1.5,
                    borderRadius: 4,
                    hoverBackgroundColor: 'rgba(38, 166, 154, 0.7)',
                    hoverBorderColor: '#26a69a'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: 'rgba(15, 18, 23, 0.95)',
                        titleColor: '#26a69a',
                        bodyColor: '#ffffff',
                        borderColor: 'rgba(255, 255, 255, 0.1)',
                        borderWidth: 1,
                        padding: 10,
                        callbacks: {
                            label: function(context) {
                                return `Thanh khoản: ${context.parsed.y.toFixed(2)} Tỷ VND`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { color: 'rgba(255, 255, 255, 0.03)' },
                        ticks: { color: '#a0aec0' }
                    },
                    y: {
                        grid: { color: 'rgba(255, 255, 255, 0.03)' },
                        ticks: {
                            color: '#a0aec0',
                            callback: function(value) {
                                return value + ' Tỷ';
                            }
                        }
                    }
                }
            }
        });
    }

    function renderLiquidityTable(list) {
        const tableBody = document.getElementById("liquidity-table").querySelector("tbody");
        const query = searchLiquidity.value.toUpperCase().trim();
        
        let filtered = list;
        if (query) {
            filtered = list.filter(item => item.Ticker.includes(query));
        }

        if (filtered.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="7" class="text-center text-muted">Không tìm thấy cổ phiếu phù hợp.</td></tr>`;
            return;
        }

        // Leader valuation for progress bar relative index
        const maxVal = list[0] ? list[0].Liquidity_VND : 1;

        tableBody.innerHTML = "";
        filtered.forEach(item => {
            const tr = document.createElement("tr");
            tr.className = "clickable-row";
            tr.addEventListener("click", () => openTickerChart(item.Ticker));

            const val = item.Liquidity_VND || 0;
            const progressPct = (val / maxVal) * 100;
            
            // Liquidity bracket classifications
            let badgeClass = "badge-red";
            let bracketText = "Thấp";
            if (val > 150000000000) { badgeClass = "badge-emerald"; bracketText = "Rất cao"; } // > 150B
            else if (val > 50000000000) { badgeClass = "badge-cyan"; bracketText = "Cao"; }      // > 50B
            else if (val > 15000000000) { badgeClass = "badge-purple"; bracketText = "Vừa"; }   // > 15B

            tr.innerHTML = `
                <td><strong>${item.Ticker}</strong></td>
                <td><span class="badge badge-purple">${item.Industry}</span></td>
                <td>${(item.Close || 0).toLocaleString()}</td>
                <td>${(item.Volume || 0).toLocaleString()}</td>
                <td class="text-cyan font-weight-bold">${val.toLocaleString()} VND</td>
                <td style="vertical-align: middle;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span class="text-muted" style="font-size: 11px; width: 35px; text-align: right;">${progressPct.toFixed(0)}%</span>
                        <div class="leaderboard-bar-container" style="flex-grow: 1; height: 5px;">
                            <div class="leaderboard-bar" style="width: ${progressPct}%; background-color: var(--accent-cyan);"></div>
                        </div>
                    </div>
                </td>
                <td><span class="badge ${badgeClass}">${bracketText}</span></td>
            `;
            tableBody.appendChild(tr);
        });
    }

    // --- 10. LIGHTWEIGHT CANDLESTICK MODAL CHART ---
    const modal = document.getElementById("ticker-modal");
    const modalTitle = document.getElementById("modal-ticker-title");
    
    // Close modal listener
    document.getElementById("btn-close-modal").addEventListener("click", () => {
        modal.style.display = "none";
    });
    window.addEventListener("click", (e) => {
        if (e.target === modal) {
            modal.style.display = "none";
        }
    });

    async function openTickerChart(symbol) {
        modalTitle.textContent = `Đồ thị Lịch sử giá & MA của ${symbol}`;
        modal.style.display = "block";

        const ctx = document.getElementById("modal-candlestick-chart").getContext("2d");
        
        if (state.charts.modal) {
            state.charts.modal.destroy();
        }

        // Draw loading
        ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);

        try {
            const source = appSource.value;
            const res = await fetch(`/api/history/${symbol}?source=${source}`);
            const data = await res.json();
            
            if (data.error || !data.history || data.history.length === 0) {
                showNotification(`Không thể tải dữ liệu nến: ${data.error || 'Empty'}`, "red");
                modal.style.display = "none";
                return;
            }

            const history = data.history;
            const labels = history.map(h => h.date);
            const closePrices = history.map(h => h.close);
            const ma50 = history.map(h => h.ma50);
            
            // Calculate wicks and bodies locally to simulate a beautiful candlestick chart on canvas!
            // To make it simple and extremely clean, we plot a detailed High/Low area and the Close price with moving averages!
            // This is visually stunning, extremely reactive and professional.
            state.charts.modal = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'Giá Đóng Cửa',
                            data: closePrices,
                            borderColor: '#00e5ff',
                            borderWidth: 2,
                            pointRadius: 0,
                            tension: 0.1
                        },
                        {
                            label: 'Đường MA50',
                            data: ma50,
                            borderColor: '#8a2be2',
                            borderWidth: 1.5,
                            borderDash: [5, 5],
                            pointRadius: 0,
                            tension: 0.1
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            labels: { color: '#ffffff' }
                        },
                        tooltip: {
                            mode: 'index',
                            intersect: false,
                            backgroundColor: 'rgba(15, 18, 23, 0.95)',
                            titleColor: '#00e5ff',
                            bodyColor: '#ffffff',
                            borderColor: 'rgba(255, 255, 255, 0.1)',
                            borderWidth: 1
                        }
                    },
                    scales: {
                        x: {
                            grid: { color: 'rgba(255, 255, 255, 0.03)' },
                            ticks: { color: '#a0aec0', maxTicksLimit: 10 }
                        },
                        y: {
                            grid: { color: 'rgba(255, 255, 255, 0.03)' },
                            ticks: { color: '#a0aec0' }
                        }
                    }
                }
            });

        } catch (err) {
            console.error("Error drawing modal chart:", err);
        }
    }

    // --- 11. EXCEL AND FILE EXPORTS INTEGRATION ---
    document.getElementById("btn-export-market").addEventListener("click", () => {
        window.location.href = `/api/export/market?source=${appSource.value}`;
        showNotification("Đã bắt đầu tải tệp Excel phân tích ngành...", "emerald");
    });
    
    document.getElementById("btn-export-scan").addEventListener("click", () => {
        window.location.href = "/api/export/scan";
        showNotification("Đã tải báo cáo quét dạng CSV thành công!", "emerald");
    });
    
    document.getElementById("btn-export-anti").addEventListener("click", () => {
        window.location.href = "/api/export/antigravity";
        showNotification("Đã tải tệp Excel tín hiệu Antigravity...", "emerald");
    });
    
    document.getElementById("btn-export-watch").addEventListener("click", () => {
        window.location.href = "/api/export/watchlist";
        showNotification("Đã tải tệp Excel danh mục Watchlist...", "emerald");
    });

    document.getElementById("btn-export-backtest").addEventListener("click", () => {
        const symbol = document.getElementById("bt-ticker").value;
        const start = document.getElementById("bt-start").value;
        const end = document.getElementById("bt-end").value;
        const cap = document.getElementById("bt-capital").value;
        const pos = document.getElementById("bt-pos-size").value;
        const rsiVal = document.getElementById("bt-rsi-period").value;
        const buyVal = document.getElementById("bt-buy-th").value;
        const sellVal = document.getElementById("bt-sell-th").value;
        const sl = document.getElementById("bt-sl").value;
        const tp = document.getElementById("bt-tp").value;
        
        window.location.href = `/api/export/backtest?symbol=${symbol}&start_date=${start}&end_date=${end}&initial_capital=${cap}&position_size=${pos}&rsi_period=${rsiVal}&buy_threshold=${buyVal}&sell_threshold=${sellVal}&stop_loss=${sl}&take_profit=${tp}`;
        showNotification(`Đã xuất và tải báo cáo giao dịch ${symbol}!`, "emerald");
    });

    // --- 11.5 NEW: VỐN HÓA (MARKET CAP ANALYZER) ---
    const btnLoadCap = document.getElementById("btn-load-cap");
    const btnExportCap = document.getElementById("btn-export-cap");
    const capDateInput = document.getElementById("cap-date");
    const filterCapIndustry = document.getElementById("filter-cap-industry");
    const searchCap = document.getElementById("search-cap");
    
    // Range controls DOM bindings
    const capMode = document.getElementById("cap-mode");
    const capSingleControls = document.getElementById("cap-single-controls");
    const capRangeControls = document.getElementById("cap-range-controls");
    const capStartDateInput = document.getElementById("cap-start-date");
    const capEndDateInput = document.getElementById("cap-end-date");
    const capSingleVisuals = document.getElementById("cap-single-visuals");
    const capRangeVisuals = document.getElementById("cap-range-visuals");
    const capRangeTableBody = document.getElementById("cap-range-table-body");

    // Add change listener to toggle Single / Range controls and displays
    if (capMode) {
        capMode.addEventListener("change", () => {
            const mode = capMode.value;
            if (mode === "single") {
                capSingleControls.style.display = "flex";
                capRangeControls.style.display = "none";
                capSingleVisuals.style.display = "grid";
                capRangeVisuals.style.display = "none";
            } else {
                capSingleControls.style.display = "none";
                capRangeControls.style.display = "flex";
                capSingleVisuals.style.display = "none";
                capRangeVisuals.style.display = "block";
            }
        });
    }
    
    let currentMarketCapData = [];
    let capInterval = null;
    let capRangeInterval = null;
    let rangeDataCache = null;



    btnLoadCap.addEventListener("click", () => {
        loadMarketCapData();
    });

    filterCapIndustry.addEventListener("change", () => {
        renderMarketCapTable(currentMarketCapData);
    });

    searchCap.addEventListener("input", () => {
        renderMarketCapTable(currentMarketCapData);
    });

    btnExportCap.addEventListener("click", () => {
        const mode = capMode.value;
        if (mode === "single") {
            const date = capDateInput.value;
            window.location.href = `/api/export/market-cap?date=${date}`;
            showNotification(`Đang xuất và tải báo cáo vốn hóa phiên ${date}!`, "emerald");
        } else {
            const start = capStartDateInput.value;
            const end = capEndDateInput.value;
            window.location.href = `/api/export/market-cap-range?start_date=${start}&end_date=${end}`;
            showNotification(`Đang xuất báo cáo vốn hóa từ ngày ${start} đến ${end}...`, "emerald");
        }
    });

    async function loadMarketCapData() {
        const mode = capMode.value;
        if (mode === "single") {
            await loadMarketCapSingle();
        } else {
            await loadMarketCapRange();
        }
    }
    
    capDateInput.addEventListener("change", () => {
        loadMarketCapData();
    });
    
    document.getElementById("btn-sync-cap").addEventListener("click", startSyncProcess);
    
    let isSyncing = false;
    let syncInterval = null;
    
    async function startSyncProcess() {
        if (isSyncing) return;
        isSyncing = true;
        
        const btnLiq = document.getElementById("btn-sync-liq");
        const btnCap = document.getElementById("btn-sync-cap");
        const btnVolCap = document.getElementById("btn-sync-vol-cap");
        btnLiq.disabled = true;
        btnCap.disabled = true;
        if (btnVolCap) btnVolCap.disabled = true;
        
        const progLiq = document.getElementById("liq-progress-wrapper");
        const progCap = document.getElementById("cap-progress-wrapper");
        progLiq.style.display = "block";
        progCap.style.display = "block";
        
        try {
            await fetch("/api/sync/start", { method: "POST" });
            
            syncInterval = setInterval(async () => {
                const res = await fetch("/api/sync/status");
                const status = await res.json();
                
                const pct = status.progress || 0;
                document.getElementById("liq-progress-bar").style.width = pct + "%";
                document.getElementById("cap-progress-bar").style.width = pct + "%";
                
                document.getElementById("liq-progress-text").textContent = `Đang đồng bộ Data: ${pct.toFixed(0)}%`;
                document.getElementById("cap-progress-text").textContent = `Đang đồng bộ Data: ${pct.toFixed(0)}%`;
                if (document.getElementById("cap-progress-indicator")) {
                    document.getElementById("cap-progress-indicator").textContent = `${pct.toFixed(0)}%`;
                }
                
                if (!status.running) {
                    clearInterval(syncInterval);
                    isSyncing = false;
                    btnLiq.disabled = false;
                    btnCap.disabled = false;
                    if (btnVolCap) btnVolCap.disabled = false;
                    progLiq.style.display = "none";
                    progCap.style.display = "none";
                    showNotification("Đồng bộ dữ liệu 3 năm hoàn tất!", "emerald");
                }
            }, 1000);
        } catch (e) {
            console.error(e);
            isSyncing = false;
            btnLiq.disabled = false;
            btnCap.disabled = false;
            if (btnVolCap) btnVolCap.disabled = false;
        }
    }
    

    async function loadMarketCapSingle() {
        const date = capDateInput.value;
        const totalVal = document.getElementById("cap-total-value");
        const leader = document.getElementById("cap-leader-ticker");
        const avgVal = document.getElementById("cap-avg-value");
        const progressIndicator = document.getElementById("cap-progress-indicator");
        const leaderboard = document.getElementById("cap-leaderboard");
        
        const progressWrapper = document.getElementById("cap-progress-wrapper");
        const progressBar = document.getElementById("cap-progress-bar");
        const progressText = document.getElementById("cap-progress-text");

        if (capInterval) {
            clearInterval(capInterval);
            capInterval = null;
        }

        leaderboard.innerHTML = `
            <div class="loading-state">
                <i class="fa-solid fa-circle-notch fa-spin"></i>
                <p>Đang quét và tính toán vốn hóa thực tế của 302 doanh nghiệp...</p>
            </div>`;

        progressWrapper.style.display = "block";
        progressBar.style.width = "0%";
        progressText.textContent = "Khởi tạo tiến trình quét vốn hóa... (0%)";
        progressIndicator.textContent = "0%";

        btnLoadCap.disabled = true;
        btnLoadCap.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Đang quét...';
        btnExportCap.disabled = true;

        try {
            const startRes = await fetch(`/api/market-cap/start?date=${date}`, { method: "POST" });
            const startData = await startRes.json();
            
            capInterval = setInterval(async () => {
                try {
                    const statusRes = await fetch("/api/market-cap/status");
                    const status = await statusRes.json();
                    
                    const progress = status.progress || 0;
                    progressBar.style.width = `${progress}%`;
                    progressIndicator.textContent = `${progress.toFixed(0)}%`;
                    
                    if (status.running) {
                        progressText.textContent = `Đang quét: ${progress.toFixed(0)}% (Mã ${status.current}/${status.total})`;
                    } else {
                        progressText.textContent = `Quét hoàn thành 100%!`;
                        progressBar.style.width = "100%";
                        progressIndicator.textContent = "100%";
                        
                        clearInterval(capInterval);
                        capInterval = null;
                        
                        const resultsRes = await fetch("/api/market-cap/results");
                        const data = await resultsRes.json();
                        
                        btnLoadCap.disabled = false;
                        btnLoadCap.innerHTML = '<i class="fa-solid fa-arrows-rotate"></i> Quét Vốn Hóa';
                        progressWrapper.style.display = "none";
                        btnExportCap.disabled = false;
                        
                        if (data.error) {
                            showNotification(`Lỗi nạp vốn hóa: ${data.error}`, "red");
                            leaderboard.innerHTML = `<div class="loading-state text-red"><p>${data.error}</p></div>`;
                            return;
                        }
                        
                        currentMarketCapData = data.results || [];
                        showNotification(`Tính toán vốn hóa thành công cho ngày ${date}!`, "emerald");
                        
                        // 1. Summary Cards
                        let totalSum = 0;
                        currentMarketCapData.forEach(item => totalSum += item.MarketCapBillion);
                        totalVal.textContent = `${totalSum.toLocaleString(undefined, {maximumFractionDigits: 0})} tỷ VND`;
                        
                        const topTicker = currentMarketCapData[0] ? currentMarketCapData[0].Ticker : "N/A";
                        leader.textContent = topTicker;
                        
                        const avg = currentMarketCapData.length > 0 ? (totalSum / currentMarketCapData.length) : 0;
                        if (avgVal) {
                            avgVal.textContent = `${avg.toLocaleString(undefined, {maximumFractionDigits: 1})} tỷ VND`;
                        }
                        
                        // 2. Industry Filters
                        loadCapSectorFilter(data.industries_summary);
                        
                        // 3. Render Leaderboard
                        renderMarketCapLeaderboard(currentMarketCapData, leaderboard);
                        
                        // 4. Bar Chart
                        drawMarketCapChart(data.top_10);
                        
                        // 5. Data Table
                        renderMarketCapTable(currentMarketCapData);
                    }
                } catch (err) {
                    console.error("Error polling market cap status:", err);
                    clearInterval(capInterval);
                    capInterval = null;
                    btnLoadCap.disabled = false;
                    btnLoadCap.innerHTML = '<i class="fa-solid fa-arrows-rotate"></i> Quét Vốn Hóa';
                    progressWrapper.style.display = "none";
                }
            }, 1000);

        } catch (err) {
            console.error("Error starting market cap scan:", err);
            btnLoadCap.disabled = false;
            btnLoadCap.innerHTML = '<i class="fa-solid fa-arrows-rotate"></i> Quét Vốn Hóa';
            progressWrapper.style.display = "none";
        }
    }

    async function loadMarketCapRange() {
        const start = capStartDateInput.value;
        const end = capEndDateInput.value;
        
        const totalVal = document.getElementById("cap-total-value");
        const leader = document.getElementById("cap-leader-ticker");
        const totalLiq = document.getElementById("cap-total-liquidity");
        const liqLeader = document.getElementById("cap-liquidity-leader");
        const progressIndicator = document.getElementById("cap-progress-indicator");
        
        const progressWrapper = document.getElementById("cap-progress-wrapper");
        const progressBar = document.getElementById("cap-progress-bar");
        const progressText = document.getElementById("cap-progress-text");

        if (capRangeInterval) {
            clearInterval(capRangeInterval);
            capRangeInterval = null;
        }

        capRangeTableBody.innerHTML = `
            <tr>
                <td colspan="5" class="text-center text-muted">
                    <i class="fa-solid fa-circle-notch fa-spin text-purple" style="margin-right: 5px;"></i> Đang tính toán dữ liệu tổng hợp theo khoảng thời gian...
                </td>
            </tr>`;

        progressWrapper.style.display = "block";
        progressBar.style.width = "0%";
        progressText.textContent = "Khởi tạo tiến trình quét khoảng thời gian... (0%)";
        progressIndicator.textContent = "0%";

        btnLoadCap.disabled = true;
        btnLoadCap.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Đang quét...';
        btnExportCap.disabled = true;

        try {
            const startRes = await fetch(`/api/market-cap-range/start?start_date=${start}&end_date=${end}`, { method: "POST" });
            
            capRangeInterval = setInterval(async () => {
                try {
                    const statusRes = await fetch("/api/market-cap-range/status");
                    const status = await statusRes.json();
                    
                    const progress = status.progress || 0;
                    progressBar.style.width = `${progress}%`;
                    progressIndicator.textContent = `${progress.toFixed(0)}%`;
                    
                    if (status.running) {
                        progressText.textContent = `Đang quét: ${progress.toFixed(0)}% (Ngày ${status.current}/${status.total})`;
                    } else {
                        progressText.textContent = `Quét hoàn thành 100%!`;
                        progressBar.style.width = "100%";
                        progressIndicator.textContent = "100%";
                        
                        clearInterval(capRangeInterval);
                        capRangeInterval = null;
                        
                        const resultsRes = await fetch("/api/market-cap-range/results");
                        const data = await resultsRes.json();
                        
                        btnLoadCap.disabled = false;
                        btnLoadCap.innerHTML = '<i class="fa-solid fa-arrows-rotate"></i> Quét Vốn Hóa';
                        progressWrapper.style.display = "none";
                        btnExportCap.disabled = false;
                        
                        if (data.error) {
                            showNotification(`Lỗi quét khoảng: ${data.error}`, "red");
                            capRangeTableBody.innerHTML = `<tr><td colspan="5" class="text-center text-red">${data.error}</td></tr>`;
                            return;
                        }
                        
                        rangeDataCache = data;
                        const daily = data.daily_summaries || [];
                        showNotification(`Quét vốn hóa & thanh khoản phiên ${start} đến ${end} hoàn tất!`, "emerald");
                        
                        if (daily.length === 0) {
                            capRangeTableBody.innerHTML = `<tr><td colspan="5" class="text-center text-muted">Không tìm thấy dữ liệu.</td></tr>`;
                            return;
                        }
                        
                        // 1. Update overall cards with latest day stats
                        const latest = daily[0];
                        totalVal.textContent = `${latest.TotalCapBillion.toLocaleString()} tỷ VND`;
                        leader.textContent = latest.LeaderTicker;
                        totalLiq.textContent = `${latest.TotalLiquidityBillion.toLocaleString()} tỷ VND`;
                        liqLeader.textContent = latest.LiquidityLeaderTicker;
                        
                        // 2. Draw line trend chart
                        drawMarketCapTrendChart(daily);
                        
                        // 3. Populate daily summaries table
                        renderMarketCapRangeTable(daily);
                        
                        // 4. By default, auto-select and display detail list of the latest day in the range!
                        if (data.latest_results && data.latest_results.length > 0) {
                            currentMarketCapData = data.latest_results;
                            
                            // Re-calculate sector filters based on latest day
                            const indMap = {};
                            data.latest_results.forEach(r => {
                                if (!indMap[r.Industry]) indMap[r.Industry] = 0;
                                indMap[r.Industry]++;
                            });
                            const indList = Object.keys(indMap).map(k => ({ Industry: k, Count: indMap[k] }));
                            loadCapSectorFilter(indList);
                            
                            renderMarketCapTable(currentMarketCapData);
                        }

                        // Add dynamic axis selector listener
                        const axisSelect = document.getElementById("chart-y-axis-select");
                        const newAxisSelect = axisSelect.cloneNode(true);
                        axisSelect.parentNode.replaceChild(newAxisSelect, axisSelect);
                        newAxisSelect.addEventListener("change", () => {
                            drawMarketCapTrendChart(daily);
                        });
                    }
                } catch (err) {
                    console.error("Error polling range status:", err);
                    clearInterval(capRangeInterval);
                    capRangeInterval = null;
                    btnLoadCap.disabled = false;
                    btnLoadCap.innerHTML = '<i class="fa-solid fa-arrows-rotate"></i> Quét Vốn Hóa';
                    progressWrapper.style.display = "none";
                }
            }, 1000);

        } catch (err) {
            console.error("Error starting range scan:", err);
            btnLoadCap.disabled = false;
            btnLoadCap.innerHTML = '<i class="fa-solid fa-arrows-rotate"></i> Quét Vốn Hóa';
            progressWrapper.style.display = "none";
        }
    }

    function drawMarketCapTrendChart(daily) {
        const ctx = document.getElementById("market-cap-trend-chart").getContext("2d");
        
        if (state.charts.marketCap) {
            state.charts.marketCap.destroy();
        }

        if (!daily || daily.length === 0) return;

        const labels = daily.map(item => item.Date);
        const caps = daily.map(item => item.TotalCapBillion);
        const liqs = daily.map(item => item.TotalLiquidityBillion || 0);

        const mode = document.getElementById("chart-y-axis-select") ? document.getElementById("chart-y-axis-select").value : "both";

        const datasets = [];
        const yScales = {
            x: {
                grid: { color: 'rgba(255, 255, 255, 0.02)' },
                ticks: { color: '#a0aec0', maxRotation: 45, minRotation: 45 }
            }
        };

        if (mode === "both" || mode === "cap") {
            datasets.push({
                label: 'Tổng Vốn Hóa (Tỷ VND)',
                data: caps,
                fill: true,
                backgroundColor: 'rgba(138, 43, 226, 0.04)',
                borderColor: '#8a2be2',
                borderWidth: 2,
                pointBackgroundColor: '#8a2be2',
                pointBorderColor: 'rgba(255, 255, 255, 0.2)',
                pointRadius: 3,
                tension: 0.2,
                yAxisID: 'y'
            });
            yScales.y = {
                type: 'linear',
                position: 'left',
                grid: { color: 'rgba(255, 255, 255, 0.02)' },
                ticks: {
                    color: '#8a2be2',
                    callback: function(value) { return value.toLocaleString() + ' Tỷ'; }
                },
                title: {
                    display: true,
                    text: 'Vốn Hóa (Tỷ VND)',
                    color: '#8a2be2'
                }
            };
        }

        if (mode === "both" || mode === "liq") {
            datasets.push({
                label: 'Tổng Thanh Khoản (Tỷ VND)',
                data: liqs,
                fill: true,
                backgroundColor: 'rgba(0, 229, 255, 0.04)',
                borderColor: '#00e5ff',
                borderWidth: 2,
                pointBackgroundColor: '#00e5ff',
                pointBorderColor: 'rgba(255, 255, 255, 0.2)',
                pointRadius: 3,
                tension: 0.2,
                yAxisID: mode === "both" ? 'y1' : 'y'
            });
            
            const targetY = mode === "both" ? 'y1' : 'y';
            yScales[targetY] = {
                type: 'linear',
                position: mode === "both" ? 'right' : 'left',
                grid: { drawOnChartArea: mode !== "both", color: 'rgba(255, 255, 255, 0.02)' },
                ticks: {
                    color: '#00e5ff',
                    callback: function(value) { return value.toLocaleString() + ' Tỷ'; }
                },
                title: {
                    display: true,
                    text: 'Thanh Khoản (Tỷ VND)',
                    color: '#00e5ff'
                }
            };
        }

        state.charts.marketCap = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                plugins: {
                    legend: {
                        display: true,
                        labels: { color: '#a0aec0', boxWidth: 12 }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(15, 18, 23, 0.95)',
                        titleColor: '#ffffff',
                        bodyColor: '#ffffff',
                        borderColor: 'rgba(255, 255, 255, 0.1)',
                        borderWidth: 1,
                        padding: 10,
                        callbacks: {
                            label: function(context) {
                                const index = context.dataIndex;
                                const item = daily[index];
                                if (context.dataset.label.includes("Vốn Hóa")) {
                                    return [
                                        `Tổng Vốn Hóa: ${item.TotalCapBillion.toLocaleString()} Tỷ VND`,
                                        `Dẫn đầu Cap: ${item.LeaderTicker} (${item.LeaderCapBillion.toLocaleString()} Tỷ)`
                                    ];
                                } else {
                                    return [
                                        `Tổng Thanh Khoản: ${item.TotalLiquidityBillion.toLocaleString()} Tỷ VND`,
                                        `Khớp nhất: ${item.LiquidityLeaderTicker} (${item.LiquidityLeaderBillion.toLocaleString()} Tỷ)`
                                    ];
                                }
                            }
                        }
                    }
                },
                scales: yScales
            }
        });
    }

    function renderMarketCapRangeTable(daily) {
        const body = document.getElementById("cap-range-table-body");
        body.innerHTML = "";
        
        daily.forEach((item, index) => {
            const tr = document.createElement("tr");
            tr.className = "clickable-row";
            tr.style.cursor = "pointer";
            
            tr.addEventListener("click", () => {
                body.querySelectorAll("tr").forEach(r => r.classList.remove("row-active"));
                tr.classList.add("row-active");
                loadDetailForDate(item.Date);
            });

            tr.innerHTML = `
                <td><strong>${item.Date}</strong></td>
                <td class="text-purple font-weight-bold">${item.TotalCapBillion.toLocaleString()} tỷ</td>
                <td class="text-cyan font-weight-bold">${(item.TotalLiquidityBillion || 0).toLocaleString()} tỷ</td>
                <td><span class="badge badge-purple">${item.LeaderTicker}</span></td>
                <td><span class="badge badge-cyan">${item.LiquidityLeaderTicker || 'N/A'}</span></td>
            `;
            body.appendChild(tr);
        });
    }

    function loadDetailForDate(date) {
        if (!rangeDataCache || !rangeDataCache.details_by_date) return;
        
        const details = rangeDataCache.details_by_date[date] || [];
        currentMarketCapData = details;
        
        showNotification(`Đã tải chi tiết vốn hóa & thanh khoản phiên ${date}!`, "purple");
        
        const totalVal = document.getElementById("cap-total-value");
        const leader = document.getElementById("cap-leader-ticker");
        const totalLiq = document.getElementById("cap-total-liquidity");
        const liqLeader = document.getElementById("cap-liquidity-leader");
        const progressIndicator = document.getElementById("cap-progress-indicator");
        
        let totalSum = 0;
        let totalLiqSum = 0;
        
        details.forEach(item => {
            totalSum += item.MarketCapBillion;
            totalLiqSum += (item.LiquidityBillion || 0);
        });
        
        totalVal.textContent = `${totalSum.toLocaleString(undefined, {maximumFractionDigits: 0})} tỷ VND`;
        
        const topTicker = details[0] ? details[0].Ticker : "N/A";
        leader.textContent = topTicker;
        
        totalLiq.textContent = `${totalLiqSum.toLocaleString(undefined, {maximumFractionDigits: 1})} tỷ VND`;
        
        const liqSorted = [...details].sort((a, b) => (b.LiquidityBillion || 0) - (a.LiquidityBillion || 0));
        const topLiqTicker = liqSorted[0] ? liqSorted[0].Ticker : "N/A";
        liqLeader.textContent = topLiqTicker;
        
        progressIndicator.textContent = "100%";
        
        const indMap = {};
        details.forEach(r => {
            if (!indMap[r.Industry]) indMap[r.Industry] = 0;
            indMap[r.Industry]++;
        });
        const indList = Object.keys(indMap).map(k => ({ Industry: k, Count: indMap[k] }));
        loadCapSectorFilter(indList);

        renderMarketCapTable(details);
    }

    function loadCapSectorFilter(summary) {
        if (!summary) return;
        const currentVal = filterCapIndustry.value;
        filterCapIndustry.innerHTML = '<option value="All">Tất cả ngành</option>';
        summary.forEach(s => {
            const opt = document.createElement("option");
            opt.value = s.Industry;
            opt.textContent = `${s.Industry} (${s.Count})`;
            filterCapIndustry.appendChild(opt);
        });
        filterCapIndustry.value = currentVal;
    }

    function renderMarketCapLeaderboard(list, container) {
        if (list.length === 0) {
            container.innerHTML = `<p class="text-center text-muted">Không có dữ liệu.</p>`;
            return;
        }

        const top10 = list.slice(0, 10);
        const maxVal = top10[0] ? top10[0].MarketCapBillion : 1;

        container.innerHTML = "";
        top10.forEach((item, index) => {
            const row = document.createElement("div");
            row.className = "leaderboard-row";
            row.addEventListener("click", () => openTickerChart(item.Ticker));

            const rank = index + 1;
            const progressPct = (item.MarketCapBillion / maxVal) * 100;

            row.innerHTML = `
                <div class="leaderboard-rank rank-${rank <= 3 ? rank : 'other'}">${rank}</div>
                <div class="leaderboard-ticker">${item.Ticker}</div>
                <div class="leaderboard-bar-area">
                    <div class="leaderboard-label-row">
                        <span class="text-muted">${item.Industry}</span>
                        <span class="leaderboard-value" style="color: #a78bfa;">${item.MarketCapBillion.toLocaleString(undefined, {maximumFractionDigits: 1})} Tỷ VND</span>
                    </div>
                    <div class="leaderboard-bar-container">
                        <div class="leaderboard-bar" style="width: ${progressPct}%; background-color: var(--accent-purple);"></div>
                    </div>
                </div>
            `;
            container.appendChild(row);
        });
    }

    function drawMarketCapChart(top10) {
        const ctx = document.getElementById("market-cap-chart").getContext("2d");
        
        if (state.charts.marketCap) {
            state.charts.marketCap.destroy();
        }

        if (!top10 || top10.length === 0) return;

        const labels = top10.map(item => item.Ticker);
        const values = top10.map(item => item.MarketCapBillion);

        state.charts.marketCap = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Vốn hóa thị trường (Tỷ VND)',
                    data: values,
                    backgroundColor: 'rgba(138, 43, 226, 0.45)',
                    borderColor: '#8a2be2',
                    borderWidth: 1.5,
                    borderRadius: 4,
                    hoverBackgroundColor: 'rgba(138, 43, 226, 0.7)',
                    hoverBorderColor: '#8a2be2'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: 'rgba(15, 18, 23, 0.95)',
                        titleColor: '#8a2be2',
                        bodyColor: '#ffffff',
                        borderColor: 'rgba(255, 255, 255, 0.1)',
                        borderWidth: 1,
                        padding: 10,
                        callbacks: {
                            label: function(context) {
                                return `Vốn hóa: ${context.parsed.y.toLocaleString()} Tỷ VND`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { color: 'rgba(255, 255, 255, 0.03)' },
                        ticks: { color: '#a0aec0' }
                    },
                    y: {
                        grid: { color: 'rgba(255, 255, 255, 0.03)' },
                        ticks: {
                            color: '#a0aec0',
                            callback: function(value) {
                                return value.toLocaleString() + ' Tỷ';
                            }
                        }
                    }
                }
            }
        });
    }

    function renderMarketCapTable(list) {
        const tableBody = document.getElementById("cap-table-body");
        const selectedSec = filterCapIndustry.value;
        const query = searchCap.value.toUpperCase().trim();
        
        let filtered = list;
        if (selectedSec !== "All") {
            filtered = list.filter(item => item.Industry === selectedSec);
        }
        if (query) {
            filtered = filtered.filter(item => item.Ticker.includes(query));
        }

        if (filtered.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="8" class="text-center text-muted">Không tìm thấy cổ phiếu phù hợp.</td></tr>`;
            return;
        }

        const top1Val = list[0] ? list[0].MarketCapBillion : 1;

        tableBody.innerHTML = "";
        filtered.forEach((item, idx) => {
            const tr = document.createElement("tr");
            tr.className = "clickable-row";
            tr.addEventListener("click", () => openTickerChart(item.Ticker));

            const val = item.MarketCapBillion || 0;
            const pctOfTop1 = (val / top1Val) * 100;
            const liqVal = item.LiquidityBillion || 0;
            
            let badgeClass = "badge-red";
            let bracketText = "Small Cap";
            if (val > 100000) { badgeClass = "badge-green"; bracketText = "Mega Cap"; }
            else if (val > 30000) { badgeClass = "badge-cyan"; bracketText = "Large Cap"; }
            else if (val > 10000) { badgeClass = "badge-purple"; bracketText = "Mid Cap"; }

            tr.innerHTML = `
                <td class="text-center font-weight-bold">${idx + 1}</td>
                <td><strong>${item.Ticker}</strong></td>
                <td><span class="badge badge-purple">${item.Industry}</span></td>
                <td>${(item.Close || 0).toLocaleString()}</td>
                <td>${(item.OutstandingShares || 0).toLocaleString()}</td>
                <td class="text-purple font-weight-bold">${val.toLocaleString(undefined, {minimumFractionDigits: 1, maximumFractionDigits: 1})} Tỷ</td>
                <td class="text-cyan font-weight-bold">${liqVal.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})} Tỷ</td>
                <td style="vertical-align: middle;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span class="text-muted" style="font-size: 11px; width: 35px; text-align: right;">${pctOfTop1.toFixed(0)}%</span>
                        <div class="leaderboard-bar-container" style="flex-grow: 1; height: 5px;">
                            <div class="leaderboard-bar" style="width: ${pctOfTop1}%; background-color: var(--accent-purple);"></div>
                        </div>
                    </div>
                </td>
            `;
            tableBody.appendChild(tr);
        });
    }

    // --- 12. UTILS: Sleek Visual Notifications ---
    function showNotification(msg, type = "cyan") {
        // Create slick element
        const note = document.createElement("div");
        note.style.position = "fixed";
        note.style.bottom = "24px";
        note.style.right = "24px";
        note.style.padding = "12px 24px";
        note.style.borderRadius = "10px";
        note.style.zIndex = "9999";
        note.style.fontSize = "13px";
        note.style.fontWeight = "600";
        note.style.display = "flex";
        note.style.alignItems = "center";
        note.style.gap = "10px";
        note.style.boxShadow = "0 10px 20px rgba(0,0,0,0.4)";
        note.style.animation = "note-slide-in 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)";
        note.style.backdropFilter = "blur(10px)";
        note.style.webkitBackdropFilter = "blur(10px)";
        
        let colorHex = "#00e5ff";
        let icon = "fa-circle-info";
        
        if (type === "red") { colorHex = "#ef5350"; icon = "fa-circle-exclamation"; }
        else if (type === "emerald") { colorHex = "#26a69a"; icon = "fa-circle-check"; }
        else if (type === "purple") { colorHex = "#8a2be2"; icon = "fa-bolt-lightning"; }

        note.style.color = "#ffffff";
        note.style.backgroundColor = "rgba(18, 22, 29, 0.9)";
        note.style.border = `1px solid ${colorHex}`;
        
        note.innerHTML = `<i class="fa-solid ${icon}" style="color: ${colorHex}; font-size: 16px;"></i> <span>${msg}</span>`;
        document.body.appendChild(note);
        
        // Add CSS keyframe locally if not already done
        if (!document.getElementById("note-keyframes")) {
            const style = document.createElement("style");
            style.id = "note-keyframes";
            style.innerHTML = `
                @keyframes note-slide-in {
                    from { transform: translateY(40px); opacity: 0; }
                    to { transform: translateY(0); opacity: 1; }
                }
            `;
            document.head.appendChild(style);
        }

        setTimeout(() => {
            note.style.transition = "opacity 0.3s ease, transform 0.3s ease";
            note.style.opacity = "0";
            note.style.transform = "translateY(15px)";
            setTimeout(() => note.remove(), 300);
        }, 3500);
    }

    // Initialize Default view
    fetchHeatmapData();

    // --- 11.6 NEW: OUTSTANDING SHARES CRAWLER STATUS MONITOR ---
    let crawlerInterval = null;
    async function updateSharesCrawlerStatus() {
        const icon = document.getElementById("shares-crawler-icon");
        const text = document.getElementById("shares-crawler-text");
        const box = document.getElementById("shares-crawler-status-box");
        if (!icon || !text || !box) return;

        try {
            const res = await fetch("/api/shares-crawler/status");
            const data = await res.json();

            // Resume polling if crawler is active but we are not polling
            if (!data.completed && !crawlerInterval) {
                crawlerInterval = setInterval(updateSharesCrawlerStatus, 5000);
            }

            if (data.completed) {
                icon.className = "fa-solid fa-circle-check text-emerald";
                box.style.background = "rgba(16, 185, 129, 0.08)";
                box.style.borderColor = "rgba(16, 185, 129, 0.3)";
                text.innerHTML = `CP lưu hành: <span class="text-emerald">Đã đồng bộ 100% (302/302 mã)</span>`;
                if (crawlerInterval) {
                    clearInterval(crawlerInterval);
                    crawlerInterval = null;
                }
            } else if (data.running) {
                icon.className = "fa-solid fa-spinner fa-spin text-cyan";
                box.style.background = "rgba(0, 229, 255, 0.05)";
                box.style.borderColor = "rgba(0, 229, 255, 0.15)";
                text.innerHTML = `Đang đồng bộ CP lưu hành: <span class="text-cyan font-weight-bold">${data.progress}%</span> (${data.current}/${data.total} mã)...`;
            } else {
                icon.className = "fa-solid fa-circle-info text-amber";
                box.style.background = "rgba(245, 158, 11, 0.05)";
                box.style.borderColor = "rgba(245, 158, 11, 0.15)";
                text.innerHTML = `CP lưu hành: Đang cào (${data.current}/${data.total} mã)...`;
            }
        } catch (e) {
            console.error("Error updating shares crawler status:", e);
        }
    }

    // Start polling shares crawler status
    updateSharesCrawlerStatus();
    crawlerInterval = setInterval(updateSharesCrawlerStatus, 5000);

    // Event listener for outstanding shares force-sync restart
    const btnSyncShares = document.getElementById("btn-sync-shares");
    if (btnSyncShares) {
        btnSyncShares.addEventListener("click", async (e) => {
            e.stopPropagation();
            if (!confirm("Bạn có chắc chắn muốn làm sạch cache và đồng bộ lại từ đầu số lượng CP lưu hành của tất cả 302 mã doanh nghiệp không?")) {
                return;
            }
            btnSyncShares.disabled = true;
            const refreshIcon = btnSyncShares.querySelector("i");
            refreshIcon.classList.add("fa-spin");
            
            try {
                const res = await fetch("/api/shares-crawler/restart", { method: "POST" });
                const data = await res.json();
                if (data.status === "started") {
                    showNotification("Bắt đầu quét và đồng bộ lại 100% số lượng CP lưu hành!", "cyan");
                    // Trigger immediate poll
                    await updateSharesCrawlerStatus();
                } else {
                    showNotification("Bộ quét hiện đang bận hoặc đang chạy!", "amber");
                }
            } catch (err) {
                console.error("Error restarting shares crawler:", err);
                showNotification("Không thể khởi động lại bộ quét!", "red");
            } finally {
                btnSyncShares.disabled = false;
                refreshIcon.classList.remove("fa-spin");
            }
        });
    }

    // --- 11.6 NEW: VOL/CAP RATIO ANALYZER ---
    const btnLoadVolCap = document.getElementById("btn-load-vol-cap");
    const btnSyncVolCap = document.getElementById("btn-sync-vol-cap");
    const btnExportVolCap3y = document.getElementById("btn-export-vol-cap-3y");
    const volCapDateInput = document.getElementById("vol-cap-date");
    const filterVolCapIndustry = document.getElementById("filter-vol-cap-industry");
    const searchVolCap = document.getElementById("search-vol-cap");
    
    let currentVolCapData = [];

    if (btnLoadVolCap) {
        btnLoadVolCap.addEventListener("click", () => {
            loadVolCapData();
        });
    }

    if (btnSyncVolCap) {
        btnSyncVolCap.addEventListener("click", startSyncProcess);
    }

    if (volCapDateInput) {
        volCapDateInput.addEventListener("change", () => {
            loadVolCapData();
        });
    }

    if (filterVolCapIndustry) {
        filterVolCapIndustry.addEventListener("change", () => {
            renderVolCapTable(currentVolCapData);
        });
    }

    if (searchVolCap) {
        searchVolCap.addEventListener("input", () => {
            renderVolCapTable(currentVolCapData);
        });
    }

    if (btnExportVolCap3y) {
        btnExportVolCap3y.addEventListener("click", () => {
            window.location.href = "/api/export/vol-cap-history";
            showNotification("Đang xuất và tải dữ liệu Vol/Cap 3 năm gần nhất...", "emerald");
        });
    }

    async function loadVolCapData() {
        if (!volCapDateInput) return;
        const date = volCapDateInput.value;
        const totalVal = document.getElementById("vol-cap-total-value");
        const totalLiq = document.getElementById("vol-cap-total-liquidity");
        const avgRatio = document.getElementById("vol-cap-avg-ratio");
        const leader = document.getElementById("vol-cap-leader-ticker");
        const tableBody = document.getElementById("vol-cap-table-body");

        if (tableBody) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="9" class="text-center text-muted">
                        <i class="fa-solid fa-circle-notch fa-spin text-cyan" style="margin-right: 5px;"></i> Đang truy vấn dữ liệu tỷ lệ Vol/Cap...
                    </td>
                </tr>`;
        }

        if (btnLoadVolCap) {
            btnLoadVolCap.disabled = true;
            btnLoadVolCap.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Đang tải...';
        }

        try {
            const res = await fetch(`/api/vol-cap/results?date=${date}`);
            const data = await res.json();

            if (btnLoadVolCap) {
                btnLoadVolCap.disabled = false;
                btnLoadVolCap.innerHTML = '<i class="fa-solid fa-arrows-rotate"></i> Truy Vấn Tức Thì';
            }

            if (data.error) {
                showNotification(`Lỗi nạp Vol/Cap: ${data.error}`, "red");
                if (tableBody) {
                    tableBody.innerHTML = `<tr><td colspan="9" class="text-center text-red">${data.error}</td></tr>`;
                }
                return;
            }

            currentVolCapData = data.results || [];
            showNotification(`Tính toán Vol/Cap thành công cho ngày ${data.date}!`, "emerald");

            // Update date input if date was adjusted to nearest trading date
            if (data.date && volCapDateInput && volCapDateInput.value !== data.date) {
                volCapDateInput.value = data.date;
            }

            // 1. Update Summary Cards
            const summary = data.summary || {};
            if (totalVal) {
                totalVal.textContent = `${summary.total_cap_billion.toLocaleString(undefined, {maximumFractionDigits: 0})} tỷ VND`;
            }
            
            if (totalLiq) {
                const liqVND = summary.total_liquidity_vnd || 0;
                if (liqVND >= 1_000_000_000) {
                    totalLiq.textContent = `${(liqVND / 1_000_000_000).toLocaleString(undefined, {maximumFractionDigits: 1})} tỷ VND`;
                } else {
                    totalLiq.textContent = `${liqVND.toLocaleString(undefined, {maximumFractionDigits: 0})} VND`;
                }
            }
            
            if (avgRatio) {
                avgRatio.textContent = `${summary.avg_vol_cap.toFixed(2)}%`;
            }
            if (leader) {
                leader.textContent = summary.leader_ticker || "N/A";
            }

            // 2. Populate Sector Filter Dropdown
            populateVolCapSectorFilter(data.sectors || []);

            // 3. Render Table
            renderVolCapTable(currentVolCapData);

        } catch (err) {
            console.error("Error loading Vol/Cap data:", err);
            if (btnLoadVolCap) {
                btnLoadVolCap.disabled = false;
                btnLoadVolCap.innerHTML = '<i class="fa-solid fa-arrows-rotate"></i> Truy Vấn Tức Thì';
            }
            if (tableBody) {
                tableBody.innerHTML = `<tr><td colspan="9" class="text-center text-red">Lỗi kết nối máy chủ. Vui lòng thử lại.</td></tr>`;
            }
        }
    }

    function populateVolCapSectorFilter(sectors) {
        if (!filterVolCapIndustry) return;
        const currentVal = filterVolCapIndustry.value;
        filterVolCapIndustry.innerHTML = '<option value="All">Tất cả ngành</option>';
        sectors.forEach(sec => {
            if (sec.Industry && sec.Industry !== "Chưa phân loại") {
                const opt = document.createElement("option");
                opt.value = sec.Industry;
                opt.textContent = `${sec.Industry} (${sec.Count})`;
                filterVolCapIndustry.appendChild(opt);
            }
        });
        if (currentVal && [...filterVolCapIndustry.options].some(o => o.value === currentVal)) {
            filterVolCapIndustry.value = currentVal;
        }
    }

    function renderVolCapTable(data) {
        const tableBody = document.getElementById("vol-cap-table-body");
        if (!tableBody) return;
        
        const selectedSector = filterVolCapIndustry ? filterVolCapIndustry.value : "All";
        const searchQuery = searchVolCap ? searchVolCap.value.trim().toUpperCase() : "";

        // Filter data
        let filtered = data;
        if (selectedSector !== "All") {
            filtered = filtered.filter(item => item.Industry === selectedSector);
        }
        if (searchQuery) {
            filtered = filtered.filter(item => item.Ticker.includes(searchQuery));
        }

        if (filtered.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="9" class="text-center text-muted">Không tìm thấy mã cổ phiếu phù hợp.</td></tr>`;
            return;
        }

        tableBody.innerHTML = filtered.map(item => {
            const rowClass = item.VolCapPct > 2.0 ? 'style="background: rgba(0, 229, 255, 0.04);"' : '';
            return `
                <tr ${rowClass}>
                    <td class="text-center font-bold text-cyan">${item.Rank}</td>
                    <td class="text-center font-bold text-white hover-ticker" style="cursor: pointer;">${item.Ticker}</td>
                    <td>${item.Industry}</td>
                    <td class="text-right">${item.Close.toLocaleString(undefined, {maximumFractionDigits: 0})}</td>
                    <td class="text-right">${item.Volume.toLocaleString(undefined, {maximumFractionDigits: 0})}</td>
                    <td class="text-right text-muted">${item.OutstandingShares.toLocaleString(undefined, {maximumFractionDigits: 0})}</td>
                    <td class="text-right text-emerald">${item.LiquidityVND.toLocaleString(undefined, {maximumFractionDigits: 0})}</td>
                    <td class="text-right text-purple">${item.MarketCapBillion.toLocaleString(undefined, {maximumFractionDigits: 1})}</td>
                    <td class="text-center font-bold text-cyan">${item.VolCapPct.toFixed(2)}%</td>
                </tr>
            `;
        }).join("");

        // Attach click listeners to ticker cells to open technical chart modal
        tableBody.querySelectorAll(".hover-ticker").forEach(cell => {
            cell.addEventListener("click", () => {
                const ticker = cell.textContent;
                if (typeof showTickerModal === "function") {
                    showTickerModal(ticker);
                } else if (typeof window.showTickerModal === "function") {
                    window.showTickerModal(ticker);
                }
            });
        });
    }

    // Expose global function for tab activation
    window.loadVolCapData = loadVolCapData;

});


    let liqRangeInterval = null;
    let liqRangeDataCache = null;

    async function loadLiquidityRange() {
        const start = document.getElementById("liq-start-date").value;
        const end = document.getElementById("liq-end-date").value;
        
        const progressWrapper = document.getElementById("liq-progress-wrapper");
        const progressBar = document.getElementById("liq-progress-bar");
        const progressText = document.getElementById("liq-progress-text");
        
        if (liqRangeInterval) clearInterval(liqRangeInterval);
        
        liqRangeTableBody.innerHTML = `<tr><td colspan="4" class="text-center"><i class="fa-solid fa-spin fa-circle-notch"></i> Đang quét dữ liệu...</td></tr>`;
        progressWrapper.style.display = "block";
        btnLoadLiquidity.disabled = true;
        
        try {
            await fetch(`/api/market-cap-range/start?start_date=${start}&end_date=${end}`, { method: "POST" });
            
            liqRangeInterval = setInterval(async () => {
                const st = await (await fetch("/api/market-cap-range/status")).json();
                progressBar.style.width = `${st.progress || 0}%`;
                progressText.textContent = `Đang quét: ${st.progress || 0}%`;
                
                if (!st.running) {
                    clearInterval(liqRangeInterval);
                    const data = await (await fetch("/api/market-cap-range/results")).json();
                    btnLoadLiquidity.disabled = false;
                    progressWrapper.style.display = "none";
                    
                    if (data.error) {
                        showNotification(data.error, "red");
                        return;
                    }
                    
                    liqRangeDataCache = data;
                    const daily = data.daily_summaries || [];
                    if (daily.length === 0) {
                        liqRangeTableBody.innerHTML = `<tr><td colspan="4" class="text-center">Không tìm thấy dữ liệu.</td></tr>`;
                        return;
                    }
                    
                    showNotification("Quét thanh khoản hoàn tất!", "emerald");
                    
                    // Render range table
                    liqRangeTableBody.innerHTML = daily.map(d => `
                        <tr style="cursor: pointer; transition: 0.2s;" onmouseover="this.style.backgroundColor='rgba(0,229,255,0.1)'" onmouseout="this.style.backgroundColor='transparent'" onclick="loadLiquidityDetailForDate('${d.Date}')">
                            <td>${d.Date}</td>
                            <td class="text-cyan font-weight-bold">${d.TotalLiquidityBillion.toLocaleString()} tỷ</td>
                            <td>${d.LiquidityLeaderTicker}</td>
                            <td class="text-emerald">${d.LiquidityLeaderBillion.toLocaleString()} tỷ</td>
                        </tr>
                    `).join("");
                    
                    // Auto load latest day
                    loadLiquidityDetailForDate(daily[daily.length-1].Date);
                }
            }, 500);
        } catch (e) {
            clearInterval(liqRangeInterval);
            btnLoadLiquidity.disabled = false;
            progressWrapper.style.display = "none";
        }
    }
    
    window.loadLiquidityDetailForDate = function(dateStr) {
        if (!liqRangeDataCache || !liqRangeDataCache.details_by_date) return;
        const details = liqRangeDataCache.details_by_date[dateStr] || [];
        
        // Populate stats
        const totalLiq = details.reduce((sum, item) => sum + item.LiquidityBillion, 0);
        const totalVol = details.reduce((sum, item) => sum + item.Volume, 0);
        
        document.getElementById("liq-total-value").textContent = `${totalLiq.toLocaleString('en-US', {maximumFractionDigits: 0})} tỷ VND`;
        document.getElementById("liq-total-volume").textContent = `${totalVol.toLocaleString()} CP`;
        
        if (details.length > 0) {
            const sorted = [...details].sort((a,b) => b.LiquidityBillion - a.LiquidityBillion);
            document.getElementById("liq-leader-ticker").textContent = sorted[0].Ticker;
            document.getElementById("liq-avg-value").textContent = `${(totalLiq / details.length).toLocaleString('en-US', {maximumFractionDigits: 2})} tỷ VND`;
        }
        
        // Draw charts
        drawLiquidityChart(details);
        renderLiquidityTable(details);
        
        // Show notification to user
        showNotification(`Đang xem chi tiết thanh khoản phiên: ${dateStr}`, "cyan");
    };
