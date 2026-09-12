"""
Auntie Aloha Dashboard - 13-Week Cash Flow & Runway Engine
Simulates rolling weekly cash inflows and outflows with scenario stress-testing.
"""

import datetime
from typing import Dict, List, Any
import pandas as pd
import numpy as np


def generate_13_week_forecast(
    starting_cash: float = 14000.0,
    base_biweekly_nabis: float = 2200.0,
    sales_growth_pct: float = 0.0,
    collection_lag_weeks: int = 0,
    tpo_monthly_royalty: float = 5000.0,
    hawaii_quarterly_royalty: float = 4000.0,
    include_hawaii: bool = True,
    smoakland_batch_cost: float = 32000.0,
    smoakland_run_week: int = 6,
    mygreen_batch_cost: float = 8500.0,
    mygreen_run_week: int = 10,
    luis_commission_rate: float = 0.12,
    fixed_weekly_opex: float = 450.0,
    nabis_monthly_software: float = 780.15,
) -> pd.DataFrame:
    """
    Computes a 13-week detailed cash flow projection.
    Returns a dataframe with weekly breakdown and summary metrics.
    """
    today = datetime.date.today()
    # Align to nearest Monday
    start_monday = today - datetime.timedelta(days=today.weekday())
    
    weeks = []
    current_balance = float(starting_cash)
    growth_multiplier = 1.0 + (sales_growth_pct / 100.0)

    for w in range(1, 14):
        week_date = start_monday + datetime.timedelta(weeks=w - 1)
        week_label = f"W{w:02d} ({week_date.strftime('%b %d')})"
        
        # 1. Inflows
        # Nabis remits bi-weekly (weeks 2, 4, 6, 8, 10, 12, adjusted for lag)
        effective_week = w - collection_lag_weeks
        is_remittance_week = (effective_week > 0) and (effective_week % 2 == 0)
        
        nabis_inflow = (base_biweekly_nabis * growth_multiplier) if is_remittance_week else 0.0
        
        # Royalties: TPO arrives monthly (~weeks 1, 5, 9, 13)
        tpo_inflow = tpo_monthly_royalty if (w in [1, 5, 9, 13]) else 0.0
        
        # Hawaii arrives quarterly (~week 4)
        hawaii_inflow = hawaii_quarterly_royalty if (include_hawaii and w == 4) else 0.0
        
        total_inflow = nabis_inflow + tpo_inflow + hawaii_inflow
        
        # 2. Outflows
        # Manufacturing runs
        mfg_smoakland = smoakland_batch_cost if (w == smoakland_run_week) else 0.0
        mfg_mygreen = mygreen_batch_cost if (w == mygreen_run_week) else 0.0
        
        # Nabis monthly software fee ($780.15 charged roughly week 2, 6, 10)
        software_fee = nabis_monthly_software if (w in [2, 6, 10]) else 0.0
        
        # Luis commission is ~12% on wholesale sales (tied to remittance weeks)
        luis_commission = (nabis_inflow * luis_commission_rate) if nabis_inflow > 0 else 0.0
        
        # Fixed OPEX (admin, legal, storage, misc)
        opex = fixed_weekly_opex
        
        total_outflow = mfg_smoakland + mfg_mygreen + software_fee + luis_commission + opex
        
        net_cash_flow = total_inflow - total_outflow
        ending_balance = current_balance + net_cash_flow
        
        weeks.append({
            "week_num": w,
            "week_label": week_label,
            "week_start": week_date,
            "starting_cash": current_balance,
            "nabis_inflow": nabis_inflow,
            "tpo_royalty": tpo_inflow,
            "hawaii_royalty": hawaii_inflow,
            "total_inflow": total_inflow,
            "mfg_smoakland": mfg_smoakland,
            "mfg_mygreen": mfg_mygreen,
            "nabis_software": software_fee,
            "luis_commission": luis_commission,
            "opex": opex,
            "total_outflow": total_outflow,
            "net_cash_flow": net_cash_flow,
            "ending_cash": ending_balance,
        })
        
        current_balance = ending_balance
        
    df = pd.DataFrame(weeks)
    return df


def calculate_cash_runway_metrics(forecast_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Computes summary metrics: lowest cash point, week of lowest point,
    cash runway in weeks, and total burn/surplus over 13 weeks.
    """
    min_cash = forecast_df["ending_cash"].min()
    min_week_row = forecast_df.loc[forecast_df["ending_cash"].idxmin()]
    
    # Runway: first week where ending cash < 0, or >13 if always positive
    negative_weeks = forecast_df[forecast_df["ending_cash"] < 0]
    if not negative_weeks.empty:
        runway_weeks = int(negative_weeks.iloc[0]["week_num"]) - 1
        is_critical = True
    else:
        runway_weeks = 13
        is_critical = False
        
    total_inflows = forecast_df["total_inflow"].sum()
    total_outflows = forecast_df["total_outflow"].sum()
    net_13_weeks = total_inflows - total_outflows
    
    return {
        "starting_cash": forecast_df.iloc[0]["starting_cash"],
        "ending_cash_13w": forecast_df.iloc[-1]["ending_cash"],
        "min_cash_balance": min_cash,
        "trough_week": min_week_row["week_label"],
        "runway_weeks": runway_weeks,
        "is_critical": is_critical,
        "total_inflows": total_inflows,
        "total_outflows": total_outflows,
        "net_13_weeks": net_13_weeks,
    }
