"""
Auntie Aloha Dashboard - Inventory & Reorder Engine
Tracks stock on hand, depletion run rates, days of supply, batch reorder triggers, and SKU aggregation.
"""

import datetime
from typing import Dict, List, Any
import pandas as pd


def compute_inventory_health(
    inventory_df: pd.DataFrame,
    lead_time_weeks: int = 5,
    safety_stock_weeks: int = 2,
) -> pd.DataFrame:
    """
    Evaluates inventory status, Days of Inventory on Hand (DOH),
    and suggests reorder dates based on production lead time and safety stock.
    """
    if inventory_df.empty:
        return inventory_df.copy()

    df = inventory_df.copy()
    
    # Ensure numeric columns
    numeric_cols = [
        "units_on_hand", "units_reserved", "units_available",
        "units_incoming", "units_quarantined",
        "weekly_velocity", "weeks_on_hand", "batch_cost", "wholesale_price"
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
        else:
            df[col] = 0.0

    # Valuation
    df["cogs_valuation"] = (df["units_available"] * df["batch_cost"]).round(2)
    df["wholesale_valuation"] = (df["units_available"] * df["wholesale_price"]).round(2)

    # Reorder threshold in units
    df["safety_stock_units"] = (df["weekly_velocity"] * safety_stock_weeks).round(0)
    df["reorder_point_units"] = (df["weekly_velocity"] * (lead_time_weeks + safety_stock_weeks)).round(0)
    
    # Days and weeks of supply
    df["daily_velocity"] = df["weekly_velocity"] / 7.0
    
    def calc_weeks_supply(row):
        avail = row["units_available"]
        vel = row["weekly_velocity"]
        woh = row.get("weeks_on_hand", 0.0)
        if avail <= 0:
            return 0.0
        if vel > 0:
            return round(avail / vel, 1)
        if woh > 0:
            return round(woh, 1)
        return 99.0

    def calc_days_supply(row):
        w = calc_weeks_supply(row)
        return round(w * 7.0, 1)

    df["weeks_of_supply"] = df.apply(calc_weeks_supply, axis=1)
    df["days_of_supply"] = df.apply(calc_days_supply, axis=1)

    # Days until reorder must be initiated
    today = datetime.date.today()

    def get_reorder_date(row):
        if row.get("is_obsolete", False):
            rep = row.get("replacement_sku", "")
            return f"Discontinued (Replaced by {rep})" if rep else "Discontinued"
        avail = row["units_available"]
        vel = row["weekly_velocity"]
        if avail <= 0:
            return "Out of Stock"
        if vel <= 0:
            return "No Active Velocity"
        
        daily_vel = vel / 7.0
        # days until stock hits safety stock
        days_until_trigger = (avail - row["safety_stock_units"]) / daily_vel
        # reorder needed lead_time_weeks before safety stock
        days_until_action = days_until_trigger - (lead_time_weeks * 7)
        if days_until_action <= 0:
            return "IMMEDIATE (Past Due)"
        target_date = today + datetime.timedelta(days=int(days_until_action))
        return target_date.strftime("%b %d, %Y")

    df["reorder_trigger_date"] = df.apply(get_reorder_date, axis=1)

    # Status classification
    def classify_status(row):
        if row.get("is_obsolete", False):
            return "⚪ Discontinued / Superseded"
        avail = row["units_available"]
        if avail <= 0:
            return "⚫ Depleted / Out of Stock"
        
        w = row["weeks_of_supply"]
        if w < lead_time_weeks:
            return "🔴 Critical Stockout Risk"
        elif w < (lead_time_weeks + safety_stock_weeks):
            return "🟡 Reorder Now (In Lead-Time)"
        elif w <= 25:
            return "🟢 Healthy Stock"
        else:
            return "🔵 Well Stocked"

    df["inventory_status"] = df.apply(classify_status, axis=1)
    return df


def aggregate_inventory_by_sku(
    inventory_df: pd.DataFrame,
    lead_time_weeks: int = 5,
    safety_stock_weeks: int = 2,
) -> pd.DataFrame:
    """
    Consolidates inventory records by SKU, aggregating batch quantities,
    computing overall velocity, supply runway, and combined valuations.
    """
    if inventory_df.empty:
        return pd.DataFrame()

    df = inventory_df.copy()

    # Ensure required columns exist
    for col in ["units_on_hand", "units_reserved", "units_available", "weekly_velocity", "weeks_on_hand", "batch_cost", "wholesale_price"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
        else:
            df[col] = 0.0

    if "product_name" not in df.columns:
        df["product_name"] = df["sku"]
    if "category" not in df.columns:
        df["category"] = "Gummies"
    if "manufacturer" not in df.columns:
        df["manufacturer"] = "Standard"
    if "is_sample" not in df.columns:
        df["is_sample"] = False
    if "is_obsolete" not in df.columns:
        df["is_obsolete"] = False
    if "replacement_sku" not in df.columns:
        df["replacement_sku"] = ""
    if "batch_code" not in df.columns:
        df["batch_code"] = "--"
    if "expiration_date" not in df.columns:
        df["expiration_date"] = "--"

    def format_batches(series):
        valid = sorted(list(set(str(b).strip() for b in series if str(b).strip() not in ["--", "nan", "None", ""])))
        return ", ".join(valid) if valid else "--"

    def format_earliest_exp(series):
        valid = [str(e).strip() for e in series if str(e).strip() not in ["--", "nan", "None", ""]]
        return min(valid) if valid else "--"

    grouped = df.groupby("sku", as_index=False).agg({
        "product_name": "first",
        "category": "first",
        "manufacturer": "first",
        "is_sample": "first",
        "is_obsolete": "first",
        "replacement_sku": "first",
        "units_available": "sum",
        "units_reserved": "sum",
        "units_on_hand": "sum",
        "weekly_velocity": "max",
        "weeks_on_hand": "max",
        "batch_cost": "first",
        "wholesale_price": "first",
        "batch_code": format_batches,
        "expiration_date": format_earliest_exp,
    })

    # Evaluate health on aggregated data
    agg_df = compute_inventory_health(grouped, lead_time_weeks=lead_time_weeks, safety_stock_weeks=safety_stock_weeks)
    return agg_df

