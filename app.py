from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import bcrypt
import secrets
import os
from datetime import datetime
from src.ui_data_reader import UIDataReader
from src.logger import setup_logger

logger = setup_logger()

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

DEFAULT_PASSWORD = os.getenv('GRIDDER_UI_PASSWORD')
if not DEFAULT_PASSWORD:
    logger.error("GRIDDER_UI_PASSWORD environment variable is required")
    exit(1)
data_reader = UIDataReader()

def check_password(password):
    """Check if the provided password is correct"""
    return password == DEFAULT_PASSWORD

def require_auth():
    """Check if user is authenticated"""
    return session.get('authenticated', False)

@app.route('/')
def index():
    if require_auth():
        return render_template('dashboard.html')
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        if check_password(password):
            session['authenticated'] = True
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Invalid password')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/api/bot-names')
def api_bot_names():
    if not require_auth():
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        bot_names = data_reader.get_available_bot_names()
        return jsonify({'bot_names': bot_names})
    except Exception as e:
        logger.error(f"Error getting bot names: {e}")
        return jsonify({'error': 'Failed to load bot names'}), 500

@app.route('/api/trades')
def api_trades():
    if not require_auth():
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        bot_name = request.args.get('bot_name')
        if bot_name == '':
            bot_name = None
        
        trades_df = data_reader.get_trades_data(bot_name)
        
        trades = []
        for _, row in trades_df.iterrows():
            trades.append({
                'timestamp': row['timestamp'].isoformat(),
                'price': float(row['price']),
                'side': row['side'],
                'quantity': float(row['quantity']),
                'bot_name': row['bot_name']
            })
        
        return jsonify({'trades': trades})
    except Exception as e:
        logger.error(f"Error getting trades: {e}")
        return jsonify({'error': 'Failed to load trades'}), 500

@app.route('/api/stats')
def api_stats():
    if not require_auth():
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        bot_name = request.args.get('bot_name')
        bot_run = request.args.get('bot_run')
        include_all_runs = request.args.get('include_all_runs', 'false').lower() == 'true'
        hours_filter = request.args.get('hours_filter')
        
        if bot_name == '':
            bot_name = None
        if bot_run == '':
            bot_run = None
        if hours_filter:
            hours_filter = int(hours_filter)
        
        stats = data_reader.get_summary_stats(bot_name, bot_run, include_all_runs, hours_filter)
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({'error': 'Failed to load stats'}), 500

@app.route('/api/options-pnl')
def api_options_pnl():
    if not require_auth():
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        bot_name = request.args.get('bot_name')
        if bot_name == '':
            bot_name = None
        
        options_df = data_reader.get_options_pnl_data(bot_name)
        
        data = []
        for _, row in options_df.iterrows():
            data.append({
                'timestamp': row['timestamp'].isoformat(),
                'call_unrealized_pnl': float(row['call_unrealized_pnl']),
                'put_unrealized_pnl': float(row['put_unrealized_pnl']),
                'bot_name': row['bot_name']
            })
        
        return jsonify({'data': data})
    except Exception as e:
        logger.error(f"Error getting options PnL: {e}")
        return jsonify({'error': 'Failed to load options PnL'}), 500

@app.route('/api/total-pnl')
def api_total_pnl():
    if not require_auth():
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        bot_name = request.args.get('bot_name')
        if bot_name == '':
            bot_name = None
        
        total_pnl_df = data_reader.get_total_unrealized_pnl_data(bot_name)
        
        data = []
        for _, row in total_pnl_df.iterrows():
            data.append({
                'timestamp': row['timestamp'].isoformat(),
                'total_unrealized_pnl': float(row['total_unrealized_pnl']),
                'bot_name': row['bot_name']
            })
        
        return jsonify({'data': data})
    except Exception as e:
        logger.error(f"Error getting total PnL: {e}")
        return jsonify({'error': 'Failed to load total PnL'}), 500

@app.route('/api/price-data')
def api_price_data():
    if not require_auth():
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        bot_name = request.args.get('bot_name')
        if bot_name == '':
            bot_name = None
        
        price_df = data_reader.get_price_data(bot_name)
        
        data = []
        for _, row in price_df.iterrows():
            data.append({
                'timestamp': row['timestamp'].isoformat(),
                'price': float(row['price']),
                'bot_name': row['bot_name']
            })
        
        return jsonify({'data': data})
    except Exception as e:
        logger.error(f"Error getting price data: {e}")
        return jsonify({'error': 'Failed to load price data'}), 500

@app.route('/api/bot-runs')
def api_bot_runs():
    if not require_auth():
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        bot_name = request.args.get('bot_name')
        if not bot_name:
            return jsonify({'error': 'bot_name parameter required'}), 400
        
        runs = data_reader.get_bot_runs(bot_name)
        return jsonify({'runs': runs})
    except Exception as e:
        logger.error(f"Error getting bot runs: {e}")
        return jsonify({'error': 'Failed to load bot runs'}), 500

@app.route('/api/latest-bot-run')
def api_latest_bot_run():
    if not require_auth():
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        latest = data_reader.get_latest_bot_run()
        return jsonify(latest)
    except Exception as e:
        logger.error(f"Error getting latest bot run: {e}")
        return jsonify({'error': 'Failed to load latest bot run'}), 500

@app.route('/api/run-config')
def api_run_config():
    if not require_auth():
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        bot_name = request.args.get('bot_name')
        bot_run = request.args.get('bot_run')
        if not bot_name or not bot_run:
            return jsonify({'error': 'bot_name and bot_run parameters required'}), 400
        
        config = data_reader.get_run_config(bot_name, bot_run)
        return jsonify({'config': config})
    except Exception as e:
        logger.error(f"Error getting run config: {e}")
        return jsonify({'error': 'Failed to load run config'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
