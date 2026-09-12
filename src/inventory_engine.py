"""
Auntie Aloha Dashboard - Inventory & Reorder Engine
Tracks stock on hand, depletion run rates, days of supply, and batch reorder triggers.
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
    df = inventory_df.copy()
    
    # Ensure numeric columns
    for col in ["units_on_hand", "units_reserved", "units_available", "weekly_velocity", "batch_cost", "wholesale_price"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    # Reorder threshold in units
    df["safety_stock_units"] = (df["weekly_velocity"] * safety_stock_weeks).round(0)
    df["reorder_point_units"] = (df["weekly_velocity"] * (lead_time_weeks + safety_stock_weeks)).round(0)
    
    # Days and weeks of supply
    df["daily_velocity"] = df["weekly_velocity"] / 7.0
    df["days_of_supply"] = df.apply(
        lambda r: round(r["units_available"] / r["daily_velocity"], 1) if r["daily_velocity"] > 0 else 999.0,
        axis=1,
    )
    df["weeks_of_supply"] = df.apply(
        lambda r: round(r["units_available"] / r["weekly_velocity"], 1) if r["weekly_velocity"] > 0 else 99.0,
        axis=1,
    )

    # Days until reorder must be initiated
    today = datetime.date.today()
    def get_reorder_date(row):
        if row["daily_velocity"] <= 0:
            return "N/A"
        # days until stock hits safety stock
        days_until_trigger = (row["units_available"] - row["safety_stock_units"]) / row["daily_velocity"]
        # reorder needed lead_time_weeks before safety stock
        days_until_action = days_until_trigger - (lead_time_weeks * 7)
        if days_until_action <= 0:
            return "IMMEDIATE (Past Due)"
        target_date = today + datetime.timedelta(days=int(days_until_action))
        return target_date.strftime("%b %d, %Y")

    df["reorder_trigger_date"] = df.apply(get_reorder_date, axis=1)

    # Status classification
    def classify_status(row):
        w = row["weeks_of_supply"]
        if w < lead_time_weeks:
            return "🔴 Critical Stockout Risk"
        elif w < (lead_time_weeks + safety_stock_weeks):
            return "🟡 Reorder Now (In Lead-Time)"
        elif w < (lead_time_weeks + safety_stock_weeks + 4):
            return "🟢 Healthy Stock"
        else:
            return "🔵 High / Overstocked"

    df["inventory_status"] = df.apply(classify_status, axis=1)
    
    # Valuation
    df["cogs_valuation"] = (df["units_available"] * df["batch_cost"]).round(2)
    df["wholesale_valuation"] = (df["units_available"] * df["wholesale_price"]).round(2)
    
    return df
