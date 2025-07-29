import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import time
import os
from datetime import datetime
import bcrypt
from src.ui_data_reader import UIDataReader
from src.logger import setup_logger

logger = setup_logger()

DEFAULT_PASSWORD = "gridder123"
DEFAULT_REFRESH_RATE = 30

def check_password():
    """Returns True if the user has entered the correct password."""
    
    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == DEFAULT_PASSWORD:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct", False):
        return True

    st.text_input(
        "Password", type="password", on_change=password_entered, key="password"
    )
    
    if "password_correct" in st.session_state:
        st.error("😕 Password incorrect")
    
    return False

def create_trades_scatter_plot(df: pd.DataFrame):
    """Create scatter plot for trades data"""
    if df.empty:
        st.warning("No trades data available yet. The chart will update when trades are executed.")
        return None
    
    fig = go.Figure()
    
    buy_trades = df[df['side'] == 'BUY']
    if not buy_trades.empty:
        fig.add_trace(go.Scatter(
            x=buy_trades['timestamp'],
            y=buy_trades['price'],
            mode='markers',
            marker=dict(color='green', size=8),
            name='Buy Trades',
            hovertemplate='<b>Buy Trade</b><br>' +
                        'Time: %{x}<br>' +
                        'Price: $%{y:.2f}<br>' +
                        'Quantity: %{customdata:.6f}<extra></extra>',
            customdata=buy_trades['quantity']
        ))
    
    sell_trades = df[df['side'] == 'SELL']
    if not sell_trades.empty:
        fig.add_trace(go.Scatter(
            x=sell_trades['timestamp'],
            y=sell_trades['price'],
            mode='markers',
            marker=dict(color='red', size=8),
            name='Sell Trades',
            hovertemplate='<b>Sell Trade</b><br>' +
                        'Time: %{x}<br>' +
                        'Price: $%{y:.2f}<br>' +
                        'Quantity: %{customdata:.6f}<extra></extra>',
            customdata=sell_trades['quantity']
        ))
    
    fig.update_layout(
        title='Trading Activity - Buy/Sell Trades',
        xaxis_title='Time',
        yaxis_title='Price (FDUSD)',
        hovermode='closest',
        showlegend=True
    )
    
    return fig

def main():
    st.set_page_config(
        page_title="Gridder Trading Dashboard",
        page_icon="📈",
        layout="wide"
    )
    
    if not check_password():
        return
    
    st.title("📈 Gridder Trading Dashboard")
    st.markdown("---")
    
    st.sidebar.header("Dashboard Controls")
    
    refresh_rate = st.sidebar.slider(
        "Refresh Rate (seconds)",
        min_value=5,
        max_value=300,
        value=DEFAULT_REFRESH_RATE,
        step=5
    )
    
    auto_refresh = st.sidebar.checkbox("Auto Refresh", value=True)
    
    if st.sidebar.button("🔄 Refresh Now"):
        st.rerun()
    
    data_reader = UIDataReader()
    
    available_bots = data_reader.get_available_bots()
    selected_bot = None
    
    if available_bots:
        st.sidebar.markdown("---")
        st.sidebar.subheader("Bot Selection")
        bot_options = ["All Bots"] + available_bots
        selected_option = st.sidebar.selectbox("Select Bot", bot_options)
        if selected_option != "All Bots":
            selected_bot = selected_option
    
    trades_df = data_reader.get_trades_data(selected_bot)
    summary_stats = data_reader.get_summary_stats(selected_bot)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Trades", summary_stats['total_trades'])
    
    with col2:
        st.metric("Buy Trades", summary_stats['buy_trades'])
    
    with col3:
        st.metric("Sell Trades", summary_stats['sell_trades'])
    
    with col4:
        st.metric("Unrealized PnL", f"${summary_stats['unrealized_pnl']:.2f}")
    
    st.markdown("---")
    
    st.subheader("Trading Activity Chart")
    
    fig = create_trades_scatter_plot(trades_df)
    if fig:
        st.plotly_chart(fig, use_container_width=True)
    
    if not trades_df.empty:
        st.subheader("Recent Trades")
        recent_trades = trades_df.tail(10)[['timestamp', 'side', 'price', 'quantity', 'bot_name']]
        st.dataframe(recent_trades, use_container_width=True)
    
    st.sidebar.markdown("---")
    st.sidebar.text(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")
    
    if auto_refresh:
        time.sleep(refresh_rate)
        st.rerun()

if __name__ == "__main__":
    main()
