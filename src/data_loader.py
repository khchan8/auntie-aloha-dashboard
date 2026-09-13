"""
Auntie Aloha Dashboard - Data Loader & Pipeline
Parses Nabis remittances (2025-YTD), Nabis orders/inventory, QuickBooks exports, and budget models.
"""

import os
import glob
import re
import datetime
from typing import Dict, List, Optional, Tuple
import pandas as pd
import openpyxl

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def parse_nabis_remittance_file(file_path: str) -> Tuple[pd.DataFrame, Dict]:
    """
    Parses a single Nabis remittance Excel workbook.
    Extracts raw line items and metadata (period dates, net remittance, fees).
    """
    fname = os.path.basename(file_path)
    wb = openpyxl.load_workbook(file_path, data_only=True)
    
    # 1. Detect target raw sheet
    raw_sheet_name = None
    for name in wb.sheetnames:
        lower = name.lower()
        if "raw" in lower or "auntie" in lower or "rrn" in lower:
            raw_sheet_name = name
            break
    if not raw_sheet_name:
        raw_sheet_name = wb.sheetnames[0]
        
    ws_raw = wb[raw_sheet_name]
    
    # Find header row
    hdr_row = 1
    headers = []
    for r in range(1, min(10, ws_raw.max_row + 1)):
        row_vals = [str(ws_raw.cell(r, c).value or "").strip() for c in range(1, ws_raw.max_column + 1)]
        if any("Paid Date" in v or "Order Number" in v for v in row_vals):
            hdr_row = r
            headers = row_vals
            break
            
    col_map = {h: i + 1 for i, h in enumerate(headers) if h}
    
    records = []
    for r in range(hdr_row + 1, ws_raw.max_row + 1):
        def get_val(col_name, default=None):
            idx = col_map.get(col_name)
            return ws_raw.cell(r, idx).value if idx else default

        def get_float(col_name):
            val = get_val(col_name, 0.0)
            try:
                if val is None:
                    return 0.0
                return float(val)
            except (ValueError, TypeError):
                return 0.0

        dispensary = str(get_val("Licensed Location Name", "") or "").strip()
        order_num = str(get_val("Order Number", "") or "").strip()
        inv_type = str(get_val("Invoice Type", "") or "").strip()
        paid_date = get_val("Paid Date")
        applied_date = get_val("Applied Date")
        
        nabis_collected = get_float("Nabis Collected")
        nabis_kept = get_float("Nabis Kept")
        nabis_remitted = get_float("Nabis Remitted to Brand")
        order_total = get_float("Order Total")
        inv_total = get_float("Invoice Total")
        
        # Categorize invoice / fee type
        inv_lower = inv_type.lower()
        if "due to processor" in inv_lower:
            fee_category = "Net Remittance to Brand"
        elif "fulfillment" in inv_lower:
            fee_category = "Distribution Fulfillment"
        elif "fuel" in inv_lower:
            fee_category = "Fuel Surcharge"
        elif "software" in inv_lower:
            fee_category = "Software Subscription"
        elif "case break" in inv_lower:
            fee_category = "Case Break Fee"
        elif "labeling" in inv_lower:
            fee_category = "Labeling Fee"
        elif "sample" in inv_lower or "trade" in inv_lower:
            fee_category = "Sample Order Fee"
        else:
            fee_category = "Other / Adjustments"

        # Format dates
        if isinstance(paid_date, datetime.datetime):
            paid_date = paid_date.date()
        if isinstance(applied_date, datetime.datetime):
            applied_date = applied_date.date()

        if order_num or inv_type or dispensary or nabis_collected != 0 or nabis_remitted != 0:
            records.append({
                "source_file": fname,
                "paid_date": paid_date,
                "applied_date": applied_date,
                "dispensary": dispensary,
                "order_number": order_num,
                "po_so_number": str(get_val("PO/SO Number", "") or "").strip(),
                "invoice_number": str(get_val("Invoice Number", "") or "").strip(),
                "invoice_type": inv_type,
                "fee_category": fee_category,
                "transaction_type": str(get_val("Transaction Type", "") or "").strip(),
                "order_total": order_total,
                "invoice_total": inv_total,
                "nabis_collected": nabis_collected,
                "nabis_kept": nabis_kept,
                "nabis_remitted": nabis_remitted,
            })
            
    df = pd.DataFrame(records)
    
    # 2. Extract metadata / period dates
    metadata = {
        "file": fname,
        "start_date": None,
        "end_date": None,
        "total_collected": float(df["nabis_collected"].sum()) if not df.empty else 0.0,
        "total_kept": float(df["nabis_kept"].sum()) if not df.empty else 0.0,
        "total_remitted": float(df["nabis_remitted"].sum()) if not df.empty else 0.0,
        "software_fee": float(df[df["fee_category"] == "Software Subscription"]["nabis_kept"].sum()) if not df.empty else 0.0,
    }
    
    # Check if 'Remittance Export' sheet exists for explicit dates
    if "Remittance Export" in wb.sheetnames:
        ws_meta = wb["Remittance Export"]
        for r in range(1, 10):
            val1 = str(ws_meta.cell(r, 2).value or "")
            if "Period Start Date" in val1:
                metadata["start_date"] = ws_meta.cell(r, 3).value
            elif "Period End Date" in val1:
                metadata["end_date"] = ws_meta.cell(r, 3).value
                
    # Fallback to filename regex for dates (e.g. 0106-01182025 or 2026-08-03_2026-08-15)
    if not metadata["start_date"]:
        match_iso = re.search(r"(\d{4}-\d{2}-\d{2})_(\d{4}-\d{2}-\d{2})", fname)
        if match_iso:
            metadata["start_date"] = match_iso.group(1)
            metadata["end_date"] = match_iso.group(2)
        else:
            match_mdy = re.search(r"(\d{2})(\d{2})-(\d{2})(\d{2})(\d{4})", fname)
            if match_mdy:
                m1, d1, m2, d2, y = match_mdy.groups()
                metadata["start_date"] = f"{y}-{m1}-{d1}"
                metadata["end_date"] = f"{y}-{m2}-{d2}"
                
    if metadata["start_date"] and isinstance(metadata["start_date"], (datetime.datetime, datetime.date)):
        metadata["start_date"] = str(metadata["start_date"])[:10]
    if metadata["end_date"] and isinstance(metadata["end_date"], (datetime.datetime, datetime.date)):
        metadata["end_date"] = str(metadata["end_date"])[:10]

    return df, metadata


def load_all_nabis_remittances(base_dir: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Scans base_dir for all Nabis remittance XLSX files (including 2025, 2026 subdirs).
    Returns (raw_transactions_df, biweekly_summary_df).
    """
    pattern = os.path.join(base_dir, "**", "*.xlsx")
    files = glob.glob(pattern, recursive=True)
    # Filter out cashflow model itself
    remittance_files = [f for f in files if "cashflow" not in os.path.basename(f).lower() and not os.path.basename(f).startswith("~$")]
    
    all_rows = []
    summaries = []
    
    for f in sorted(remittance_files):
        try:
            df, meta = parse_nabis_remittance_file(f)
            if not df.empty:
                all_rows.append(df)
            summaries.append(meta)
        except Exception as e:
            print(f"Warning: Failed to parse {f}: {e}")
            
    if all_rows:
        raw_df = pd.concat(all_rows, ignore_index=True)
    else:
        raw_df = pd.DataFrame()
        
    summary_df = pd.DataFrame(summaries)
    if not summary_df.empty and "start_date" in summary_df.columns:
        summary_df["start_date"] = pd.to_datetime(summary_df["start_date"], errors="coerce")
        summary_df = summary_df.sort_values("start_date").reset_index(drop=True)
        summary_df["realization_pct"] = (summary_df["total_remitted"] / summary_df["total_collected"].replace(0, float("nan"))) * 100
        summary_df["realization_pct"] = summary_df["realization_pct"].fillna(0)
        
    return raw_df, summary_df


def load_budget_cashflow_model(file_path: str) -> Dict[str, pd.DataFrame]:
    """
    Loads baseline budget, income, expenses, and summary projections from
    'Auntie Aloha Cashflow Model.xlsx'.
    """
    wb = openpyxl.load_workbook(file_path, data_only=True)
    
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    
    # 1. Income tab
    income_records = []
    if "Income" in wb.sheetnames:
        ws_inc = wb["Income"]
        for r in range(2, ws_inc.max_row + 1):
            category = str(ws_inc.cell(r, 2).value or "").strip()
            item_name = str(ws_inc.cell(r, 5).value or "").strip()
            if not item_name and not category:
                continue
            name = item_name if item_name else category
            values = [float(ws_inc.cell(r, c).value or 0.0) for c in range(6, 18)]
            if any(v != 0 for v in values) or item_name:
                row_dict = {"Category": category, "Stream": name}
                for m_idx, m_name in enumerate(month_names):
                    row_dict[m_name] = values[m_idx] if m_idx < len(values) else 0.0
                income_records.append(row_dict)
                
    income_df = pd.DataFrame(income_records)
    
    # 2. Expenses tab
    expense_records = []
    if "Expenses" in wb.sheetnames:
        ws_exp = wb["Expenses"]
        for r in range(2, ws_exp.max_row + 1):
            category = str(ws_exp.cell(r, 2).value or "").strip()
            item_name = str(ws_exp.cell(r, 5).value or "").strip()
            if not item_name and not category:
                continue
            name = item_name if item_name else category
            values = [float(ws_exp.cell(r, c).value or 0.0) for c in range(6, 18)]
            if any(v != 0 for v in values) or item_name:
                row_dict = {"Category": category, "Expense": name}
                for m_idx, m_name in enumerate(month_names):
                    row_dict[m_name] = values[m_idx] if m_idx < len(values) else 0.0
                expense_records.append(row_dict)
                
    expense_df = pd.DataFrame(expense_records)
    
    # 3. Starting Balance
    starting_balance = 14000.0
    if "Setup" in wb.sheetnames:
        ws_setup = wb["Setup"]
        for r in range(1, 15):
            val = str(ws_setup.cell(r, 2).value or "")
            if "Starting balance" in val:
                try:
                    starting_balance = float(ws_setup.cell(r, 3).value or 14000.0)
                except:
                    pass
                    
    return {
        "starting_balance": starting_balance,
        "income": income_df,
        "expenses": expense_df,
    }


def parse_nabis_inventory_export(file_or_buffer) -> pd.DataFrame:
    """
    Parses a Nabis inventory CSV or Excel export.
    Uses an advanced Smart Fuzzy Matcher to automatically identify and extract:
    - SKU Code & Product Name
    - Available, Total On-Hand, Packed/Reserved, Incoming, Quarantined units
    - Weekly Velocity (trailing 4-week sales average) & Weeks on Hand (WOH)
    - Batch/Lot Code & Expiration Dates
    - Wholesale Price, Sample tags, and Warehouse Facilities (Woodlake, Oakland, LA)
    """
    try:
        if hasattr(file_or_buffer, "name"):
            fname = file_or_buffer.name.lower()
            if fname.endswith(".csv"):
                df_raw = pd.read_csv(file_or_buffer)
            else:
                df_raw = pd.read_excel(file_or_buffer)
        elif isinstance(file_or_buffer, str):
            if file_or_buffer.lower().endswith(".csv"):
                df_raw = pd.read_csv(file_or_buffer)
            else:
                df_raw = pd.read_excel(file_or_buffer)
        else:
            df_raw = pd.DataFrame(file_or_buffer)

        # Build case-insensitive column map
        col_map = {orig: str(orig).strip().lower() for orig in df_raw.columns}

        def find_col(exact_candidates, fallback_substrings=None, exclude_prefixes=None):
            # 1. Exact matches first across candidates
            for cand in exact_candidates:
                target = cand.lower().strip()
                for orig, clean in col_map.items():
                    if clean == target:
                        return orig
            # 2. Substring matches with optional exclusions (avoids picking hub-specific cols like oak_vel)
            if fallback_substrings:
                for cand in fallback_substrings:
                    target = cand.lower().strip()
                    for orig, clean in col_map.items():
                        if exclude_prefixes and any(clean.startswith(p.lower()) for p in exclude_prefixes):
                            continue
                        if target in clean:
                            return orig
            return None

        # Hub prefixes to exclude when searching for brand-wide aggregate columns
        hub_prefixes = ["oak_", "la_", "woodlake_", "oakland_", "los_angeles_"]

        col_sku = find_col(
            ["sku_code", "sku", "sku code", "item_code", "item code", "code", "upc"],
            ["sku", "item_code", "code"]
        )
        col_product = find_col(
            ["sku_name", "product_name", "product name", "item_name", "item name", "description", "title", "product"],
            ["sku_name", "product_name", "item_name", "description", "title"]
        )
        col_avail = find_col(
            ["total_available", "units_available", "available", "available_units", "total available"],
            ["total_available", "available"],
            exclude_prefixes=hub_prefixes
        )
        col_total = find_col(
            ["total_count", "total_units", "units_on_hand", "total on hand", "quantity_on_hand", "qty on hand", "total_on_hand"],
            ["total_count", "units_on_hand", "on_hand"],
            exclude_prefixes=hub_prefixes
        )
        col_packed = find_col(
            ["total_packed", "units_reserved", "units_packed", "total packed", "reserved", "allocated", "packed"],
            ["total_packed", "packed", "reserved"],
            exclude_prefixes=hub_prefixes
        )
        col_incoming = find_col(
            ["total_incoming", "incoming_units", "total incoming", "incoming"],
            ["incoming"],
            exclude_prefixes=hub_prefixes
        )
        col_quarantined = find_col(
            ["total_quarantined", "quarantined_units", "total quarantined", "quarantined"],
            ["quarantined", "hold"],
            exclude_prefixes=hub_prefixes
        )
        col_price = find_col(
            ["sku_price_per_unit", "wholesale_price", "wholesale price", "price per unit", "price", "unit price"],
            ["price_per_unit", "wholesale_price", "unit_price"]
        )
        col_woh = find_col(
            ["weeks_on_hand", "weeks on hand", "woh"],
            ["weeks_on_hand", "weeksonhand", "woh"],
            exclude_prefixes=hub_prefixes
        )
        col_vel = find_col(
            ["trailing_4_weeks_sales_avg", "weekly_velocity", "avg_weekly_volume", "sales_avg", "weekly velocity"],
            ["trailing_4_weeks", "weekly_velocity", "weekly_volume", "trailing4weekssalesavg", "velocity"],
            exclude_prefixes=hub_prefixes
        )
        col_sample = find_col(
            ["sku_is_sample", "is_sample", "sample"],
            ["is_sample", "sample"]
        )
        col_batch = find_col(
            ["batch_code", "batch code", "batch", "lot", "lot number", "batch number", "lot_number", "lot_code"],
            ["batch_code", "batch", "lot"]
        )
        col_exp = find_col(
            ["batch_expiration_date", "expiration date", "expiration", "exp date", "expiry", "batch_exp_date"],
            ["expiration", "exp_date", "expiry"]
        )
        col_woodlake = find_col(
            ["woodlake_available", "woodlake_count", "woodlake"],
            ["woodlake_available", "woodlake"]
        )
        col_oak = find_col(
            ["oak_available", "oakland_available", "oakland"],
            ["oak_available", "oakland"]
        )
        col_la = find_col(
            ["la_commerce_available", "la_available", "los_angeles_available", "la_commerce"],
            ["la_commerce_available", "la_available"]
        )
        col_whs_generic = find_col(
            ["warehouse", "facility", "location", "hub", "site"],
            ["warehouse", "facility", "location"]
        )

        records = []
        for idx, row in df_raw.iterrows():
            prod = str(row[col_product]).strip() if col_product else f"SKU {idx+1}"
            if not prod or prod.lower() == "nan" or prod.lower() == "total":
                continue

            sku = str(row[col_sku]).strip() if col_sku else f"AA-SKU-{idx+1}"
            batch = str(row[col_batch]).strip() if col_batch and pd.notna(row[col_batch]) else "--"
            exp_date = str(row[col_exp]).strip() if col_exp and pd.notna(row[col_exp]) else "--"

            def get_num(col, default=0.0):
                if col and col in row:
                    try:
                        v = float(row[col])
                        return v if not pd.isna(v) else default
                    except (ValueError, TypeError):
                        return default
                return default

            total_count = get_num(col_total)
            avail_units = get_num(col_avail)
            packed_units = get_num(col_packed)
            incoming_units = get_num(col_incoming)
            quarantined_units = get_num(col_quarantined)
            unit_price = get_num(col_price, 6.99)
            weekly_vel = get_num(col_vel, 0.0)
            woh_val = get_num(col_woh, 0.0)

            # Reconcile unit numbers
            if avail_units == 0 and total_count > 0:
                avail_units = max(0.0, total_count - packed_units - quarantined_units)
            if total_count == 0 and avail_units > 0:
                total_count = avail_units + packed_units + quarantined_units

            # Determine sample status
            sample_val = str(row.get(col_sample, "")).strip().upper() if col_sample else ""
            is_sample = (
                sample_val.startswith("Y")
                or "SAMPLE" in sku.upper()
                or "SAMPLE" in prod.upper()
                or unit_price <= 0.05
            )

            # Determine category, manufacturer & standard COGS
            name_and_sku = f"{prod} {sku}".lower()
            if any(k in name_and_sku for k in ["rosin", "solventless", "thcv", "cbn"]):
                category = "Gummies - Solventless Rosin"
                mfg = "MyGreen Network"
                cogs = 3.80
                if unit_price <= 0.05 and not is_sample:
                    unit_price = 9.00
            else:
                category = "Gummies - Distillate"
                mfg = "Smoakland"
                cogs = 2.80
                if unit_price <= 0.05 and not is_sample:
                    unit_price = 6.99

            # Warehouse facility determination
            woodlake_qty = get_num(col_woodlake)
            oak_qty = get_num(col_oak)
            la_qty = get_num(col_la)

            if woodlake_qty > 0:
                warehouse = "Woodlake Hub"
            elif oak_qty > 0:
                warehouse = "Oakland Hub"
            elif la_qty > 0:
                warehouse = "LA Commerce Hub"
            elif col_whs_generic and str(row[col_whs_generic]).strip():
                warehouse = str(row[col_whs_generic]).strip()
            else:
                warehouse = "Woodlake Hub"

            # Obsolete / Superseded SKU Detection (e.g. 7391, 7395 replaced by alphanumeric AA-* SKUs)
            clean_sku = sku.strip()
            legacy_sku_map = {
                "7391": "AA-PakaloloPOG-I-10mg-10pc-Bag",
                "7392": "AA-HanaleiHighTide-S-10mg-10pc-Bag",
                "7393": "AA-LilikoiCitrusBuzz-S-10mg-10pc-Bag",
                "7394": "AA-HawaiianGuavaHaze-I-10mg-10pc-Bag",
                "7395": "AA-OGLavaFlow-H-10mg-10pc-Bag",
            }
            is_obsolete = False
            replacement_sku = ""
            for leg_code, rep_code in legacy_sku_map.items():
                if clean_sku == leg_code or clean_sku.startswith(f"{leg_code}-") or clean_sku.startswith(leg_code):
                    is_obsolete = True
                    replacement_sku = rep_code
                    break
            if not is_obsolete and bool(re.match(r"^739\d", clean_sku)):
                is_obsolete = True

            # If obsolete, zero out reorder velocity so it does not trigger false stockout alerts
            if is_obsolete:
                weekly_vel = 0.0
                woh_val = 0.0
                days_supply = 0.0
                status = "⚪ Discontinued / Superseded"
            else:
                # Compute depletion and status
                days_supply = round(woh_val * 7.0, 1) if woh_val > 0 else (round(avail_units / (weekly_vel / 7.0), 1) if weekly_vel > 0 else 0.0)
                if woh_val == 0.0 and weekly_vel > 0:
                    woh_val = round(avail_units / weekly_vel, 1)

                if avail_units == 0:
                    status = "⚫ Out of Stock / Depleted"
                elif woh_val < 5:
                    status = "🔴 Critical Stockout Risk"
                elif woh_val < 8:
                    status = "🟡 Reorder Soon (Lead-Time)"
                elif woh_val <= 25:
                    status = "🟢 Healthy Stock"
                else:
                    status = "🔵 Well Stocked"

            records.append({
                "sku": sku,
                "product_name": prod,
                "category": category,
                "warehouse": warehouse,
                "batch_code": batch,
                "expiration_date": exp_date,
                "units_on_hand": total_count,
                "units_reserved": packed_units,
                "units_available": avail_units,
                "units_incoming": incoming_units,
                "units_quarantined": quarantined_units,
                "weekly_velocity": weekly_vel,
                "weeks_on_hand": woh_val,
                "days_of_supply": days_supply,
                "batch_cost": cogs,
                "wholesale_price": unit_price,
                "cogs_valuation": round(avail_units * cogs, 2),
                "wholesale_valuation": round(avail_units * unit_price, 2),
                "manufacturer": mfg,
                "is_sample": is_sample,
                "is_obsolete": is_obsolete,
                "replacement_sku": replacement_sku,
                "inventory_status": status,
            })

        df_out = pd.DataFrame(records)
        return df_out
    except Exception as e:
        print(f"Error parsing Nabis inventory export: {e}")
        return pd.DataFrame()


def get_default_inventory_data() -> pd.DataFrame:
    """
    Loads latest actual Nabis Inventory report from disk if available,
    otherwise falls back to benchmark baseline data.
    """
    # 1. Search for real inventory files in Nabis Inventory folder or project root
    search_dirs = [
        os.path.join(BASE_DIR, "Nabis Inventory"),
        BASE_DIR,
    ]
    candidate_files = []
    for d in search_dirs:
        if os.path.exists(d):
            candidate_files.extend(glob.glob(os.path.join(d, "*inventory*.csv")))
            candidate_files.extend(glob.glob(os.path.join(d, "*inventory*.xlsx")))

    if candidate_files:
        # Load the latest file by modification time
        latest_file = sorted(candidate_files, key=os.path.getmtime)[-1]
        try:
            parsed_df = parse_nabis_inventory_export(latest_file)
            if not parsed_df.empty:
                return parsed_df
        except Exception as e:
            print(f"Warning: Failed to load inventory from {latest_file}: {e}")

    # 2. Hardcoded fallback if no files present
    records = [
        {
            "sku": "AA-MahinaMoon-10pc-10mg pack",
            "product_name": "Mahina Moon Yuzu Lavender CBN x Live Rosin 10mg 10pc pack",
            "category": "Gummies - Solventless Rosin",
            "warehouse": "Woodlake Hub",
            "batch_code": "AA-YL-070726",
            "expiration_date": "07/24/2027",
            "units_on_hand": 1700,
            "units_reserved": 0,
            "units_available": 1700,
            "units_incoming": 0,
            "units_quarantined": 0,
            "weekly_velocity": 125,
            "weeks_on_hand": 53,
            "days_of_supply": 371.0,
            "batch_cost": 3.80,
            "wholesale_price": 9.00,
            "cogs_valuation": 6460.0,
            "wholesale_valuation": 15300.0,
            "manufacturer": "MyGreen Network",
            "is_sample": False,
            "inventory_status": "🔵 Well Stocked",
        },
        {
            "sku": "AA-LycheeLuana-THCVLiveRosin-10mg-10pc-Bag",
            "product_name": "Lychee Luana THCV x Live Rosin 10mg 10pc pack",
            "category": "Gummies - Solventless Rosin",
            "warehouse": "Woodlake Hub",
            "batch_code": "AA-PL-042926",
            "expiration_date": "04/28/2027",
            "units_on_hand": 1184,
            "units_reserved": 25,
            "units_available": 1159,
            "units_incoming": 0,
            "units_quarantined": 0,
            "weekly_velocity": 151,
            "weeks_on_hand": 31,
            "days_of_supply": 217.0,
            "batch_cost": 3.80,
            "wholesale_price": 9.00,
            "cogs_valuation": 4404.2,
            "wholesale_valuation": 10431.0,
            "manufacturer": "MyGreen Network",
            "is_sample": False,
            "inventory_status": "🔵 Well Stocked",
        },
        {
            "sku": "AA-AlohaMix-MIX-10mg-10pc-Bag",
            "product_name": "Aloha Mix 10mg 10pc pack",
            "category": "Gummies - Distillate",
            "warehouse": "Woodlake Hub",
            "batch_code": "AAG-AMX-04092026",
            "expiration_date": "04/06/2027",
            "units_on_hand": 1562,
            "units_reserved": 0,
            "units_available": 1562,
            "units_incoming": 0,
            "units_quarantined": 0,
            "weekly_velocity": 148,
            "weeks_on_hand": 42,
            "days_of_supply": 294.0,
            "batch_cost": 2.80,
            "wholesale_price": 6.99,
            "cogs_valuation": 4373.6,
            "wholesale_valuation": 10918.38,
            "manufacturer": "Smoakland",
            "is_sample": False,
            "inventory_status": "🔵 Well Stocked",
        },
        {
            "sku": "AA-HawaiianGuavaHaze-I-10mg-10pc-Bag",
            "product_name": "Hawaiian Guava Haze 10mg 10pc pack",
            "category": "Gummies - Distillate",
            "warehouse": "Woodlake Hub",
            "batch_code": "AAG-HGH-04072026",
            "expiration_date": "04/02/2027",
            "units_on_hand": 1387,
            "units_reserved": 25,
            "units_available": 1362,
            "units_incoming": 0,
            "units_quarantined": 0,
            "weekly_velocity": 100,
            "weeks_on_hand": 55,
            "days_of_supply": 385.0,
            "batch_cost": 2.80,
            "wholesale_price": 6.99,
            "cogs_valuation": 3813.6,
            "wholesale_valuation": 9520.38,
            "manufacturer": "Smoakland",
            "is_sample": False,
            "inventory_status": "🔵 Well Stocked",
        },
        {
            "sku": "AA-HanaleiHighTide-S-10mg-10pc-Bag",
            "product_name": "Hanalei high Tide 10mg 10pc pack",
            "category": "Gummies - Distillate",
            "warehouse": "Woodlake Hub",
            "batch_code": "AAG-HHT-04012026",
            "expiration_date": "03/31/2027",
            "units_on_hand": 1115,
            "units_reserved": 25,
            "units_available": 1065,
            "units_incoming": 0,
            "units_quarantined": 0,
            "weekly_velocity": 200,
            "weeks_on_hand": 22,
            "days_of_supply": 154.0,
            "batch_cost": 2.80,
            "wholesale_price": 6.99,
            "cogs_valuation": 2982.0,
            "wholesale_valuation": 7444.35,
            "manufacturer": "Smoakland",
            "is_sample": False,
            "inventory_status": "🟢 Healthy Stock",
        },
    ]
    return pd.DataFrame(records)


