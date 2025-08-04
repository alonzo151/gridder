import csv
from datetime import datetime
import numpy as np
from scipy.stats import norm
from scipy.optimize import minimize
import pandas as pd
import time
from global_assumptions import *

def check_global_assumptions():
    if spot_order_size_quote < 10:
        raise ValueError("spot_order_size_quote must be at least 10 USD")

# === Black-Scholes ===
def black_scholes_inverse_option_price(strike, T, IV, option_type, F):
    if F <= 0: return 0.0
    if T == 0:
        return max((F - strike) / F, 0) if option_type == 'call' else max((strike - F) / F, 0)
    d1 = (np.log(F / strike) + 0.5 * IV**2 * T) / (IV * np.sqrt(T))
    d2 = d1 - IV * np.sqrt(T)
    if option_type == 'call':
        return (F * norm.cdf(d1) - strike * norm.cdf(d2)) / F
    else:
        return (strike * norm.cdf(-d2) - F * norm.cdf(-d1)) / F

# === Spot PnL ===
def spot_pnl(price_change, entry_price, size):
    new_price = entry_price * (1 + price_change)
    return (new_price - entry_price) * size

# === PnL Constraints
def pnl_constraints_2eq(x, call, put, spot_below, underline_price, T, basis_rate):
    put_size, spot_below_size = x
    results = []
    for change in [-zero_profit_at_one_side_percent / 100, zero_profit_at_one_side_percent / 100]:
        S = underline_price * (1 + change)
        F = S * (1 + basis_rate * T)

        call_price = black_scholes_inverse_option_price(call['strike'], T, call['IV'], 'call', F)
        put_price = black_scholes_inverse_option_price(put['strike'], T, put['IV'], 'put', F)
        call_usd = call_price * S * call['size']
        put_usd = put_price * S * put_size

        F0 = underline_price * (1 + basis_rate * T)
        call_cost = black_scholes_inverse_option_price(call['strike'], T, call['IV'], 'call', F0) * underline_price * call['size']
        put_cost = black_scholes_inverse_option_price(put['strike'], T, put['IV'], 'put', F0) * underline_price * put_size

        spot_below_usd = spot_pnl(change, spot_below['entry_price'], spot_below_size) if change <= 0 else 0

        total_pnl = call_usd + put_usd + spot_below_usd - call_cost - put_cost
        results.append(total_pnl)
    return results

# === Optimization
def solve_two_size_strategy(call, put, spot_below, underline_price, expiration_date, basis_rate=0.072):
    T = (expiration_date - datetime.now()).days / 365.0

    def objective(x):
        pnl = pnl_constraints_2eq(x, call, put, spot_below, underline_price, T, basis_rate)
        return sum(p**2 for p in pnl)

    initial_guess = [1.0, 0.5]
    bounds = [(0, None), (0, None)]

    result = minimize(objective, initial_guess, bounds=bounds)

    if result.success:
        put_size, spot_below_size = result.x
        days_to_expiration = (expiration_date - datetime.now()).days
        T = days_to_expiration / 365.0
        F0 = underline_price * (1 + basis_rate * T)

        call_price = black_scholes_inverse_option_price(call['strike'], T, call['IV'], 'call', F0)
        put_price = black_scholes_inverse_option_price(put['strike'], T, put['IV'], 'put', F0)

        call_cost_btc = call['size'] * call_price
        put_cost_btc = put_size * put_price
        total_option_cost_btc = call_cost_btc + put_cost_btc
        invest_ratio = spot_below_size / total_option_cost_btc if total_option_cost_btc > 0 else np.inf
        options_daily_cost = total_option_cost_btc / days_to_expiration if days_to_expiration > 0 else np.inf

        total_daily_pnl = spot_below_size * daily_grid_profit_percent / 100 - options_daily_cost
        total_funds_needed_usd = (total_option_cost_btc + spot_below_size) * underline_price
        daily_roi_percent = 100 * (total_daily_pnl * underline_price) / total_funds_needed_usd if total_funds_needed_usd > 0 else np.inf

        return {
            'expiration_date': expiration_date.strftime('%Y-%m-%d'),
            'days_to_expiration': days_to_expiration,

            'call_strike': call['strike'],
            'call_IV': call['IV'],
            'call_theo_price': round(call_price, 6),
            'call_bid': call.get('Bid'),
            'call_bid_usd': round(call['Bid'] * underline_price, 2) if 'Bid' in call else None,
            'call_ask': call.get('Ask'),
            'call_ask_usd': round(call['Ask'] * underline_price, 2) if 'Ask' in call else None,
            'call_size': round(call['size'], 6),

            'put_strike': put['strike'],
            'put_IV': put['IV'],
            'put_theo_price': round(put_price, 6),
            'put_bid': put.get('Bid'),
            'put_ask': put.get('Ask'),
            'put_bid_usd': round(put.get('Bid', 0) * underline_price, 2),

            'put_size': round(put_size, 6),
            'spot_below_size': round(spot_below_size, 6),
            'spot_below_size_usd': round(spot_below_size * underline_price, 2),
            'invest_ratio': round(invest_ratio, 6),
            'options_daily_cost': round(options_daily_cost, 8),
            'total_daily_pnl': round(total_daily_pnl, 8),
            'total_funds_needed_usd': round(total_funds_needed_usd, 2),
            'daily_roi_percent': round(daily_roi_percent, 6),
            'objective': round(result.fun, 10),
            'basis_rate': basis_rate,
            'total_spot_funds_base': round(spot_below_size, 6),
        }


    else:
        return {
            'call_strike': call['strike'],
            'call_IV': call['IV'],
            'put_strike': put['strike'],
            'put_IV': put['IV'],
            'error': result.message
        }

def parse_float_safe(value):
    try:
        return float(value)
    except:
        return None

# === Load deal_analyzer and meta, group by expiration ===
def load_grouped_data(options_file, meta_file):
    options_df = pd.read_csv(options_file)
    meta_df = pd.read_csv(meta_file)

    grouped = {}
    for expiry, group_df in options_df.groupby("expiration"):
        meta_row = meta_df[meta_df["expiry"] == expiry]
        if meta_row.empty:
            print(f"⚠️ Skipping {expiry}: No meta info found")
            continue
        try:
            underline_price = float(meta_row["spot_price"].values[0])
            basis_rate = float(meta_row["basis_rate"].values[0])
            future_price = float(meta_row["future_price"].values[0])
            expiration_date = datetime.strptime(expiry, "%d%b%y")
        except Exception as e:
            print(f"⚠️ Failed to parse meta for {expiry}: {e}")
            continue

        calls = []
        puts = []
        for _, row in group_df.iterrows():
            try:
                strike = float(row["strike"])
                iv_bid = parse_float_safe(row.get("IV_Bid"))
                iv_ask = parse_float_safe(row.get("IV_Ask"))
                bid = parse_float_safe(row.get("Bid"))
                ask = parse_float_safe(row.get("Ask"))
                iv = iv_ask or iv_bid

                if iv is None:
                    continue

                option = {
                    "option_name": row["Instrument"],
                    "strike": strike,
                    "IV": iv,
                    "IV Bid": iv_bid,
                    "IV Ask": iv_ask,
                    "Bid": bid,
                    "Ask": ask
                }

                if row["Instrument"].endswith("-C"):
                    option["option_type"] = "call"
                    option["size"] = call_option_basic_size_base
                    calls.append(option)
                elif row["Instrument"].endswith("-P"):
                    option["option_type"] = "put"
                    puts.append(option)
            except:
                continue

        if calls and puts:
            grouped[expiry] = {
                "calls": calls,
                "puts": puts,
                "underline_price": underline_price,
                "basis_rate": basis_rate,
                "future_price": future_price,
                "expiration_date": expiration_date
            }
    return grouped


# === Run optimizer for all groups ===
def run_all_groups(grouped_data):
    all_results = []
    for expiry, info in grouped_data.items():
        print(f"\n▶️ Optimizing {expiry} | Spot: {info['underline_price']:.2f}, Basis: {info['basis_rate']:.5f}")
        spot_below_entry = info["underline_price"] * (1 - spot_one_side_range_percent / 100 / 4)

        for call in info["calls"]:
            for put in info["puts"]:
                if call["strike"] < info["future_price"] or put["strike"] > info["future_price"]:
                    continue
                result = solve_two_size_strategy(
                    call, put, {'entry_price': spot_below_entry},
                    info["underline_price"], info["expiration_date"], info["basis_rate"]
                )
                if "invest_ratio" in result:
                    result['call_option_name'] = call["option_name"]
                    result['put_option_name'] = put["option_name"]
                    result["expiration"] = expiry
                    result["basis_rate"] = info["basis_rate"]
                    result["spot_price"] = info["underline_price"]

                    all_results.append(result)
    return all_results

def create_configuration_json(sorted_results):
    for r in sorted_results:
        try:
            multiplier = r.get('spot_multiplier')
            data = {
                "bot_name": str(int(r.get("spot_price"))) +  time.strftime("_%Y_%m_%d_%H:%M:%S"),
                "call_option_name": r.get("call_option_name"),
                "call_option_size_base": multiplier * r.get("call_size"),
                "call_option_initial_cost_base": multiplier * r.get("call_size") * r.get("call_ask"),

                "put_option_name": r.get("put_option_name"),
                "put_option_size_base":  multiplier * r.get("put_size"),
                "put_option_initial_cost_base": multiplier * r.get("put_size") * r.get("put_ask"),

                "spot_entry_price": r.get("spot_price"),
                "spot_down_range_percent": spot_one_side_range_percent,
                "spot_up_range_percent": spot_one_side_range_percent,
                "spot_order_size_quote": spot_order_size_quote,
                "spot_orders_diff_percent": spot_orders_diff_percent,

                "basis_rate": r.get("basis_rate"),
                "call_option_iv": r.get("call_IV"),
                "put_option_iv": r.get("put_IV"),
                "total_spot_funds_base": r.get("total_spot_funds_base"),
            }
            lines = []
            for k, v in data.items():
                # Convert np.float64 to float
                if isinstance(v, np.floating):
                    v = float(v)
                # Use double quotes for keys and string values
                if isinstance(v, str):
                    lines.append(f'"{k}": "{v}",')
                else:
                    lines.append(f'"{k}": {v},')

            output = "\n".join(lines)
            r['config'] = output
        except Exception as e:
            print(f"⚠️ Error creating config for result {r.get('call_strike', 'N/A')} / {r.get('put_strike', 'N/A')}: {e}")
            continue
    return sorted_results

def results_filter(results):
    valid_results = [r for r in results if np.isfinite(r.get("invest_ratio", np.nan))]
    sorted_results = sorted(valid_results, key=lambda x: x['options_daily_cost'])
    # filter results with total_daily_pnl < 0
    sorted_results = [r for r in sorted_results if r['total_daily_pnl'] > 0]
    # filter results with days_to_expiration < 30
    sorted_results = [r for r in sorted_results if r['days_to_expiration'] >= options_min_days_to_expiration]
    # sort by daily_roi_percent
    sorted_results = sorted(sorted_results, key=lambda x: x['daily_roi_percent'], reverse=True)[:1000]
    # create an new column named 'spot_multiplier' which is the ratio of spot_below_size_usd to desired_spot_one_side_spot_position_usd
    for r in sorted_results:
        multiplier = max(spot_total_funds / r['spot_below_size_usd'], 1)
        r['spot_multiplier'] = multiplier
        r['call_ask_usd_final'] = r['call_ask_usd'] * multiplier * r['call_size']
        r['put_bid_usd_final'] = r['put_bid_usd'] * multiplier * r['put_size']
        r['spot_below_one_side_usd'] = r['spot_below_size_usd'] * multiplier

    return sorted_results

# === Main Run ===
if __name__ == "__main__":
    check_global_assumptions()
    options_file = "BTC-deal_analyzer-export.csv"
    meta_file = "BTC-deal_analyzer-meta.csv"

    grouped_data = load_grouped_data(options_file, meta_file)

    results = run_all_groups(grouped_data)

    results = results_filter(results)

    results = create_configuration_json(results)

    df = pd.DataFrame(results)
    print("\n📈 Top 1000 Strategies by Invest Ratio (Across All Expirations):\n")
    print(df.to_string(index=False))

    df.to_csv("top_1000_strategies.csv", index=False)
    print("✅ Results saved to top_1000_strategies.csv")
