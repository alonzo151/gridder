class GridderDashboard {
    constructor() {
        this.refreshRate = 30;
        this.autoRefresh = true;
        this.refreshTimer = null;
        this.selectedBot = '';
        this.timeFilter = 6;
        
        this.initializeControls();
        this.loadInitialData();
        this.startAutoRefresh();
    }

    initializeControls() {
        const refreshRateSlider = document.getElementById('refresh-rate');
        const refreshRateValue = document.getElementById('refresh-rate-value');
        
        refreshRateSlider.addEventListener('input', (e) => {
            this.refreshRate = parseInt(e.target.value);
            refreshRateValue.textContent = this.refreshRate;
            this.restartAutoRefresh();
        });

        const autoRefreshCheckbox = document.getElementById('auto-refresh');
        autoRefreshCheckbox.addEventListener('change', (e) => {
            this.autoRefresh = e.target.checked;
            this.restartAutoRefresh();
        });

        const refreshButton = document.getElementById('refresh-now');
        refreshButton.addEventListener('click', () => {
            this.refreshData();
        });

        const botSelect = document.getElementById('bot-select');
        botSelect.addEventListener('change', (e) => {
            this.selectedBot = e.target.value;
            this.refreshData();
        });

        const timeFilterSelect = document.getElementById('time-filter');
        timeFilterSelect.addEventListener('change', (e) => {
            this.timeFilter = e.target.value ? parseInt(e.target.value) : null;
            this.refreshData();
        });
    }

    async loadInitialData() {
        await this.loadBotList();
        await this.loadBotConfig();
        await this.refreshData();
    }

    async loadBotList() {
        try {
            const response = await fetch('/api/bots');
            const data = await response.json();
            
            if (data.bots) {
                const botSelect = document.getElementById('bot-select');
                
                botSelect.innerHTML = '<option value="">All Bots</option>';
                
                data.bots.forEach(bot => {
                    const option = document.createElement('option');
                    option.value = bot;
                    option.textContent = bot;
                    botSelect.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Error loading bot list:', error);
        }
    }

    async refreshData() {
        try {
            await Promise.all([
                this.loadTradesData(),
                this.loadStatsData(),
                this.loadOptionsPnlData(),
                this.loadTotalPnlData(),
                this.loadPriceData()
            ]);
            
            this.updateLastUpdatedTime();
        } catch (error) {
            console.error('Error refreshing data:', error);
        }
    }

    async loadTradesData() {
        try {
            let url = this.selectedBot ? `/api/trades?bot_name=${encodeURIComponent(this.selectedBot)}` : '/api/trades';
            
            if (this.timeFilter) {
                url += (url.includes('?') ? '&' : '?') + `hours_filter=${this.timeFilter}`;
            }
            
            const response = await fetch(url);
            const data = await response.json();
            
            if (data.trades) {
                this.updateTradingChart(data.trades);
            }
        } catch (error) {
            console.error('Error loading trades data:', error);
        }
    }

    async loadStatsData() {
        try {
            const url = this.selectedBot ? `/api/stats?bot_name=${encodeURIComponent(this.selectedBot)}` : '/api/stats';
            const response = await fetch(url);
            const data = await response.json();
            
            this.updateStatsCards(data);
        } catch (error) {
            console.error('Error loading stats data:', error);
        }
    }

    updateTradingChart(trades) {
        if (!trades || trades.length === 0) {
            const chartDiv = document.getElementById('trading-chart');
            chartDiv.innerHTML = '<div style="text-align: center; padding: 2rem; color: #999;">No trades data available yet. The chart will update when trades are executed.</div>';
            return;
        }

        const buyTrades = trades.filter(trade => trade.side === 'BUY');
        const sellTrades = trades.filter(trade => trade.side === 'SELL');

        const traces = [];

        if (buyTrades.length > 0) {
            traces.push({
                x: buyTrades.map(trade => new Date(trade.timestamp)),
                y: buyTrades.map(trade => trade.price),
                mode: 'markers',
                marker: {
                    color: 'green',
                    size: 8
                },
                name: 'Buy Trades',
                hovertemplate: '<b>Buy Trade</b><br>' +
                              'Time: %{x}<br>' +
                              'Price: $%{y:.2f}<br>' +
                              'Quantity: %{customdata:.6f}<extra></extra>',
                customdata: buyTrades.map(trade => trade.quantity)
            });
        }

        if (sellTrades.length > 0) {
            traces.push({
                x: sellTrades.map(trade => new Date(trade.timestamp)),
                y: sellTrades.map(trade => trade.price),
                mode: 'markers',
                marker: {
                    color: 'red',
                    size: 8
                },
                name: 'Sell Trades',
                hovertemplate: '<b>Sell Trade</b><br>' +
                              'Time: %{x}<br>' +
                              'Price: $%{y:.2f}<br>' +
                              'Quantity: %{customdata:.6f}<extra></extra>',
                customdata: sellTrades.map(trade => trade.quantity)
            });
        }

        const layout = {
            title: 'Trading Activity - Buy/Sell Trades',
            xaxis: {
                title: 'Time',
                type: 'date'
            },
            yaxis: {
                title: 'Price (FDUSD)'
            },
            hovermode: 'closest',
            showlegend: true,
            margin: {
                l: 60,
                r: 30,
                t: 60,
                b: 60
            }
        };

        const config = {
            responsive: true,
            displayModeBar: true,
            modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d']
        };

        Plotly.newPlot('trading-chart', traces, layout, config);
    }

    async loadOptionsPnlData() {
        try {
            let url = this.selectedBot ? `/api/options-pnl?bot_name=${encodeURIComponent(this.selectedBot)}` : '/api/options-pnl';
            
            if (this.timeFilter) {
                url += (url.includes('?') ? '&' : '?') + `hours_filter=${this.timeFilter}`;
            }
            
            const response = await fetch(url);
            const data = await response.json();
            
            if (data.data) {
                this.updateOptionsPnlChart(data.data);
            }
        } catch (error) {
            console.error('Error loading options PnL data:', error);
        }
    }

    async loadTotalPnlData() {
        try {
            let url = this.selectedBot ? `/api/total-pnl?bot_name=${encodeURIComponent(this.selectedBot)}` : '/api/total-pnl';
            
            if (this.timeFilter) {
                url += (url.includes('?') ? '&' : '?') + `hours_filter=${this.timeFilter}`;
            }
            
            const response = await fetch(url);
            const data = await response.json();
            
            if (data.data) {
                this.updateTotalPnlChart(data.data);
            }
        } catch (error) {
            console.error('Error loading total PnL data:', error);
        }
    }

    async loadPriceData() {
        try {
            let url = this.selectedBot ? `/api/price-data?bot_name=${encodeURIComponent(this.selectedBot)}` : '/api/price-data';
            
            if (this.timeFilter) {
                url += (url.includes('?') ? '&' : '?') + `hours_filter=${this.timeFilter}`;
            }
            
            const response = await fetch(url);
            const data = await response.json();
            
            if (data.data) {
                this.updatePriceChart(data.data);
            }
        } catch (error) {
            console.error('Error loading price data:', error);
        }
    }

    updateOptionsPnlChart(data) {
        if (!data || data.length === 0) {
            const chartDiv = document.getElementById('options-pnl-chart');
            chartDiv.innerHTML = '<div style="text-align: center; padding: 2rem; color: #999;">No options PnL data available yet.</div>';
            return;
        }

        const traces = [
            {
                x: data.map(item => new Date(item.timestamp)),
                y: data.map(item => item.call_unrealized_pnl),
                mode: 'lines+markers',
                marker: { color: 'blue', size: 6 },
                line: { color: 'blue', width: 2 },
                name: 'Call Option PnL',
                hovertemplate: '<b>Call PnL</b><br>Time: %{x}<br>PnL: $%{y:.2f}<extra></extra>'
            },
            {
                x: data.map(item => new Date(item.timestamp)),
                y: data.map(item => item.put_unrealized_pnl),
                mode: 'lines+markers',
                marker: { color: 'orange', size: 6 },
                line: { color: 'orange', width: 2 },
                name: 'Put Option PnL',
                hovertemplate: '<b>Put PnL</b><br>Time: %{x}<br>PnL: $%{y:.2f}<extra></extra>'
            }
        ];

        const layout = {
            title: 'Options PnL Over Time',
            xaxis: { title: 'Time', type: 'date' },
            yaxis: { title: 'PnL (FDUSD)' },
            hovermode: 'closest',
            showlegend: true,
            margin: { l: 60, r: 30, t: 60, b: 60 }
        };

        const config = { responsive: true, displayModeBar: true, modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d'] };
        Plotly.newPlot('options-pnl-chart', traces, layout, config);
    }

    updateTotalPnlChart(data) {
        if (!data || data.length === 0) {
            const chartDiv = document.getElementById('total-pnl-chart');
            chartDiv.innerHTML = '<div style="text-align: center; padding: 2rem; color: #999;">No total PnL data available yet.</div>';
            return;
        }

        const traces = [{
            x: data.map(item => new Date(item.timestamp)),
            y: data.map(item => item.total_unrealized_pnl),
            mode: 'lines+markers',
            marker: { color: 'purple', size: 6 },
            line: { color: 'purple', width: 2 },
            name: 'Total Unrealized PnL',
            hovertemplate: '<b>Total PnL</b><br>Time: %{x}<br>PnL: $%{y:.2f}<extra></extra>'
        }];

        const layout = {
            title: 'Total Unrealized PnL Over Time',
            xaxis: { title: 'Time', type: 'date' },
            yaxis: { title: 'PnL (FDUSD)' },
            hovermode: 'closest',
            showlegend: true,
            margin: { l: 60, r: 30, t: 60, b: 60 }
        };

        const config = { responsive: true, displayModeBar: true, modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d'] };
        Plotly.newPlot('total-pnl-chart', traces, layout, config);
    }

    updatePriceChart(data) {
        if (!data || data.length === 0) {
            const chartDiv = document.getElementById('price-chart');
            chartDiv.innerHTML = '<div style="text-align: center; padding: 2rem; color: #999;">No price data available yet.</div>';
            return;
        }

        const traces = [{
            x: data.map(item => new Date(item.timestamp)),
            y: data.map(item => item.price),
            mode: 'lines',
            line: { color: 'green', width: 2 },
            name: 'BTCFDUSD Price',
            hovertemplate: '<b>BTCFDUSD</b><br>Time: %{x}<br>Price: $%{y:.2f}<extra></extra>'
        }];

        const layout = {
            title: 'BTCFDUSD Price Over Time',
            xaxis: { title: 'Time', type: 'date' },
            yaxis: { title: 'Price (FDUSD)' },
            hovermode: 'closest',
            showlegend: true,
            margin: { l: 60, r: 30, t: 60, b: 60 }
        };

        const config = { responsive: true, displayModeBar: true, modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d'] };
        Plotly.newPlot('price-chart', traces, layout, config);
    }

    updateStatsCards(stats) {
        document.getElementById('total-trades').textContent = stats.total_trades || 0;
        document.getElementById('buy-trades').textContent = stats.buy_trades || 0;
        document.getElementById('sell-trades').textContent = stats.sell_trades || 0;
        document.getElementById('unrealized-pnl').textContent = `$${(stats.unrealized_pnl || 0).toFixed(2)}`;
        document.getElementById('total-unrealized-pnl').textContent = `$${(stats.total_unrealized_pnl || 0).toFixed(2)}`;
    }

    async loadBotConfig() {
        try {
            const response = await fetch('/api/config');
            const data = await response.json();
            
            if (data.config) {
                this.updateBotConfig(data.config);
            }
        } catch (error) {
            console.error('Error loading bot config:', error);
        }
    }

    updateBotConfig(config) {
        document.getElementById('config-mode').textContent = config.trading_mode || '--';
        document.getElementById('config-entry-price').textContent = config.spot_entry_price ? `$${config.spot_entry_price}` : '--';
        document.getElementById('config-market').textContent = config.spot_market || '--';
        document.getElementById('config-grid-orders').textContent = config.grid_max_open_orders || '--';
    }

    updateLastUpdatedTime() {
        const now = new Date();
        const timeString = now.toLocaleTimeString();
        document.getElementById('last-updated-time').textContent = timeString;
    }

    startAutoRefresh() {
        if (this.autoRefresh && this.refreshRate > 0) {
            this.refreshTimer = setInterval(() => {
                this.refreshData();
            }, this.refreshRate * 1000);
        }
    }

    stopAutoRefresh() {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
            this.refreshTimer = null;
        }
    }

    restartAutoRefresh() {
        this.stopAutoRefresh();
        this.startAutoRefresh();
    }
}

const style = document.createElement('style');
style.textContent = `
    .buy-side {
        color: #4CAF50;
        font-weight: bold;
    }
    .sell-side {
        color: #f44336;
        font-weight: bold;
    }
`;
document.head.appendChild(style);

document.addEventListener('DOMContentLoaded', () => {
    new GridderDashboard();
});
