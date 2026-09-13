"""
Auntie Aloha Dashboard - Inventory & Reorder Engine
Tracks stock on hand, depletion run rates, days of supply, batch reorder triggers, and SKU aggregation.
"""

import datetime
import re
from typing import Dict, List, Any
import pandas as pd


def is_obsolete_sku(row_or_dict) -> bool:
    """
    Identifies whether an item is a discontinued / superseded legacy SKU (e.g., 739X series).
    """
    if bool(row_or_dict.get("is_obsolete", False)):
        return True
    sku_val = str(row_or_dict.get("sku", "")).strip().upper()
    prod_val = str(row_or_dict.get("product_name", "")).strip().upper()

    if bool(re.match(r"^739\d", sku_val)) or sku_val in ["7391", "7392", "7393", "7394", "7395"]:
        return True
    if prod_val in ["PAKALOLO POG", "OG LAVA FLOW", "HANALEI HIGH TIDE", "LILIKOI CITRUS BUZZ", "HAWAIIAN GUAVA HAZE"]:
        return True
    return False


def is_active_commercial_sku(row_or_dict) -> bool:
    """
    Returns True only for active commercial SKUs (excludes promotional samples and discontinued/obsolete lines).
    """
    if bool(row_or_dict.get("is_sample", False)):
        return False
    sku_val = str(row_or_dict.get("sku", "")).strip().upper()
    prod_val = str(row_or_dict.get("product_name", "")).strip().upper()
    if "SAMPLE" in sku_val or "SAMPLE" in prod_val:
        return False
    if is_obsolete_sku(row_or_dict):
        return False
    return True


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

    # Dynamic Obsolete SKU Tagging (guarantees obsolete status even with stale cached data)
    if "is_obsolete" not in df.columns:
        df["is_obsolete"] = False
    if "replacement_sku" not in df.columns:
        df["replacement_sku"] = ""

    legacy_map = {
        "7391": "AA-PakaloloPOG-I-10mg-10pc-Bag",
        "7392": "AA-HanaleiHighTide-S-10mg-10pc-Bag",
        "7393": "AA-LilikoiCitrusBuzz-S-10mg-10pc-Bag",
        "7394": "AA-HawaiianGuavaHaze-I-10mg-10pc-Bag",
        "7395": "AA-OGLavaFlow-H-10mg-10pc-Bag",
    }
    for idx, row in df.iterrows():
        sku_val = str(row.get("sku", "")).strip()
        is_obs = is_obsolete_sku(row)
        rep = str(row.get("replacement_sku", "") or "")

        for leg, target in legacy_map.items():
            if sku_val == leg or sku_val.startswith(f"{leg}-"):
                is_obs = True
                rep = target
                break
        if not rep and is_obs:
            rep = legacy_map.get(sku_val, "")

        if is_obs:
            df.at[idx, "is_obsolete"] = True
            df.at[idx, "replacement_sku"] = rep
            df.at[idx, "weekly_velocity"] = 0.0
            df.at[idx, "weeks_on_hand"] = 0.0
    
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
        if row.get("is_obsolete", False) or is_obsolete_sku(row):
            return 99.0
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

    def calc_pipeline_weeks_supply(row):
        if row.get("is_obsolete", False) or is_obsolete_sku(row):
            return 99.0
        tot = row["units_available"] + row.get("units_incoming", 0.0)
        vel = row["weekly_velocity"]
        if tot <= 0:
            return 0.0
        if vel > 0:
            return round(tot / vel, 1)
        return 99.0

    df["weeks_of_supply"] = df.apply(calc_weeks_supply, axis=1)
    df["pipeline_weeks_of_supply"] = df.apply(calc_pipeline_weeks_supply, axis=1)
    df["days_of_supply"] = df.apply(calc_days_supply, axis=1)

    # Days until reorder must be initiated
    today = datetime.date.today()

    def get_reorder_date(row):
        if row.get("is_obsolete", False) or is_obsolete_sku(row):
            rep = row.get("replacement_sku", "")
            return f"Discontinued (Replaced by {rep})" if rep else "Discontinued"
        avail = row["units_available"]
        vel = row["weekly_velocity"]
        inc = row.get("units_incoming", 0.0)
        pipe_w = row.get("pipeline_weeks_of_supply", 0.0)
        if avail <= 0 and inc <= 0:
            return "Out of Stock"
        if vel <= 0:
            return "No Active Velocity"
        if inc > 0 and pipe_w >= (lead_time_weeks + safety_stock_weeks):
            return "PO Placed (In Production)"
        
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
        if row.get("is_obsolete", False) or is_obsolete_sku(row):
            return "⚪ Discontinued / Superseded"
        avail = row["units_available"]
        inc = row.get("units_incoming", 0.0)
        if avail <= 0 and inc <= 0:
            return "⚫ Depleted / Out of Stock"
        
        w = row["weeks_of_supply"]
        pipe_w = row.get("pipeline_weeks_of_supply", w)

        if w < lead_time_weeks:
            if pipe_w >= (lead_time_weeks + safety_stock_weeks):
                return "🟢 Covered by Incoming PO"
            return "🔴 Critical Stockout Risk"
        elif w < (lead_time_weeks + safety_stock_weeks):
            if pipe_w >= (lead_time_weeks + safety_stock_weeks):
                return "🟢 Covered by Incoming PO"
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

    # Pre-tag obsolete items before aggregation
    for idx, row in df.iterrows():
        if is_obsolete_sku(row):
            df.at[idx, "is_obsolete"] = True
            df.at[idx, "weekly_velocity"] = 0.0
            df.at[idx, "weeks_on_hand"] = 0.0

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
        "is_sample": "any",
        "is_obsolete": "any",
        "replacement_sku": "first",
        "units_available": "sum",
        "units_reserved": "sum",
        "units_on_hand": "sum",
        "units_incoming": "sum",
        "units_quarantined": "sum",
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

