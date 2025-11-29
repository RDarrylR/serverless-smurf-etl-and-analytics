#!/usr/bin/env python3
"""
Realistic Sample Data Generator for Smurf Memorabilia Inc.

Generates 30 days of transaction data for 11 stores with:
- ~200 transactions per store per day (with variation)
- Weekend seasonality (Fri/Sat/Sun higher sales)
- Store-level performance tiers (some stores consistently better)
- Product popularity waves across all stores
- Random variation for realism
"""

import json
import random
import os
from datetime import datetime, timedelta
from typing import List, Dict
import math

# Configuration
NUM_STORES = 11
NUM_DAYS = 30
BASE_TRANSACTIONS_PER_DAY = 200
OUTPUT_DIR = "sample_data"

# End date is November 27, 2025, start date is 30 days before
END_DATE = datetime(2025, 11, 27)
START_DATE = END_DATE - timedelta(days=NUM_DAYS - 1)  # October 29, 2025

# Product catalog with base prices and popularity scores
PRODUCTS = [
    {"sku": "SMURF-FIG-001", "name": "Papa Smurf Figurine", "price": 24.99, "base_popularity": 0.85},
    {"sku": "SMURF-FIG-002", "name": "Smurfette Figurine", "price": 24.99, "base_popularity": 0.90},
    {"sku": "SMURF-FIG-003", "name": "Brainy Smurf Figurine", "price": 22.99, "base_popularity": 0.70},
    {"sku": "SMURF-FIG-004", "name": "Hefty Smurf Figurine", "price": 22.99, "base_popularity": 0.75},
    {"sku": "SMURF-FIG-005", "name": "Clumsy Smurf Figurine", "price": 21.99, "base_popularity": 0.65},
    {"sku": "SMURF-FIG-006", "name": "Gargamel & Azrael Set", "price": 34.99, "base_popularity": 0.60},
    {"sku": "SMURF-PLU-001", "name": "Smurf Plush Toy (Small)", "price": 14.99, "base_popularity": 0.80},
    {"sku": "SMURF-PLU-002", "name": "Smurf Plush Toy (Large)", "price": 29.99, "base_popularity": 0.55},
    {"sku": "SMURF-PLU-003", "name": "Smurfette Plush Toy", "price": 16.99, "base_popularity": 0.75},
    {"sku": "SMURF-TSH-001", "name": "Vintage Smurf T-Shirt", "price": 19.99, "base_popularity": 0.70},
    {"sku": "SMURF-TSH-002", "name": "Smurfs Group T-Shirt", "price": 21.99, "base_popularity": 0.80},
    {"sku": "SMURF-HAT-001", "name": "Smurf Hat (Blue)", "price": 15.99, "base_popularity": 0.50},
    {"sku": "SMURF-MUG-001", "name": "Smurf Coffee Mug", "price": 12.99, "base_popularity": 0.85},
    {"sku": "SMURF-KEY-001", "name": "Smurf Keychain", "price": 6.99, "base_popularity": 0.90},
    {"sku": "SMURF-KEY-002", "name": "Smurfette Keychain", "price": 6.99, "base_popularity": 0.88},
    {"sku": "SMURF-PST-001", "name": "Smurf Village Poster", "price": 9.99, "base_popularity": 0.60},
    {"sku": "SMURF-PST-002", "name": "Retro Smurfs Poster Set", "price": 24.99, "base_popularity": 0.45},
    {"sku": "SMURF-DVD-001", "name": "Smurfs Complete Season 1 DVD", "price": 29.99, "base_popularity": 0.40},
    {"sku": "SMURF-GAM-001", "name": "Smurf Board Game", "price": 24.99, "base_popularity": 0.55},
    {"sku": "SMURF-LUN-001", "name": "Smurf Lunch Box", "price": 18.99, "base_popularity": 0.65},
]

# Payment method distribution (weighted)
PAYMENT_METHODS = ["cash", "credit", "debit", "gift_card", "mobile"]
PAYMENT_WEIGHTS = [0.20, 0.35, 0.25, 0.10, 0.10]

# Store performance tiers (multiplier for transaction count and avg transaction value)
# Some stores are flagship/high-traffic, others are smaller
STORE_TIERS = {
    "0001": {"transactions_mult": 1.2, "value_mult": 1.1, "name": "Downtown Flagship"},
    "0002": {"transactions_mult": 1.3, "value_mult": 1.15, "name": "Mall Location"},
    "0003": {"transactions_mult": 0.9, "value_mult": 0.95, "name": "Suburban North"},
    "0004": {"transactions_mult": 0.7, "value_mult": 0.90, "name": "Small Town"},
    "0005": {"transactions_mult": 1.0, "value_mult": 1.0, "name": "University District"},
    "0006": {"transactions_mult": 0.6, "value_mult": 0.85, "name": "Rural Outlet"},
    "0007": {"transactions_mult": 1.1, "value_mult": 1.05, "name": "Shopping Center"},
    "0008": {"transactions_mult": 1.15, "value_mult": 1.08, "name": "Tourist Area"},
    "0009": {"transactions_mult": 0.95, "value_mult": 0.98, "name": "Residential Plaza"},
    "0010": {"transactions_mult": 0.85, "value_mult": 0.92, "name": "Industrial Park"},
    "0011": {"transactions_mult": 1.05, "value_mult": 1.02, "name": "Airport Terminal"},
}


def get_day_of_week_multiplier(date: datetime) -> float:
    """Return a sales multiplier based on day of week (weekend boost)"""
    day = date.weekday()  # Monday=0, Sunday=6

    multipliers = {
        0: 0.85,   # Monday - slow start to week
        1: 0.90,   # Tuesday
        2: 0.95,   # Wednesday - midweek pickup
        3: 1.00,   # Thursday
        4: 1.25,   # Friday - weekend starts
        5: 1.40,   # Saturday - peak
        6: 1.20,   # Sunday - strong but less than Saturday
    }
    return multipliers[day]


def get_product_trend_multiplier(product_idx: int, day_num: int) -> float:
    """
    Generate product popularity waves that affect all stores similarly.
    Uses sine waves with different phases for different products.
    """
    # Each product has a unique phase offset
    phase = (product_idx * 2.5) % (2 * math.pi)

    # Create a wave with a ~10 day period
    wave_period = 10 + (product_idx % 5)  # Vary period slightly per product
    wave = math.sin((day_num / wave_period) * 2 * math.pi + phase)

    # Scale wave to reasonable multiplier range (0.7 to 1.3)
    multiplier = 1.0 + (wave * 0.3)

    # Add some random daily noise
    noise = random.uniform(-0.1, 0.1)

    return max(0.5, min(1.5, multiplier + noise))


def get_monthly_trend(day_num: int) -> float:
    """
    Simulate monthly patterns - slight dip mid-month, pickup at month end
    """
    # Payday effect - beginning and end of month slightly higher
    if day_num <= 5 or day_num >= 25:
        return 1.1
    elif 10 <= day_num <= 20:
        return 0.95
    return 1.0


def generate_transaction_id(store_id: str, date: datetime, seq: int) -> str:
    """Generate unique transaction ID"""
    return f"TXN-{store_id}-{date.strftime('%Y%m%d')}-{seq:04d}"


def generate_customer_id() -> str:
    """Generate customer ID (some repeat customers)"""
    # 70% chance of being a "regular" customer from pool of 500
    # 30% chance of being a "new" customer
    if random.random() < 0.7:
        return f"CUST-{random.randint(1, 500):05d}"
    else:
        return f"CUST-{random.randint(10000, 99999):05d}"


def select_products_for_transaction(date: datetime, day_num: int) -> List[Dict]:
    """Select 1-5 products for a transaction with trend-aware weighting"""
    num_items = random.choices([1, 2, 3, 4, 5], weights=[0.35, 0.30, 0.20, 0.10, 0.05])[0]

    # Calculate weighted probabilities for each product
    weights = []
    for idx, product in enumerate(PRODUCTS):
        base_weight = product["base_popularity"]
        trend_mult = get_product_trend_multiplier(idx, day_num)
        weights.append(base_weight * trend_mult)

    # Normalize weights
    total = sum(weights)
    weights = [w / total for w in weights]

    # Select products (without replacement)
    selected_indices = []
    available_indices = list(range(len(PRODUCTS)))
    available_weights = weights.copy()

    for _ in range(min(num_items, len(PRODUCTS))):
        if not available_indices:
            break
        # Normalize available weights
        total_avail = sum(available_weights)
        if total_avail == 0:
            break
        norm_weights = [w / total_avail for w in available_weights]

        chosen_idx = random.choices(range(len(available_indices)), weights=norm_weights)[0]
        selected_indices.append(available_indices[chosen_idx])

        # Remove from available
        del available_indices[chosen_idx]
        del available_weights[chosen_idx]

    return [PRODUCTS[i] for i in selected_indices]


def generate_transaction(store_id: str, date: datetime, seq: int, day_num: int,
                         store_tier: Dict) -> List[Dict]:
    """Generate a single transaction (which may have multiple line items)"""
    transaction_id = generate_transaction_id(store_id, date, seq)
    customer_id = generate_customer_id()

    # Random time during business hours (9am - 9pm)
    hour = random.randint(9, 20)
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    timestamp = date.replace(hour=hour, minute=minute, second=second)

    payment_method = random.choices(PAYMENT_METHODS, weights=PAYMENT_WEIGHTS)[0]

    # Select products for this transaction
    products = select_products_for_transaction(date, day_num)

    records = []
    for product in products:
        quantity = random.choices([1, 2, 3, 4], weights=[0.60, 0.25, 0.10, 0.05])[0]

        # Apply store tier value multiplier to pricing (premium locations can charge more)
        unit_price = round(product["price"] * store_tier["value_mult"], 2)
        line_total = round(unit_price * quantity, 2)

        # Random discount (80% chance of no discount, 15% small discount, 5% bigger discount)
        discount_choice = random.choices(
            [0, 1, 2],
            weights=[0.80, 0.15, 0.05]
        )[0]

        if discount_choice == 1:
            discount_amount = round(line_total * random.uniform(0.05, 0.10), 2)
        elif discount_choice == 2:
            discount_amount = round(line_total * random.uniform(0.15, 0.25), 2)
        else:
            discount_amount = 0.0

        records.append({
            "transaction_id": transaction_id,
            "transaction_timestamp": timestamp.isoformat() + "Z",
            "item_sku": product["sku"],
            "item_name": product["name"],
            "quantity": quantity,
            "unit_price": unit_price,
            "line_total": line_total,
            "discount_amount": discount_amount,
            "payment_method": payment_method,
            "customer_id": customer_id
        })

    return records


def generate_store_day_data(store_id: str, date: datetime, day_num: int) -> List[Dict]:
    """Generate all transactions for a store for a single day"""
    store_tier = STORE_TIERS[store_id]

    # Calculate number of transactions
    dow_mult = get_day_of_week_multiplier(date)
    monthly_mult = get_monthly_trend(day_num)
    store_mult = store_tier["transactions_mult"]

    # Base with multipliers and random variation (+/- 20%)
    base_transactions = BASE_TRANSACTIONS_PER_DAY * dow_mult * monthly_mult * store_mult
    random_variation = random.uniform(0.80, 1.20)
    num_transactions = int(base_transactions * random_variation)

    # Generate all transactions
    all_records = []
    for seq in range(1, num_transactions + 1):
        records = generate_transaction(store_id, date, seq, day_num, store_tier)
        all_records.extend(records)

    # Sort by timestamp
    all_records.sort(key=lambda x: x["transaction_timestamp"])

    return all_records


def main():
    """Generate all sample data files"""
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Track statistics
    total_files = 0
    total_transactions = 0
    total_records = 0

    print(f"Generating {NUM_DAYS} days of data for {NUM_STORES} stores...")
    print(f"Output directory: {OUTPUT_DIR}/")
    print("-" * 60)

    for day_offset in range(NUM_DAYS):
        date = START_DATE + timedelta(days=day_offset)
        day_num = day_offset + 1
        dow_name = date.strftime("%A")

        print(f"\nDay {day_num:2d} - {date.strftime('%Y-%m-%d')} ({dow_name})")

        day_transactions = 0
        day_records = 0

        for store_num in range(1, NUM_STORES + 1):
            store_id = f"{store_num:04d}"

            # Generate data
            records = generate_store_day_data(store_id, date, day_num)

            # Count unique transactions
            unique_txns = len(set(r["transaction_id"] for r in records))

            # Create filename
            filename = f"store_{store_id}_{date.strftime('%Y-%m-%d')}.json"
            filepath = os.path.join(OUTPUT_DIR, filename)

            # Write file
            with open(filepath, 'w') as f:
                json.dump(records, f, indent=2)

            day_transactions += unique_txns
            day_records += len(records)
            total_files += 1

        total_transactions += day_transactions
        total_records += day_records

        print(f"  Generated {NUM_STORES} files | {day_transactions:,} transactions | {day_records:,} line items")

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total files generated: {total_files}")
    print(f"Total transactions: {total_transactions:,}")
    print(f"Total line items: {total_records:,}")
    print(f"Average transactions per store per day: {total_transactions / (NUM_STORES * NUM_DAYS):.0f}")
    print(f"Average line items per transaction: {total_records / total_transactions:.2f}")
    print(f"\nFiles saved to: {os.path.abspath(OUTPUT_DIR)}/")


if __name__ == "__main__":
    main()
