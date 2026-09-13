"""
Auntie Aloha Dashboard - Purchase Order & Incoming Inventory Engine
Tracks manufacturing batches placed with Smoakland and MyGreen Network,
incoming production pipeline by SKU, and QuickBooks PO exports.
"""

import os
from typing import Dict, List, Any, Optional
import pandas as pd

# SKU Mapping for Smoakland Distillate line
SKU_MAP = {
    "Pakalolo POG": "AA-PakaloloPOG-I-10mg-10pc-Bag",
    "Hanalei High Tide": "AA-HanaleiHighTide-S-10mg-10pc-Bag",
    "OG Lava Flow": "AA-OGLavaFlow-H-10mg-10pc-Bag",
    "Hawaiian Guava Haze": "AA-HawaiianGuavaHaze-I-10mg-10pc-Bag",
    "Lilikoi Citrus Buzz": "AA-LilikoiCitrusBuzz-S-10mg-10pc-Bag",
    "Aloha Mix": "AA-AlohaMix-MIX-10mg-10pc-Bag",
}

DEFAULT_PURCHASE_ORDERS = [
    {
        "po_number": "PO 260101",
        "vendor": "Smoakland",
        "order_date": "2025-12-24",
        "status": "Fulfilled / Received",
        "total_units": 7500,
        "unit_cogs": 2.80,
        "mfg_cost": 21000.00,
        "testing_fees": 0.00,
        "grand_total": 21000.00,
        "notes": "Initial 2026 replenishment batch. Delivered and stocked at Nabis Woodlake.",
        "items": [
            {"product_name": "Pakalolo POG", "sku": "AA-PakaloloPOG-I-10mg-10pc-Bag", "units": 1250, "rate": 2.80, "amount": 3500.00},
            {"product_name": "Hanalei High Tide", "sku": "AA-HanaleiHighTide-S-10mg-10pc-Bag", "units": 1250, "rate": 2.80, "amount": 3500.00},
            {"product_name": "OG Lava Flow", "sku": "AA-OGLavaFlow-H-10mg-10pc-Bag", "units": 1250, "rate": 2.80, "amount": 3500.00},
            {"product_name": "Hawaiian Guava Haze", "sku": "AA-HawaiianGuavaHaze-I-10mg-10pc-Bag", "units": 1250, "rate": 2.80, "amount": 3500.00},
            {"product_name": "Lilikoi Citrus Buzz", "sku": "AA-LilikoiCitrusBuzz-S-10mg-10pc-Bag", "units": 1250, "rate": 2.80, "amount": 3500.00},
            {"product_name": "Aloha Mix", "sku": "AA-AlohaMix-MIX-10mg-10pc-Bag", "units": 1250, "rate": 2.80, "amount": 3500.00},
        ],
    },
    {
        "po_number": "PO 260311",
        "vendor": "Smoakland",
        "order_date": "2026-03-11",
        "status": "Fulfilled / Received",
        "total_units": 9500,
        "unit_cogs": 2.80,
        "mfg_cost": 26600.00,
        "testing_fees": 3300.00,
        "grand_total": 29900.00,
        "notes": "Spring production run including 6 state compliance lab testing fees ($550/test).",
        "items": [
            {"product_name": "Pakalolo POG", "sku": "AA-PakaloloPOG-I-10mg-10pc-Bag", "units": 1500, "rate": 2.80, "amount": 4200.00},
            {"product_name": "Hanalei High Tide", "sku": "AA-HanaleiHighTide-S-10mg-10pc-Bag", "units": 1500, "rate": 2.80, "amount": 4200.00},
            {"product_name": "OG Lava Flow", "sku": "AA-OGLavaFlow-H-10mg-10pc-Bag", "units": 1500, "rate": 2.80, "amount": 4200.00},
            {"product_name": "Hawaiian Guava Haze", "sku": "AA-HawaiianGuavaHaze-I-10mg-10pc-Bag", "units": 1500, "rate": 2.80, "amount": 4200.00},
            {"product_name": "Lilikoi Citrus Buzz", "sku": "AA-LilikoiCitrusBuzz-S-10mg-10pc-Bag", "units": 1500, "rate": 2.80, "amount": 4200.00},
            {"product_name": "Aloha Mix", "sku": "AA-AlohaMix-MIX-10mg-10pc-Bag", "units": 2000, "rate": 2.80, "amount": 5600.00},
        ],
    },
    {
        "po_number": "PO 260805",
        "vendor": "Smoakland",
        "order_date": "2026-08-05",
        "status": "In Production / Incoming",
        "total_units": 6000,
        "unit_cogs": 2.80,
        "mfg_cost": 16800.00,
        "testing_fees": 3300.00,
        "grand_total": 20100.00,
        "notes": "Latest order currently in production / compliance testing at Smoakland. 1,000 units per SKU incoming to Nabis Woodlake.",
        "items": [
            {"product_name": "Pakalolo POG", "sku": "AA-PakaloloPOG-I-10mg-10pc-Bag", "units": 1000, "rate": 2.80, "amount": 2800.00},
            {"product_name": "Hanalei High Tide", "sku": "AA-HanaleiHighTide-S-10mg-10pc-Bag", "units": 1000, "rate": 2.80, "amount": 2800.00},
            {"product_name": "OG Lava Flow", "sku": "AA-OGLavaFlow-H-10mg-10pc-Bag", "units": 1000, "rate": 2.80, "amount": 2800.00},
            {"product_name": "Hawaiian Guava Haze", "sku": "AA-HawaiianGuavaHaze-I-10mg-10pc-Bag", "units": 1000, "rate": 2.80, "amount": 2800.00},
            {"product_name": "Lilikoi Citrus Buzz", "sku": "AA-LilikoiCitrusBuzz-S-10mg-10pc-Bag", "units": 1000, "rate": 2.80, "amount": 2800.00},
            {"product_name": "Aloha Mix", "sku": "AA-AlohaMix-MIX-10mg-10pc-Bag", "units": 1000, "rate": 2.80, "amount": 2800.00},
        ],
    },
]


def get_all_purchase_orders() -> List[Dict[str, Any]]:
    """Returns the full master list of purchase orders."""
    return DEFAULT_PURCHASE_ORDERS


def get_po_summary_dataframe() -> pd.DataFrame:
    """Returns a high-level summary DataFrame of all Purchase Orders."""
    rows = []
    for po in DEFAULT_PURCHASE_ORDERS:
        rows.append({
            "PO Number": po["po_number"],
            "Vendor": po["vendor"],
            "Order Date": po["order_date"],
            "Status": po["status"],
            "Total Units": po["total_units"],
            "Unit COGS": po["unit_cogs"],
            "Production Cost": po["mfg_cost"],
            "Testing Fees": po["testing_fees"],
            "Grand Total": po["grand_total"],
            "Notes": po["notes"],
        })
    return pd.DataFrame(rows)


def get_po_sku_breakdown_dataframe(po_number: Optional[str] = None) -> pd.DataFrame:
    """Returns itemized SKU records across POs, optionally filtered by PO Number."""
    rows = []
    for po in DEFAULT_PURCHASE_ORDERS:
        if po_number and po["po_number"] != po_number:
            continue
        for item in po["items"]:
            rows.append({
                "PO Number": po["po_number"],
                "Order Date": po["order_date"],
                "Status": po["status"],
                "Product Name": item["product_name"],
                "SKU Code": item["sku"],
                "Units Ordered": item["units"],
                "Unit Rate": item["rate"],
                "Line Total": item["amount"],
            })
    return pd.DataFrame(rows)


def get_incoming_units_by_sku() -> Dict[str, int]:
    """
    Returns total incoming units grouped by SKU from all active / in-production POs.
    """
    incoming = {}
    for po in DEFAULT_PURCHASE_ORDERS:
        if "Incoming" in po["status"] or "In Production" in po["status"]:
            for item in po["items"]:
                sku = item["sku"]
                incoming[sku] = incoming.get(sku, 0) + int(item["units"])
    return incoming


def parse_qbo_po_export(file_path_or_buffer) -> pd.DataFrame:
    """
    Parses a QuickBooks Online 'Open Purchase Order Detail' or
    'Purchases by Product/Service Detail' spreadsheet export.
    """
    try:
        df_raw = pd.read_excel(file_path_or_buffer, header=None)
        # Scan for header row
        hdr_idx = None
        for r in range(min(15, len(df_raw))):
            row_vals = [str(v).strip().lower() for v in df_raw.iloc[r] if pd.notna(v)]
            if any("num" in v or "po" in v or "item" in v or "product" in v for v in row_vals):
                hdr_idx = r
                break

        if hdr_idx is not None:
            df_data = pd.read_excel(file_path_or_buffer, skiprows=hdr_idx)
            return df_data
        return df_raw
    except Exception as e:
        print(f"Error parsing QBO PO export: {e}")
        return pd.DataFrame()
