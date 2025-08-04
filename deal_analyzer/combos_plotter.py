from datetime import datetime
import numpy as np
from scipy.stats import norm
import matplotlib.pyplot as plt
import pandas as pd
import json
import re
from global_assumptions import *


# === Updated Black-Scholes with basis-adjusted forward ===
def black_scholes_inverse_option_price(strike, T, IV, option_type, F):
    if F <= 0:
        return 0.0
    if T == 0:
        return max((F - strike) / F, 0) if option_type == 'call' else max((strike - F) / F, 0)
    d1 = (np.log(F / strike) + 0.5 * IV**2 * T) / (IV * np.sqrt(T))
    d2 = d1 - IV * np.sqrt(T)
    if option_type == 'call':
        price_usd = F * norm.cdf(d1) - strike * norm.cdf(d2)
    else:
        price_usd = strike * norm.cdf(-d2) - F * norm.cdf(-d1)
    return price_usd / F

# === PnL Grid Simulation ===
def simulate_pnl_grid_inverse(underline_price_at_entry, strike, T_total, IV, option_type, size=1.0,
                              steps_price=101, steps_time=21, basis_rate=None):
    price_changes = np.linspace(-one_side_plotting_range_percent / 100, one_side_plotting_range_percent / 100, steps_price)
    time_fractions = np.linspace(0, 1, steps_time)
    S0 = underline_price_at_entry
    initial_price_btc = black_scholes_inverse_option_price(strike, T_total, IV, option_type,
                                                           S0 * (1 + basis_rate * T_total))
    initial_usd_cost = initial_price_btc * S0 * size
    pnl_btc_matrix, pnl_usd_matrix = [], []
    for t_frac in time_fractions:
        T_remain = T_total * (1 - t_frac)
        row_btc, row_usd = [], []
        for p in price_changes:
            S = underline_price_at_entry * (1 + p)
            F = S * (1 + basis_rate * T_remain)
            current_price = black_scholes_inverse_option_price(strike, T_remain, IV, option_type, F)
            pnl_btc = (current_price - initial_price_btc) * size
            pnl_usd = current_price * S * size - initial_usd_cost
            row_btc.append(pnl_btc)
            row_usd.append(pnl_usd)
        pnl_btc_matrix.append(row_btc)
        pnl_usd_matrix.append(row_usd)
    return np.array(pnl_btc_matrix), np.array(pnl_usd_matrix), price_changes, time_fractions

# === Spot PnL Simulation ===
def simulate_spot_pnl(price_changes, entry_price, size, apply_below_zero=True):
    spot_pnl = []
    for p in price_changes:
        if (apply_below_zero and p <= 0) or (not apply_below_zero and p >= 0):
            current_price = entry_price * (1 + p)
            pnl = (current_price - entry_price) * size
        else:
            pnl = 0
        spot_pnl.append(pnl)
    return np.array(spot_pnl)

# === Combined Plotting and Table ===
def plot_combined_pnls_and_table(opt1, opt2, spot_below, spot_above, underline_price_at_entry,
                                 T_total, basis_rate=None):
    pnl1_btc, pnl1_usd, price_changes, time_fractions = simulate_pnl_grid_inverse(
        underline_price_at_entry, **opt1, T_total=T_total, basis_rate=basis_rate)
    pnl2_btc, pnl2_usd, _, _ = simulate_pnl_grid_inverse(
        underline_price_at_entry, **opt2, T_total=T_total, basis_rate=basis_rate)

    spot_below_usd = simulate_spot_pnl(price_changes, **spot_below, apply_below_zero=True)
    spot_above_usd = simulate_spot_pnl(price_changes, **spot_above, apply_below_zero=False)
    spot_total_usd = spot_below_usd + spot_above_usd

    total_time0_usd = pnl1_usd[0] + pnl2_usd[0] + spot_total_usd
    total_expiry_usd = pnl1_usd[-1] + pnl2_usd[-1] + spot_total_usd

    # Plotting
    plt.figure(figsize=(12, 6))
    plt.plot(price_changes * 100, pnl1_usd[0], '--', label=f"Option 1 (t=0): {opt1['option_type']} K={opt1['strike']}")
    plt.plot(price_changes * 100, pnl1_usd[-1], '-', label=f"Option 1 (expiry)")
    plt.plot(price_changes * 100, pnl2_usd[0], '--', label=f"Option 2 (t=0): {opt2['option_type']} K={opt2['strike']}")
    plt.plot(price_changes * 100, pnl2_usd[-1], '-', label=f"Option 2 (expiry)")
    plt.plot(price_changes * 100, spot_below_usd, ':', label=f"Spot Below: {spot_below['size']} BTC @ {spot_below['entry_price']}")
    plt.plot(price_changes * 100, spot_above_usd, ':', label=f"Spot Above: {spot_above['size']} BTC @ {spot_above['entry_price']}")
    plt.plot(price_changes * 100, total_time0_usd, '--', label="Total PnL (t=0)", color='black')
    plt.plot(price_changes * 100, total_expiry_usd, '-', label="Total PnL (expiry)", color='black')
    plt.axhline(0, linestyle='--', color='gray')
    plt.axvline(0, linestyle=':', color='gray')
    plt.xlabel("Price Change (%)")
    plt.ylabel("PnL (USD)")
    plt.title("Total PnL with Forward Basis Adjustment")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()

    # Table for -20% to +20% at 1% steps
    table = []
    percent_range = np.arange(-0.20, 0.21, 0.01)
    for p in percent_range:
        idx = (np.abs(price_changes - p)).argmin()
        table.append({
            "Price Change (%)": round(p * 100, 2),
            "Total PnL @ t=0 (USD)": round(total_time0_usd[idx], 2)
        })
    df = pd.DataFrame(table)
    print(df.to_string(index=False))

def extract_option_expiration_date(option):
    match = re.search(r'(\d{2})([A-Z]{3})(\d{2})', option)
    if match:
        day = match.group(1)
        month = match.group(2)
        year = match.group(3)
        dt = datetime.strptime(f"{day}{month}{year}", "%d%b%y")
        return dt

def extract_option_strike(option):
    all = option.split('-')
    return int(all[2])

with open('config_for_plotter.json', 'r') as f:
    config_data = json.load(f)

underline_price_at_entry = config_data['spot_entry_price']
call_expiration_date = extract_option_expiration_date(config_data['call_option_name'])
put_expiration_date = extract_option_expiration_date(config_data['put_option_name'])
if call_expiration_date != put_expiration_date:
    raise ValueError("Call and Put expiration dates must be the same for this plotter.")

T_T = (call_expiration_date - datetime.now()).days / 365.0
basis_rate = config_data.get('basis_rate')  # Default to 7.2% if not specified

# === Example Usage ===
call_option = {
    'strike': extract_option_strike(config_data.get('call_option_name')),
    'IV': config_data.get('call_option_iv'),
    'option_type': 'call',
    'size': config_data.get('call_option_size_base'),
}
put_option = {
    'strike': extract_option_strike(config_data.get('put_option_name')),
    'IV': config_data.get('put_option_iv'),
    'option_type': 'put',
    'size': config_data.get('put_option_size_base') # example adjusted size
}

spot_below = {
    'entry_price': underline_price_at_entry * (1 - spot_one_side_range_percent / 100 / 4),  # 5% below entry price
    'size': config_data.get('total_spot_funds_base'),
}

spot_above = {
    'entry_price': underline_price_at_entry * (1 + spot_one_side_range_percent / 100 / 4),
    'size': 0#config_data.get('total_spot_funds_base') # example adjusted size
}

plot_combined_pnls_and_table(call_option, put_option, spot_below, spot_above,
                             underline_price_at_entry=underline_price_at_entry,
                             T_total=T_T,
                             basis_rate=basis_rate)
