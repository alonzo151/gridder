class GridderDashboard {
    constructor() {
        this.refreshRate = 30;
        this.autoRefresh = true;
        this.refreshTimer = null;
        this.selectedBot = '';
        
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
    }

    async loadInitialData() {
        await this.loadBotList();
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
                this.loadStatsData()
            ]);
            
            this.updateLastUpdatedTime();
        } catch (error) {
            console.error('Error refreshing data:', error);
        }
    }

    async loadTradesData() {
        try {
            const url = this.selectedBot ? `/api/trades?bot_name=${encodeURIComponent(this.selectedBot)}` : '/api/trades';
            const response = await fetch(url);
            const data = await response.json();
            
            if (data.trades) {
                this.updateTradingChart(data.trades);
                this.updateRecentTradesTable(data.trades);
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

    updateRecentTradesTable(trades) {
        const tbody = document.getElementById('recent-trades-body');
        
        if (!trades || trades.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="no-data">No trades data available</td></tr>';
            return;
        }

        const recentTrades = trades.slice(-10).reverse();
        
        tbody.innerHTML = recentTrades.map(trade => {
            const timestamp = new Date(trade.timestamp).toLocaleString();
            const sideClass = trade.side === 'BUY' ? 'buy-side' : 'sell-side';
            
            return `
                <tr>
                    <td>${timestamp}</td>
                    <td><span class="${sideClass}">${trade.side}</span></td>
                    <td>$${trade.price.toFixed(2)}</td>
                    <td>${trade.quantity.toFixed(6)}</td>
                    <td>${trade.bot_name}</td>
                </tr>
            `;
        }).join('');
    }

    updateStatsCards(stats) {
        document.getElementById('total-trades').textContent = stats.total_trades || 0;
        document.getElementById('buy-trades').textContent = stats.buy_trades || 0;
        document.getElementById('sell-trades').textContent = stats.sell_trades || 0;
        document.getElementById('unrealized-pnl').textContent = `$${(stats.unrealized_pnl || 0).toFixed(2)}`;
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
