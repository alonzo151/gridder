import requests
import time
import pandas as pd
from collections import defaultdict
from global_assumptions import *

BASE_URL = "https://www.deribit.com/api/v2"  # Minimum liquidity threshold for deal_analyzer

def get_ticker(instrument_name):
    try:
        res = requests.get(f"{BASE_URL}/public/ticker", params={"instrument_name": instrument_name})
        return res.json().get("result", {})
    except Exception as e:
        print(f"Error fetching ticker for {instrument_name}: {e}")
        return {}

def get_all_option_instruments():
    res = requests.get(f"{BASE_URL}/public/get_instruments", params={"currency": "BTC", "kind": "option"})
    return res.json().get("result", [])

def get_spot_price():
    return get_ticker("BTC-PERPETUAL").get("mark_price")

def get_expiry_from_symbol(symbol):
    try:
        return symbol.split('-')[1]
    except IndexError:
        return None

def group_by_expiry(instruments):
    grouped = defaultdict(list)
    for inst in instruments:
        expiry = get_expiry_from_symbol(inst["instrument_name"])
        if expiry:
            grouped[expiry].append(inst)
    return grouped

def fetch_all_expiries():
    all_inst = get_all_option_instruments()
    grouped = group_by_expiry(all_inst)
    spot_price = get_spot_price()

    print(f"\n🎯 Spot Price: {spot_price:.2f}")
    print(f"🔍 Found {len(grouped)} expirations")

    all_rows = []
    all_meta = []

    for expiry, inst_list in grouped.items():
        future_symbol = f"BTC-{expiry}"
        future_price = get_ticker(future_symbol).get("mark_price")
        if not future_price or not spot_price:
            print(f"⚠️ Skipping {expiry} — missing future or spot")
            continue

        basis = (future_price - spot_price) / spot_price
        print(f"📆 {expiry}: Spot={spot_price:.2f}, Future={future_price:.2f}, Basis={basis:.6f}, Options={len(inst_list)}")

        for inst in inst_list:
            print(inst)
            name = inst["instrument_name"]
            ticker = get_ticker(name)
            if not ticker:
                continue

            row = {
                "Instrument": name,
                "expiration": expiry,
                "strike": inst["strike"],
                "IV_Bid": round(ticker.get("bid_iv", 0), 5) if ticker.get("bid_iv") else "-",
                "Bid": round(ticker.get("best_bid_price", 0), 5) if ticker.get("best_bid_price") else "-",
                "Bid_amount": round(ticker.get("best_bid_amount", 0), 5) if ticker.get("best_bid_amount") else "-",
                "IV_Ask": round(ticker.get("ask_iv", 0), 5) if ticker.get("ask_iv") else "-",
                "Ask": round(ticker.get("best_ask_price", 0), 5) if ticker.get("best_ask_price") else "-",
                "Ask_amount": round(ticker.get("best_ask_amount", 0), 5) if ticker.get("best_ask_amount") else "-"

            }
            if row['Ask_amount'] == '-' or row['Bid_amount'] == '-' or row['Ask_amount'] < min_liquidity_for_options_base or row['Bid_amount'] < min_liquidity_for_options_base:
                print(f"⚠️ Skipping {name} {expiry} — low liquidity")
                continue
            if row['IV_Bid'] == '-' or row['IV_Ask'] == '-':
                print(f"⚠️ Skipping {name} {expiry} — missing IV")
                continue
            row['IV_Bid'] = row['IV_Bid'] / 100
            row['IV_Ask'] = row['IV_Ask'] / 100
            all_rows.append(row)
            time.sleep(0.05)

        all_meta.append({
            "expiry": expiry,
            "spot_price": spot_price,
            "future_price": future_price,
            "basis_rate": basis
        })

    # Save consolidated option data
    if all_rows:
        df = pd.DataFrame(all_rows, columns=[
            "Instrument", "expiration", "strike", "IV_Bid", "Bid", "Bid_amount", "IV_Ask", "Ask", "Ask_amount"
        ])
        df.to_csv("BTC-deal_analyzer-export.csv", index=False)
        print(f"✅ Saved ALL deal_analyzer to BTC-deal_analyzer-export.csv")

    # Save consolidated meta info
    if all_meta:
        meta_df = pd.DataFrame(all_meta)
        meta_df.to_csv("BTC-deal_analyzer-meta.csv", index=False)
        print(f"✅ Saved ALL metadata to BTC-deal_analyzer-meta.csv")

if __name__ == "__main__":
    fetch_all_expiries()
