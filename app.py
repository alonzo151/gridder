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

@app.route('/api/bots')
def api_bots():
    if not require_auth():
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        bots = data_reader.get_available_bots()
        return jsonify({'bots': bots})
    except Exception as e:
        logger.error(f"Error getting bots: {e}")
        return jsonify({'error': 'Failed to load bots'}), 500

@app.route('/api/trades')
def api_trades():
    if not require_auth():
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        bot_name = request.args.get('bot_name')
        if bot_name == '':
            bot_name = None
        
        hours_filter = request.args.get('hours_filter')
        if hours_filter:
            hours_filter = int(hours_filter)
        
        trades_df = data_reader.get_trades_data(bot_name, hours_filter)
        
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
        if bot_name == '':
            bot_name = None
        
        stats = data_reader.get_summary_stats(bot_name)
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
        
        hours_filter = request.args.get('hours_filter')
        if hours_filter:
            hours_filter = int(hours_filter)
        
        options_df = data_reader.get_options_pnl_data(bot_name, hours_filter)
        
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
        
        hours_filter = request.args.get('hours_filter')
        if hours_filter:
            hours_filter = int(hours_filter)
        
        total_pnl_df = data_reader.get_total_unrealized_pnl_data(bot_name, hours_filter)
        
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
        
        hours_filter = request.args.get('hours_filter')
        if hours_filter:
            hours_filter = int(hours_filter)
        
        price_df = data_reader.get_price_data(bot_name, hours_filter)
        
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

@app.route('/api/config')
def api_config():
    if not require_auth():
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        import json
        config_path = 'config/config.json'
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        safe_config = {
            'trading_mode': config.get('trading_mode'),
            'spot_entry_price': config.get('spot_entry_price'),
            'spot_market': config.get('spot_market'),
            'spot_down_range_percent': config.get('spot_down_range_percent'),
            'spot_up_range_percent': config.get('spot_up_range_percent'),
            'spot_order_size_quote': config.get('spot_order_size_quote'),
            'spot_orders_diff_percent': config.get('spot_orders_diff_percent'),
            'grid_max_open_orders': config.get('grid_max_open_orders'),
            'call_option_name': config.get('call_option_name'),
            'put_option_name': config.get('put_option_name'),
            'daily_roi_target_for_exit': config.get('daily_roi_target_for_exit')
        }
        
        return jsonify({'config': safe_config})
    except Exception as e:
        logger.error(f"Error getting config: {e}")
        return jsonify({'error': 'Failed to load config'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
