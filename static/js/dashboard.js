class GridderDashboard {
    constructor() {
        this.refreshRate = 30;
        this.autoRefresh = true;
        this.refreshTimer = null;
        this.selectedBotName = '';
        this.selectedBotRun = '';
        this.includeAllRuns = false;
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

        const botNameSelect = document.getElementById('bot-name-select');
        botNameSelect.addEventListener('change', (e) => {
            this.selectedBotName = e.target.value;
            this.selectedBotRun = '';
            this.loadBotRuns();
            if (this.selectedBotName) {
                this.refreshData();
            }
        });

        const botRunSelect = document.getElementById('bot-run-select');
        botRunSelect.addEventListener('change', (e) => {
            this.selectedBotRun = e.target.value;
            this.refreshData();
        });

        const includeAllRunsCheckbox = document.getElementById('include-all-runs');
        includeAllRunsCheckbox.addEventListener('change', (e) => {
            this.includeAllRuns = e.target.checked;
            const botRunSelect = document.getElementById('bot-run-select');
            botRunSelect.disabled = this.includeAllRuns;
            if (this.includeAllRuns) {
                this.selectedBotRun = '';
            }
            this.refreshData();
        });

        const timeFilterSelect = document.getElementById('time-filter');
        timeFilterSelect.addEventListener('change', (e) => {
            this.timeFilter = e.target.value ? parseInt(e.target.value) : null;
            this.refreshData();
        });
    }

    async loadInitialData() {
        await this.loadBotNames();
        await this.loadDefaultSelection();
        await this.refreshData();
    }

    async loadBotNames() {
        try {
            const response = await fetch('/api/bot-names');
            const data = await response.json();
            
            if (data.bot_names) {
                const botNameSelect = document.getElementById('bot-name-select');
                botNameSelect.innerHTML = '<option value="">Select Bot...</option>';
                
                data.bot_names.forEach(botName => {
                    const option = document.createElement('option');
                    option.value = botName;
                    option.textContent = botName;
                    botNameSelect.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Error loading bot names:', error);
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
            let url = '/api/trades?';
            const params = new URLSearchParams();
            
            if (this.selectedBotName) params.append('bot_name', this.selectedBotName);
            if (this.selectedBotRun && !this.includeAllRuns) params.append('bot_run', this.selectedBotRun);
            if (this.includeAllRuns) params.append('include_all_runs', 'true');
            if (this.timeFilter) params.append('hours_filter', this.timeFilter.toString());
            
            url += params.toString();
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
            let url = '/api/stats?';
            const params = new URLSearchParams();
            
            if (this.selectedBotName) params.append('bot_name', this.selectedBotName);
            if (this.selectedBotRun && !this.includeAllRuns) params.append('bot_run', this.selectedBotRun);
            if (this.includeAllRuns) params.append('include_all_runs', 'true');
            if (this.timeFilter) params.append('hours_filter', this.timeFilter.toString());
            
            url += params.toString();
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
            let url = '/api/options-pnl?';
            const params = new URLSearchParams();
            
            if (this.selectedBotName) params.append('bot_name', this.selectedBotName);
            if (this.selectedBotRun && !this.includeAllRuns) params.append('bot_run', this.selectedBotRun);
            if (this.includeAllRuns) params.append('include_all_runs', 'true');
            if (this.timeFilter) params.append('hours_filter', this.timeFilter.toString());
            
            url += params.toString();
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
            let url = '/api/total-pnl?';
            const params = new URLSearchParams();
            
            if (this.selectedBotName) params.append('bot_name', this.selectedBotName);
            if (this.selectedBotRun && !this.includeAllRuns) params.append('bot_run', this.selectedBotRun);
            if (this.includeAllRuns) params.append('include_all_runs', 'true');
            if (this.timeFilter) params.append('hours_filter', this.timeFilter.toString());
            
            url += params.toString();
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
            let url = '/api/price-data?';
            const params = new URLSearchParams();
            
            if (this.selectedBotName) params.append('bot_name', this.selectedBotName);
            if (this.selectedBotRun && !this.includeAllRuns) params.append('bot_run', this.selectedBotRun);
            if (this.includeAllRuns) params.append('include_all_runs', 'true');
            if (this.timeFilter) params.append('hours_filter', this.timeFilter.toString());
            
            url += params.toString();
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

    async loadBotRuns() {
        const botRunSelect = document.getElementById('bot-run-select');
        
        if (!this.selectedBotName) {
            botRunSelect.innerHTML = '<option value="">Select Run...</option>';
            botRunSelect.disabled = true;
            return;
        }

        try {
            const response = await fetch(`/api/bot-runs?bot_name=${encodeURIComponent(this.selectedBotName)}`);
            const data = await response.json();
            
            if (data.runs) {
                botRunSelect.innerHTML = '<option value="">Select Run...</option>';
                
                data.runs.forEach(run => {
                    const option = document.createElement('option');
                    option.value = run.bot_run;
                    option.textContent = `${run.bot_run} (${new Date(run.timestamp).toLocaleString()})`;
                    botRunSelect.appendChild(option);
                });
                
                botRunSelect.disabled = this.includeAllRuns;
            }
        } catch (error) {
            console.error('Error loading bot runs:', error);
        }
    }

    async loadDefaultSelection() {
        try {
            const response = await fetch('/api/latest-bot-run');
            const data = await response.json();
            
            if (data.bot_name && data.bot_run) {
                this.selectedBotName = data.bot_name;
                this.selectedBotRun = data.bot_run;
                
                document.getElementById('bot-name-select').value = this.selectedBotName;
                await this.loadBotRuns();
                document.getElementById('bot-run-select').value = this.selectedBotRun;
                
                await this.loadRunConfig();
            }
        } catch (error) {
            console.error('Error loading default selection:', error);
        }
    }

    async loadRunConfig() {
        if (!this.selectedBotName || !this.selectedBotRun) {
            return;
        }

        try {
            const response = await fetch(`/api/run-config?bot_name=${encodeURIComponent(this.selectedBotName)}&bot_run=${encodeURIComponent(this.selectedBotRun)}`);
            const data = await response.json();
            
            if (data.config) {
                this.updateBotConfig(data.config);
            }
        } catch (error) {
            console.error('Error loading run config:', error);
        }
    }

    updateBotConfig(config) {
        document.getElementById('config-mode').textContent = config.trading_mode || '--';
        document.getElementById('config-entry-price').textContent = config.spot_entry_price ? `$${config.spot_entry_price}` : '--';
        document.getElementById('config-market').textContent = config.spot_market || '--';
        document.getElementById('config-grid-orders').textContent = config.grid_max_open_orders || '--';
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
