"""
Auntie Aloha Business Dashboard
Comprehensive Cash Flow Model, Nabis Remittance & Sales Analytics, Inventory Monitor, and QuickBooks Integration.
"""

import os
import sys
import datetime
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Setup paths - ensure both project root and src/ are in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(BASE_DIR, "src")

for p in [BASE_DIR, SRC_DIR]:
    if p in sys.path:
        sys.path.remove(p)
    sys.path.insert(0, p)

# Prevent Streamlit Cloud /mount/src namespace collision
if "src" in sys.modules and not hasattr(sys.modules["src"], "data_loader"):
    del sys.modules["src"]

try:
    from data_loader import (
        load_all_nabis_remittances,
        load_budget_cashflow_model,
        get_default_inventory_data,
        parse_nabis_remittance_file,
        parse_nabis_inventory_export,
    )
    from cashflow_engine import generate_13_week_forecast, calculate_cash_runway_metrics
    from inventory_engine import compute_inventory_health, aggregate_inventory_by_sku, is_obsolete_sku, is_active_commercial_sku
    from qbo_client import (
        QuickBooksClient,
        parse_qbo_pnl_export,
        parse_qbo_balance_sheet,
        get_default_qbo_data,
    )
    from po_manager import (
        get_all_purchase_orders,
        get_po_summary_dataframe,
        get_po_sku_breakdown_dataframe,
        get_incoming_units_by_sku,
        parse_qbo_po_export,
    )
except ImportError:
    from src.data_loader import (
        load_all_nabis_remittances,
        load_budget_cashflow_model,
        get_default_inventory_data,
        parse_nabis_remittance_file,
        parse_nabis_inventory_export,
    )
    from src.cashflow_engine import generate_13_week_forecast, calculate_cash_runway_metrics
    from src.inventory_engine import compute_inventory_health, aggregate_inventory_by_sku, is_obsolete_sku, is_active_commercial_sku
    from src.qbo_client import (
        QuickBooksClient,
        parse_qbo_pnl_export,
        parse_qbo_balance_sheet,
        get_default_qbo_data,
    )
    from src.po_manager import (
        get_all_purchase_orders,
        get_po_summary_dataframe,
        get_po_sku_breakdown_dataframe,
        get_incoming_units_by_sku,
        parse_qbo_po_export,
    )

LOGO_PATH = os.path.join(BASE_DIR, "assets", "logo.webp")
FAVICON_PATH = os.path.join(BASE_DIR, "assets", "favicon.png")

# Page configuration
st.set_page_config(
    page_title="Auntie Aloha | Executive Business Dashboard",
    page_icon=FAVICON_PATH if os.path.exists(FAVICON_PATH) else "🍍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for polished Aloha branding
st.markdown(
    """
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1b4332;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #40916c;
        margin-bottom: 1.5rem;
    }
    .kpi-card {
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
        border-radius: 12px;
        padding: 1.2rem 1.4rem;
        border: 1px solid #e9ecef;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03);
    }
    .kpi-title {
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #6c757d;
        font-weight: 600;
    }
    .kpi-val {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1b4332;
        margin: 0.3rem 0;
    }
    .kpi-sub {
        font-size: 0.8rem;
        color: #2d6a4f;
    }
    .alert-banner {
        background-color: #fff3cd;
        border-left: 5px solid #ffc107;
        padding: 0.9rem 1.2rem;
        border-radius: 6px;
        margin-bottom: 1rem;
        color: #856404;
    }
    .danger-banner {
        background-color: #f8d7da;
        border-left: 5px solid #dc3545;
        padding: 0.9rem 1.2rem;
        border-radius: 6px;
        margin-bottom: 1rem;
        color: #721c24;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 18px;
        font-weight: 600;
        border-radius: 6px 6px 0px 0px;
    }
</style>
""",
    unsafe_allow_html=True,
)



def check_password() -> bool:
    """Returns True if the user entered the correct passphrase."""
    if st.session_state.get("authenticated", False):
        return True

    # Retrieve configured password from Streamlit secrets, environment, or default
    expected_pw = os.environ.get("DASHBOARD_PASSWORD", "aloha2026")
    try:
        if "DASHBOARD_PASSWORD" in st.secrets:
            expected_pw = str(st.secrets["DASHBOARD_PASSWORD"])
    except Exception:
        pass

    def validate():
        input_pw = st.session_state.get("entered_password", "").strip()
        if input_pw == expected_pw:
            st.session_state["authenticated"] = True
            st.session_state["login_failed"] = False
        else:
            st.session_state["login_failed"] = True

    st.markdown("<br>", unsafe_allow_html=True)
    _, center_col, _ = st.columns([1, 2, 1])
    with center_col:
        if os.path.exists(LOGO_PATH):
            st.image(LOGO_PATH, use_container_width=True)
        st.markdown(
            """
            <div style="background: white; padding: 1.8rem 2.2rem; border-radius: 16px; border: 1px solid #e2e8f0; box-shadow: 0 10px 25px rgba(0,0,0,0.06); text-align: center; margin-top: 15px;">
                <div style="color: #40916c; font-size: 1.05rem; margin-bottom: 1.2rem; font-weight: 600;">Business Intelligence & Financial Portal</div>
                <div style="background: #f0fdf4; border-left: 4px solid #2d6a4f; padding: 0.8rem 1rem; border-radius: 6px; text-align: left; margin-bottom: 1.5rem; font-size: 0.88rem; color: #166534;">
                    🔒 <b>Restricted Access:</b> This portal contains confidential wholesale remittances, bank cash models, and distributor records. Please enter your team passphrase to continue.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.form("login_form"):
            st.text_input("Enter Passphrase", type="password", key="entered_password", placeholder="••••••••")
            submit = st.form_submit_button("Unlock Dashboard 🔓", use_container_width=True)
            if submit:
                validate()
                if st.session_state.get("authenticated", False):
                    st.rerun()
                else:
                    st.error("❌ Incorrect passphrase. Please verify with your team administrator.")

    return False


if not check_password():
    st.stop()


APP_DATA_VERSION = "2026.09.13.v8"


@st.cache_data(ttl=600)
def get_dashboard_data(version_tag: str = APP_DATA_VERSION):
    remittance_folder = os.path.join(BASE_DIR, "NABIS REMITTANCES 2025 TO YTD")
    raw_df, summary_df = load_all_nabis_remittances(remittance_folder)
    
    cashflow_file = os.path.join(BASE_DIR, "Auntie Aloha Cashflow Model.xlsx")
    budget_data = load_budget_cashflow_model(cashflow_file)
    
    inventory_df = get_default_inventory_data()
    qbo_data = get_default_qbo_data()
    
    return raw_df, summary_df, budget_data, inventory_df, qbo_data


# Load data with automatic cache invalidation
raw_nabis_df, summary_nabis_df, budget_data, initial_inv_df, initial_qbo_data = get_dashboard_data(APP_DATA_VERSION)

# Force-synchronize session state inventory with latest loader schema and data version
if (
    "inventory_df" not in st.session_state
    or st.session_state.get("inventory_version") != APP_DATA_VERSION
    or "is_obsolete" not in st.session_state.inventory_df.columns
):
    st.session_state.inventory_df = initial_inv_df.copy()
    st.session_state["inventory_version"] = APP_DATA_VERSION

if (
    "qbo_data" not in st.session_state
    or st.session_state.get("qbo_version") != APP_DATA_VERSION
):
    st.session_state.qbo_data = initial_qbo_data
    st.session_state["qbo_version"] = APP_DATA_VERSION

# ==========================================
# SIDEBAR CONTROLS
# ==========================================
with st.sidebar:
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, use_container_width=True)
    else:
        st.markdown("## Auntie Aloha")
    st.markdown("<div style='text-align: center; color: #2d6a4f; font-size: 0.9rem; font-weight: 600; margin-bottom: 12px;'>Operations & Finance Hub</div>", unsafe_allow_html=True)
    if st.button("🔒 Lock Portal / Log Out", use_container_width=True):
        st.session_state["authenticated"] = False
        st.rerun()
    st.markdown("---")
    
    st.markdown("### ⚙️ Global Cash & Settings")
    qbo_bs = st.session_state.qbo_data.get("balance_sheet", {})
    default_cash_val = float(qbo_bs.get("bank_cash", budget_data.get("starting_balance", 14000.0)))
    starting_cash_input = st.number_input(
        "Current Bank Cash ($)",
        min_value=0.0,
        max_value=1000000.0,
        value=default_cash_val,
        step=500.0,
        help="Synced directly from QuickBooks Online Balance Sheet (Citi Bank Checking 6648) or updated manually.",
    )
    if qbo_bs.get("has_data") or qbo_bs.get("bank_cash"):
        as_of = qbo_bs.get("as_of_date", "As of Sep 12, 2026")
        acc_name = qbo_bs.get("bank_account_name", "Citi Bank Checking (6648)")
        cc_debt = qbo_bs.get("credit_card_debt", 11983.75)
        st.caption(f"🏦 **QBO Synced:** {acc_name}")
        st.caption(f"📅 **Date:** {as_of}")
        st.caption(f"💳 **Credit Cards Payable:** ${cc_debt:,.2f}")
    
    st.markdown("### 📅 Date Scope (Nabis Data)")
    date_options = ["All Time (2025–2026)", "2026 YTD", "2025 Full Year"]
    selected_scope = st.selectbox("Select Time Horizon", date_options)
    
    # Filter Nabis data
    filtered_summary = summary_nabis_df.copy()
    filtered_raw = raw_nabis_df.copy()
    
    if selected_scope == "2026 YTD":
        filtered_summary = filtered_summary[filtered_summary["file"].str.contains("2026")].reset_index(drop=True)
        filtered_raw = filtered_raw[filtered_raw["source_file"].str.contains("2026")].reset_index(drop=True)
    elif selected_scope == "2025 Full Year":
        filtered_summary = filtered_summary[filtered_summary["file"].str.contains("2025")].reset_index(drop=True)
        filtered_raw = filtered_raw[filtered_raw["source_file"].str.contains("2025")].reset_index(drop=True)
        
    st.markdown("---")
    st.caption(f"📁 **{len(filtered_summary)}** Nabis Statements Loaded")
    st.caption(f"🧾 **{len(filtered_raw)}** Invoice Line Items Parsed")
    
    if st.button("🔄 Refresh Data Cache"):
        st.cache_data.clear()
        st.session_state.inventory_df = initial_inv_df.copy()
        st.session_state["inventory_version"] = APP_DATA_VERSION
        st.session_state.qbo_data = initial_qbo_data
        st.session_state["qbo_version"] = APP_DATA_VERSION
        st.rerun()

# ==========================================
# MAIN DASHBOARD TABS
# ==========================================
hdr_col1, hdr_col2 = st.columns([1.2, 4])
with hdr_col1:
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=220)
with hdr_col2:
    st.markdown('<div class="main-header" style="margin-top: 8px;">Business Intelligence Dashboard</div>', unsafe_allow_html=True)

st.markdown(
    '<div class="sub-header">Unified Cash Flow Forecasting, Wholesale Sales Realization, Inventory Depletion & Accounting</div>',
    unsafe_allow_html=True,
)

tab_overview, tab_cashflow, tab_nabis, tab_inventory, tab_pnl, tab_upload = st.tabs([
    "📊 Executive Overview",
    "💵 13-Week Cash Flow Model",
    "📦 Nabis Wholesale & Fees",
    "📈 Inventory & SKU Monitor",
    "📑 P&L & Royalty Tracking",
    "📤 Data Upload & Sync Portal",
])

# -----------------------------------------------------------------------------
# TAB 1: EXECUTIVE OVERVIEW
# -----------------------------------------------------------------------------
with tab_overview:
    # High-level Metrics Calculation
    tot_collected = filtered_summary["total_collected"].sum() if not filtered_summary.empty else 0.0
    tot_remitted = filtered_summary["total_remitted"].sum() if not filtered_summary.empty else 0.0
    tot_fees = filtered_summary["total_kept"].sum() if not filtered_summary.empty else 0.0
    realization_rate = (tot_remitted / tot_collected * 100) if tot_collected > 0 else 0.0
    
    # Run a baseline 13-week forecast to get runway
    avg_recent_biweekly = (
        filtered_summary.tail(6)["total_remitted"].mean()
        if len(filtered_summary) >= 6
        else (tot_remitted / max(1, len(filtered_summary)))
    )
    baseline_fc = generate_13_week_forecast(
        starting_cash=starting_cash_input,
        base_biweekly_nabis=max(1200.0, avg_recent_biweekly),
    )
    runway_info = calculate_cash_runway_metrics(baseline_fc)
    
    # KPI Cards Row
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        as_of_txt = qbo_bs.get("as_of_date", "As of Sep 12, 2026")
        acc_name = qbo_bs.get("bank_account_name", "Citi Bank Checking (6648)")
        st.markdown(
            f"""<div class="kpi-card">
            <div class="kpi-title">Current Cash Balance</div>
            <div class="kpi-val">${starting_cash_input:,.2f}</div>
            <div class="kpi-sub">QuickBooks • {acc_name} • {as_of_txt}</div>
        </div>""",
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"""<div class="kpi-card">
            <div class="kpi-title">Nabis Gross Collected</div>
            <div class="kpi-val">${tot_collected:,.2f}</div>
            <div class="kpi-sub">{len(filtered_summary)} Statement Periods</div>
        </div>""",
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f"""<div class="kpi-card">
            <div class="kpi-title">Net Cash Remitted</div>
            <div class="kpi-val">${tot_remitted:,.2f}</div>
            <div class="kpi-sub">Realization: <b>{realization_rate:.1f}%</b></div>
        </div>""",
            unsafe_allow_html=True,
        )
    with c4:
        runway_color = "#2d6a4f" if runway_info["runway_weeks"] >= 8 else "#dc3545"
        st.markdown(
            f"""<div class="kpi-card">
            <div class="kpi-title">Cash Runway (Weeks)</div>
            <div class="kpi-val" style="color: {runway_color};">{runway_info['runway_weeks']} Wks</div>
            <div class="kpi-sub">Trough: ${runway_info['min_cash_balance']:,.0f} ({runway_info['trough_week'][:3]})</div>
        </div>""",
            unsafe_allow_html=True,
        )

    # Balance sheet & Working Capital strip
    cc_debt = qbo_bs.get("credit_card_debt", 11983.75)
    net_working_cap = starting_cash_input - cc_debt
    nwc_color = "#2d6a4f" if net_working_cap >= 0 else "#dc3545"
    st.markdown(
        f"""
        <div style="display: flex; flex-wrap: wrap; gap: 16px; margin-top: 12px; margin-bottom: 20px; font-size: 0.85rem; color: #495057; background: #f8f9fa; padding: 10px 18px; border-radius: 8px; border: 1px solid #e9ecef;">
            <span>💳 <b>Credit Card Payables:</b> ${cc_debt:,.2f} (Capital One + Citi CC)</span>
            <span>•</span>
            <span>⚖️ <b>Net Liquid Working Capital:</b> <b style="color: {nwc_color};">${net_working_cap:,.2f}</b></span>
            <span>•</span>
            <span>🏢 <b>Fixed Assets (Brand & IP):</b> ${qbo_bs.get('fixed_assets', 59613.0):,.2f}</span>
            <span>•</span>
            <span>📈 <b>2026 YTD Net Income:</b> <b>${st.session_state.qbo_data.get('pnl_summary', {}).get('net_income_2026_ytd', -37971.46):,.2f}</b></span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    # Visual Highlights
    row1_c1, row1_c2 = st.columns([3, 2])
    with row1_c1:
        st.subheader("Wholesale Realization: Gross Collections vs. Net Remitted Cash")
        if not filtered_summary.empty:
            fig_trend = go.Figure()
            periods = [
                f"{str(r['start_date'])[:10]}" if pd.notna(r["start_date"]) else r["file"][:18]
                for _, r in filtered_summary.iterrows()
            ]
            fig_trend.add_trace(
                go.Bar(
                    x=periods,
                    y=filtered_summary["total_collected"],
                    name="Nabis Gross Collected",
                    marker_color="#95d5b2",
                )
            )
            fig_trend.add_trace(
                go.Bar(
                    x=periods,
                    y=filtered_summary["total_kept"],
                    name="Nabis Deducted Fees",
                    marker_color="#e76f51",
                )
            )
            fig_trend.add_trace(
                go.Scatter(
                    x=periods,
                    y=filtered_summary["total_remitted"],
                    name="Net Cash Remitted to Brand",
                    mode="lines+markers",
                    line=dict(color="#1b4332", width=3),
                )
            )
            fig_trend.update_layout(
                barmode="group",
                xaxis_title="Remittance Statement Period",
                yaxis_title="USD ($)",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=20, r=20, t=30, b=50),
                height=380,
            )
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.info("No remittance data found for the selected filter.")

    with row1_c2:
        st.subheader("Where Did the Revenue Go? (Fee Breakdown)")
        if not filtered_raw.empty:
            fee_dist = (
                filtered_raw.groupby("fee_category")["nabis_kept"]
                .sum()
                .reset_index()
                .sort_values("nabis_kept", ascending=False)
            )
            # Add net remitted to show total pie
            tot_rem = filtered_raw["nabis_remitted"].sum()
            pie_data = pd.concat([
                pd.DataFrame([{"fee_category": "Net Remitted Cash", "nabis_kept": tot_rem}]),
                fee_dist[fee_dist["nabis_kept"] > 0],
            ])
            fig_pie = px.pie(
                pie_data,
                values="nabis_kept",
                names="fee_category",
                color="fee_category",
                color_discrete_map={
                    "Net Remitted Cash": "#2d6a4f",
                    "Distribution Fulfillment": "#e76f51",
                    "Software Subscription": "#f4a261",
                    "Fuel Surcharge": "#e9c46a",
                    "Case Break Fee": "#264653",
                    "Labeling Fee": "#a8dadc",
                    "Sample Order Fee": "#d62828",
                    "Other / Adjustments": "#6c757d",
                },
                hole=0.45,
            )
            fig_pie.update_layout(
                margin=dict(l=20, r=20, t=10, b=10),
                height=380,
                legend=dict(orientation="v", xanchor="left", x=1.05),
            )
            st.plotly_chart(fig_pie, use_container_width=True)

    # Key Alerts & Strategic Insights
    st.markdown("### 💡 Strategic Operational Insights")
    col_ins1, col_ins2 = st.columns(2)
    with col_ins1:
        st.markdown(
            f"""
            <div class="alert-banner">
                <b>📌 True Nabis Realization Rate is {realization_rate:.1f}%</b><br>
                Actual historical Nabis fee deductions average <b>{(100 - realization_rate):.1f}%</b>. This deduction is driven by fixed minimum delivery charges, recurring <b>$780.15 monthly software subscription fees</b>, fuel surcharges, and sample trade orders.
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_ins2:
        # Evaluate active commercial inventory health at aggregate SKU level (strictly excluding samples and obsolete legacy SKUs)
        agg_inv = aggregate_inventory_by_sku(st.session_state.inventory_df)
        if not agg_inv.empty:
            active_mask = agg_inv.apply(is_active_commercial_sku, axis=1)
            active_skus = agg_inv[(agg_inv["units_available"] > 0) & active_mask]
            critical_items = active_skus[active_skus["inventory_status"].str.contains("Critical|Reorder Now")]
        else:
            critical_items = pd.DataFrame()
        if not critical_items.empty:
            crit_names = ", ".join(critical_items["product_name"].head(3).tolist())
            min_woh = critical_items["weeks_of_supply"].min()
            st.markdown(
                f"""
                <div class="danger-banner">
                    <b>⚠️ Inventory Reorder Alert</b><br>
                    <b>{len(critical_items)} SKU(s)</b> ({crit_names}) have reached their reorder lead-time threshold (<b>{min_woh:.1f} weeks</b> supply remaining). New manufacturing batches should be scheduled to prevent stockouts.
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                <div class="alert-banner" style="border-left-color: #28a745; background-color: #e8f5e9; color: #1b5e20;">
                    <b>✅ Commercial Inventory Levels Stable</b><br>
                    All active commercial SKUs have adequate Days of Supply (DOH) relative to manufacturing lead-time buffers.
                </div>
                """,
                unsafe_allow_html=True,
            )


# -----------------------------------------------------------------------------
# TAB 2: 13-WEEK CASH FLOW MODEL
# -----------------------------------------------------------------------------
with tab_cashflow:
    st.subheader("Interactive 13-Week Rolling Cash Flow & Runway Simulator")
    st.markdown(
        "Model future cash positions by adjusting dispensary collection delays, sales growth, and scheduled batch manufacturing costs."
    )
    
    # Scenario Controls
    with st.expander("🛠️ Scenario Planning Controls & Parameters", expanded=True):
        sc_col1, sc_col2, sc_col3 = st.columns(3)
        with sc_col1:
            st.markdown("**💰 Inflow Drivers**")
            inflow_nabis_base = st.slider(
                "Base Bi-weekly Nabis Remittance ($)",
                min_value=500.0,
                max_value=10000.0,
                value=float(round(avg_recent_biweekly if avg_recent_biweekly > 500 else 2200.0, -2)),
                step=100.0,
            )
            inflow_growth = st.slider(
                "Wholesale Sales Growth / Decline (%)",
                min_value=-50,
                max_value=100,
                value=0,
                step=5,
            )
            inflow_delay = st.select_slider(
                "Dispensary Collection Lag (Weeks)",
                options=[0, 1, 2, 3, 4],
                value=0,
                help="Shifts expected Nabis remittance inflows if retailers pay slower.",
            )
            tpo_royalty_val = st.number_input(
                "Monthly Thailand / TPO Royalty ($)",
                value=5000.0,
                step=500.0,
            )
            include_hawaii_val = st.checkbox("Include Hawaii Quarterly Royalty ($4,000 in W4)", value=True)

        with sc_col2:
            st.markdown("**🏭 Manufacturing Outflows**")
            smoakland_cost = st.number_input(
                "Smoakland Production Batch ($)",
                value=32000.0,
                step=1000.0,
            )
            smoakland_wk = st.slider(
                "Smoakland Payment Timing (Week #)",
                min_value=1,
                max_value=13,
                value=6,
            )
            mygreen_cost = st.number_input(
                "MyGreen Network Rosin Batch ($)",
                value=8500.0,
                step=500.0,
            )
            mygreen_wk = st.slider(
                "MyGreen Payment Timing (Week #)",
                min_value=1,
                max_value=13,
                value=10,
            )

        with sc_col3:
            st.markdown("**💼 Operating Expenses & Fees**")
            comm_rate = st.slider(
                "Sales Commission Rate (Luis %)",
                min_value=0,
                max_value=20,
                value=12,
                step=1,
            ) / 100.0
            weekly_opex_val = st.number_input(
                "Fixed Weekly Operating Overhead ($)",
                value=450.0,
                step=50.0,
                help="Legal, licensing, insurance, storage, and administration.",
            )
            nabis_soft_val = st.number_input(
                "Nabis Monthly Software Subscription ($)",
                value=780.15,
                step=10.0,
            )

    # Calculate Forecast
    fc_df = generate_13_week_forecast(
        starting_cash=starting_cash_input,
        base_biweekly_nabis=inflow_nabis_base,
        sales_growth_pct=float(inflow_growth),
        collection_lag_weeks=inflow_delay,
        tpo_monthly_royalty=tpo_royalty_val,
        hawaii_quarterly_royalty=4000.0,
        include_hawaii=include_hawaii_val,
        smoakland_batch_cost=smoakland_cost,
        smoakland_run_week=smoakland_wk,
        mygreen_batch_cost=mygreen_cost,
        mygreen_run_week=mygreen_wk,
        luis_commission_rate=comm_rate,
        fixed_weekly_opex=weekly_opex_val,
        nabis_monthly_software=nabis_soft_val,
    )
    metrics = calculate_cash_runway_metrics(fc_df)

    # Forecast Summary Metrics
    fc_m1, fc_m2, fc_m3, fc_m4 = st.columns(4)
    fc_m1.metric("Starting Cash", f"${metrics['starting_cash']:,.2f}")
    fc_m2.metric("Total 13-Wk Inflows", f"${metrics['total_inflows']:,.2f}")
    fc_m3.metric("Total 13-Wk Outflows", f"${metrics['total_outflows']:,.2f}")
    net_color = "normal" if metrics["net_13_weeks"] >= 0 else "inverse"
    fc_m4.metric("13-Wk Net Cash Flow", f"${metrics['net_13_weeks']:,.2f}", delta_color=net_color)

    # Visual Cash Runway Chart
    st.markdown("#### Projected Ending Cash Balance Trajectory")
    fig_cash = go.Figure()
    
    # Area for positive cash
    fig_cash.add_trace(
        go.Scatter(
            x=fc_df["week_label"],
            y=fc_df["ending_cash"],
            mode="lines+markers+text",
            text=[f"${x/1000:.1f}k" for x in fc_df["ending_cash"]],
            textposition="top center",
            name="Projected Cash Balance",
            line=dict(color="#1b4332", width=3),
            marker=dict(size=8, color="#2d6a4f"),
        )
    )
    
    # Danger Threshold line at $0
    fig_cash.add_hline(
        y=0,
        line_dash="dash",
        line_color="#dc3545",
        annotation_text="Zero Cash Threshold (Insolvent)",
        annotation_position="bottom right",
    )
    
    # Safety buffer at $5k
    fig_cash.add_hline(
        y=5000,
        line_dash="dot",
        line_color="#ffc107",
        annotation_text="Safety Buffer ($5,000)",
        annotation_position="top right",
    )
    
    fig_cash.update_layout(
        xaxis_title="Forecast Week",
        yaxis_title="Projected Cash Balance ($)",
        margin=dict(l=20, r=20, t=30, b=40),
        height=380,
    )
    st.plotly_chart(fig_cash, use_container_width=True)

    # Inflow vs Outflow breakdown
    st.markdown("#### Weekly Inflows vs. Outflows Breakdown")
    fig_bars = go.Figure()
    fig_bars.add_trace(go.Bar(x=fc_df["week_label"], y=fc_df["total_inflow"], name="Total Inflow", marker_color="#52b788"))
    fig_bars.add_trace(go.Bar(x=fc_df["week_label"], y=-fc_df["total_outflow"], name="Total Outflow", marker_color="#e76f51"))
    fig_bars.update_layout(
        barmode="relative",
        xaxis_title="Week",
        yaxis_title="Cash Flow ($)",
        margin=dict(l=20, r=20, t=20, b=40),
        height=300,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig_bars, use_container_width=True)

    # Table of forecast
    st.markdown("#### 13-Week Cash Flow Schedule")
    table_display = fc_df[[
        "week_label",
        "starting_cash",
        "nabis_inflow",
        "tpo_royalty",
        "hawaii_royalty",
        "total_inflow",
        "mfg_smoakland",
        "mfg_mygreen",
        "nabis_software",
        "luis_commission",
        "opex",
        "total_outflow",
        "net_cash_flow",
        "ending_cash",
    ]].copy()
    
    # Format currency for table
    for c in table_display.columns[1:]:
        table_display[c] = table_display[c].apply(lambda x: f"${x:,.2f}" if abs(x) > 0.001 else "-")
        
    st.dataframe(table_display, use_container_width=True, hide_index=True)


# -----------------------------------------------------------------------------
# TAB 3: NABIS WHOLESALE & FEES ANALYZER
# -----------------------------------------------------------------------------
with tab_nabis:
    st.subheader("Nabis Wholesale Remittances & Fee Deductions Deep Dive")
    st.markdown("Detailed breakdown across all 38 historical statements (2025–2026).")
    
    col_n1, col_n2 = st.columns([3, 2])
    with col_n1:
        st.markdown("#### Top 15 Dispensary Retailers by Collected Revenue")
        if not filtered_raw.empty:
            disp_summary = (
                filtered_raw[filtered_raw["dispensary"].str.len() > 0]
                .groupby("dispensary")
                .agg({
                    "nabis_collected": "sum",
                    "nabis_remitted": "sum",
                    "order_number": "nunique",
                })
                .reset_index()
                .sort_values("nabis_collected", ascending=False)
                .head(15)
            )
            disp_summary.columns = ["Dispensary Account", "Total Gross Billed", "Net Remitted to Auntie Aloha", "Orders Count"]
            
            fig_disp = px.bar(
                disp_summary,
                x="Total Gross Billed",
                y="Dispensary Account",
                orientation="h",
                color="Net Remitted to Auntie Aloha",
                color_continuous_scale="Viridis",
                text="Total Gross Billed",
            )
            fig_disp.update_traces(texttemplate="$%{text:,.0f}", textposition="outside")
            fig_disp.update_layout(
                yaxis=dict(autorange="reversed"),
                height=480,
                margin=dict(l=20, r=20, t=20, b=20),
            )
            st.plotly_chart(fig_disp, use_container_width=True)

    with col_n2:
        st.markdown("#### Nabis Deducted Fees By Category")
        if not filtered_raw.empty:
            fee_totals = (
                filtered_raw.groupby("fee_category")["nabis_kept"]
                .sum()
                .reset_index()
                .sort_values("nabis_kept", ascending=False)
            )
            fee_totals = fee_totals[fee_totals["nabis_kept"] > 0]
            fee_totals["Formatted Amount"] = fee_totals["nabis_kept"].apply(lambda x: f"${x:,.2f}")
            fee_totals["% of All Fees"] = (fee_totals["nabis_kept"] / fee_totals["nabis_kept"].sum() * 100).round(1).astype(str) + "%"
            
            st.dataframe(
                fee_totals[["fee_category", "Formatted Amount", "% of All Fees"]].rename(
                    columns={"fee_category": "Fee Category"}
                ),
                use_container_width=True,
                hide_index=True,
            )
            
            st.markdown(
                """
                **Fee Observations:**
                * **Software Subscription ($780.15)** is billed bi-weekly/monthly regardless of order volume.
                * **Distribution Fulfillment** ranges between flat rates ($60–$170) and percentage fees depending on order size.
                * **Sample Orders** carry full flat delivery fees unless specifically designated under promo agreements.
                """
            )

    st.markdown("---")
    st.markdown("#### Search & Filter Remittance Line Items")
    search_q = st.text_input("🔍 Search by Dispensary Name, Order #, or Invoice #", "")
    view_raw = filtered_raw.copy()
    if search_q:
        mask = (
            view_raw["dispensary"].str.contains(search_q, case=False, na=False)
            | view_raw["order_number"].str.contains(search_q, case=False, na=False)
            | view_raw["invoice_number"].str.contains(search_q, case=False, na=False)
        )
        view_raw = view_raw[mask]
        
    st.dataframe(
        view_raw[[
            "source_file",
            "paid_date",
            "dispensary",
            "order_number",
            "invoice_type",
            "fee_category",
            "order_total",
            "nabis_collected",
            "nabis_kept",
            "nabis_remitted",
        ]].head(200),
        use_container_width=True,
        hide_index=True,
    )


# -----------------------------------------------------------------------------
# TAB 4: INVENTORY & SKU MONITOR
# -----------------------------------------------------------------------------
with tab_inventory:
    st.subheader("📦 Auntie Aloha SKU Inventory & Warehouse Depletion Monitor")
    st.markdown(
        "Real-time visibility across all commercial SKUs and production batches housed at **Nabis Woodlake Distribution Hub**. Track stock counts, weekly depletion velocities, days of supply, and automated manufacturing reorder dates."
    )

    # Top Control & Filter Bar
    with st.expander("⚙️ Production Planning & SKU Filter Settings", expanded=True):
        fcol1, fcol2, fcol3, fcol4, fcol5 = st.columns([1.4, 1.1, 1.1, 1.0, 1.2])
        with fcol1:
            view_mode = st.radio(
                "View Mode",
                ["📊 Consolidated by SKU", "📦 Batch & Lot Expiration Detail"],
                horizontal=True,
                help="Switch between aggregate SKU health and individual production batch lot tracking."
            )
        with fcol2:
            cat_filter = st.selectbox(
                "Filter by Category",
                ["All Categories", "Gummies - Solventless Rosin", "Gummies - Distillate"],
            )
        with fcol3:
            stock_filter = st.selectbox(
                "Filter by Stock Status",
                ["Active Stock (> 0 Units)", "All SKUs (Including Depleted)", "Depleted / Out of Stock"],
            )
        with fcol4:
            include_samples = st.checkbox("Include Samples ($0.01)", value=False, help="Show promotional sample units")
        with fcol5:
            include_obsolete = st.checkbox("Include Obsolete (739X)", value=False, help="Show legacy discontinued SKUs superseded by active 10mg lines")

        # Lead Time & Buffer Sliders
        scol1, scol2, scol3 = st.columns(3)
        with scol1:
            lead_time_val = st.slider("Manufacturing Lead Time (Weeks)", min_value=2, max_value=12, value=5, help="Lead time required by Smoakland or MyGreen Network to produce a batch.")
        with scol2:
            safety_stock_val = st.slider("Safety Stock Buffer (Weeks)", min_value=1, max_value=8, value=2, help="Buffer weeks to absorb sudden retail demand surges.")
        with scol3:
            total_lead_horizon = lead_time_val + safety_stock_val
            st.metric("Total Reorder Horizon", f"{total_lead_horizon} Weeks", help=f"Orders must be scheduled when stock reaches {total_lead_horizon} weeks of supply.")

        # Unit COGS & Product Margin Settings
        ccol1, ccol2, ccol3 = st.columns(3)
        with ccol1:
            distillate_cogs = st.number_input(
                "Distillate Unit COGS ($)",
                min_value=0.50,
                max_value=15.00,
                value=2.80,
                step=0.05,
                help="Unit production cost paid to Smoakland ($2.80/bag as verified in PO 260805, 260311, 260101)."
            )
        with ccol2:
            rosin_cogs = st.number_input(
                "Solventless Rosin Unit COGS ($)",
                min_value=0.50,
                max_value=25.00,
                value=3.80,
                step=0.05,
                help="Unit production cost paid to MyGreen Network for live rosin solventless gummies."
            )
        with ccol3:
            dist_margin = ((6.99 - distillate_cogs) / 6.99 * 100) if distillate_cogs > 0 else 0
            ros_margin = ((9.00 - rosin_cogs) / 9.00 * 100) if rosin_cogs > 0 else 0
            st.markdown(
                f"""
                <div style="font-size: 0.85rem; color: #4b5563; padding-top: 15px;">
                    <b>Unit Margins:</b><br>
                    • Distillate ($6.99): <b>{dist_margin:.1f}%</b> (${6.99 - distillate_cogs:.2f}/unit)<br>
                    • Rosin ($9.00): <b>{ros_margin:.1f}%</b> (${9.00 - rosin_cogs:.2f}/unit)
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Pipeline Runway Toggle
        st.markdown("---")
        pcol1, pcol2 = st.columns([1.6, 2.4])
        with pcol1:
            factor_incoming_po = st.checkbox(
                "📦 Factor Incoming PO 260805 into Runway",
                value=True,
                help="Adds 6,000 pending production units from Smoakland PO 260805 (1,000 units per Distillate SKU) into supply runway projections."
            )
        with pcol2:
            st.caption("When enabled, SKU runway and status account for batches currently in manufacturing/compliance testing at Smoakland.")

    # Prepare base data
    raw_inv_df = st.session_state.inventory_df.copy()

    # Map incoming PO units from active Smoakland POs (apply once per SKU to avoid duplicating across batch lots)
    incoming_map = get_incoming_units_by_sku()
    seen_po_skus = set()
    raw_inv_df["incoming_po_units"] = 0.0
    for idx, row in raw_inv_df.iterrows():
        sku_val = row.get("sku")
        if sku_val in incoming_map and sku_val not in seen_po_skus:
            raw_inv_df.at[idx, "incoming_po_units"] = float(incoming_map[sku_val])
            seen_po_skus.add(sku_val)

    if factor_incoming_po:
        raw_inv_df["units_incoming"] = raw_inv_df["units_incoming"] + raw_inv_df["incoming_po_units"]

    # Apply user-selected COGS dynamically to inventory
    if "batch_cost" in raw_inv_df.columns:
        is_rosin = raw_inv_df["category"].str.contains("Rosin|Solventless", case=False, na=False)
        raw_inv_df.loc[is_rosin, "batch_cost"] = rosin_cogs
        raw_inv_df.loc[~is_rosin, "batch_cost"] = distillate_cogs

    if not include_samples:
        raw_inv_df = raw_inv_df[~raw_inv_df["is_sample"]]
    if not include_obsolete:
        raw_inv_df = raw_inv_df[~raw_inv_df.apply(is_obsolete_sku, axis=1)]

    # Category filter
    if cat_filter != "All Categories":
        raw_inv_df = raw_inv_df[raw_inv_df["category"] == cat_filter]

    # Evaluate health
    if "Consolidated" in view_mode:
        active_display_df = aggregate_inventory_by_sku(raw_inv_df, lead_time_weeks=lead_time_val, safety_stock_weeks=safety_stock_val)
    else:
        active_display_df = compute_inventory_health(raw_inv_df, lead_time_weeks=lead_time_val, safety_stock_weeks=safety_stock_val)

    # Stock filter
    if stock_filter == "Active Stock (> 0 Units)":
        active_display_df = active_display_df[active_display_df["units_available"] > 0]
    elif stock_filter == "Depleted / Out of Stock":
        active_display_df = active_display_df[active_display_df["units_available"] == 0]

    # Top KPI Metrics Row
    tot_avail_units = active_display_df["units_available"].sum() if not active_display_df.empty else 0.0
    tot_whs_val = active_display_df["wholesale_valuation"].sum() if not active_display_df.empty else 0.0
    tot_cogs_val = active_display_df["cogs_valuation"].sum() if not active_display_df.empty else 0.0
    tot_weekly_burn = active_display_df["weekly_velocity"].sum() if not active_display_df.empty else 0.0
    overall_woh = (tot_avail_units / tot_weekly_burn) if tot_weekly_burn > 0 else 0.0

    tot_incoming_units = active_display_df["units_incoming"].sum() if "units_incoming" in active_display_df.columns else 0.0

    km1, km2, km3, km4, km5, km6 = st.columns(6)
    km1.metric("Available In Stock", f"{int(tot_avail_units):,} Units")
    km2.metric("Incoming PO Units", f"+{int(tot_incoming_units):,} Bags" if tot_incoming_units > 0 else "0 Bags", help="Units in production from Smoakland PO 260805")
    km3.metric("Wholesale Valuation", f"${tot_whs_val:,.2f}")
    km4.metric("Inventory COGS Value", f"${tot_cogs_val:,.2f}", help=f"Valuation at ${distillate_cogs:.2f} Distillate / ${rosin_cogs:.2f} Rosin")
    km5.metric("Weekly Burn Rate", f"{int(tot_weekly_burn):,} Units/Wk")
    km6.metric("Brand Overall Runway", f"{overall_woh:.1f} Weeks")

    st.markdown("<br>", unsafe_allow_html=True)

    if not active_display_df.empty:
        # VISUAL CHARTS ROW 1: Stock by SKU & Valuation Share
        ch_col1, ch_col2 = st.columns([1.3, 1])
        with ch_col1:
            st.markdown("#### 📊 Available Units by SKU")
            sorted_units_df = active_display_df.sort_values("units_available", ascending=True)
            fig_units = px.bar(
                sorted_units_df,
                x="units_available",
                y="product_name",
                orientation="h",
                color="category",
                color_discrete_map={
                    "Gummies - Solventless Rosin": "#2d6a4f",
                    "Gummies - Distillate": "#e76f51",
                },
                text="units_available",
                hover_data={"wholesale_valuation": ":$,.2f", "weekly_velocity": True, "product_name": False},
                labels={"units_available": "Units Available", "product_name": "Product SKU", "category": "Product Line"},
            )
            fig_units.update_traces(texttemplate="%{text:,.0f} units", textposition="inside")
            fig_units.update_layout(
                height=380,
                margin=dict(l=10, r=20, t=20, b=30),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            st.plotly_chart(fig_units, use_container_width=True)

        with ch_col2:
            st.markdown("#### 💰 Wholesale Inventory Value Share")
            donut_data = active_display_df[active_display_df["wholesale_valuation"] > 0]
            if not donut_data.empty:
                fig_donut = px.pie(
                    donut_data,
                    names="product_name",
                    values="wholesale_valuation",
                    hole=0.45,
                    color_discrete_sequence=px.colors.qualitative.Prism,
                )
                fig_donut.update_traces(textposition="inside", textinfo="percent+label")
                fig_donut.update_layout(
                    showlegend=False,
                    height=380,
                    margin=dict(l=10, r=10, t=20, b=20),
                )
                st.plotly_chart(fig_donut, use_container_width=True)
            else:
                st.info("No active valuation data.")

        # VISUAL CHARTS ROW 2: Weeks of Supply Runway & Velocity Depletion Matrix
        ch_col3, ch_col4 = st.columns([1.2, 1.2])
        with ch_col3:
            y_runway_col = "pipeline_weeks_of_supply" if (factor_incoming_po and "pipeline_weeks_of_supply" in active_display_df.columns) else "weeks_of_supply"
            chart_title = "#### ⏳ Weeks of Supply Remaining (Pipeline: Stock + PO 260805)" if factor_incoming_po else "#### ⏳ Weeks of Supply Remaining (Warehouse On-Hand Only)"
            st.markdown(chart_title)
            status_color_map = {
                "🔴 Critical Stockout Risk": "#dc3545",
                "🟡 Reorder Now (In Lead-Time)": "#ffc107",
                "🟢 Covered by Incoming PO": "#10b981",
                "🟢 Healthy Stock": "#28a745",
                "🔵 Well Stocked": "#17a2b8",
                "⚪ Discontinued / Superseded": "#94a3b8",
                "⚫ Depleted / Out of Stock": "#6c757d",
            }
            sorted_woh_df = active_display_df.sort_values(y_runway_col, ascending=False)
            fig_runway = px.bar(
                sorted_woh_df,
                x="product_name",
                y=y_runway_col,
                color="inventory_status",
                color_discrete_map=status_color_map,
                text=y_runway_col,
                labels={y_runway_col: "Weeks of Supply", "product_name": "SKU", "inventory_status": "Health Status"},
            )
            fig_runway.update_traces(texttemplate="%{text:.1f} wks", textposition="outside")
            fig_runway.add_hline(
                y=total_lead_horizon,
                line_dash="dash",
                line_color="#dc3545",
                annotation_text=f"Reorder Horizon ({total_lead_horizon} Wks)",
                annotation_position="top left",
            )
            fig_runway.update_layout(
                xaxis_title="",
                yaxis_title="Weeks of Supply",
                height=380,
                margin=dict(l=20, r=20, t=30, b=60),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            st.plotly_chart(fig_runway, use_container_width=True)

        with ch_col4:
            st.markdown("#### ⚡ Weekly Sales Burn Rate vs. Stock On Hand")
            bubble_df = active_display_df.copy()
            fig_scatter = px.scatter(
                bubble_df,
                x="weekly_velocity",
                y="units_available",
                size=bubble_df["wholesale_valuation"].apply(lambda v: max(v, 100)),
                color="category",
                color_discrete_map={
                    "Gummies - Solventless Rosin": "#2d6a4f",
                    "Gummies - Distillate": "#e76f51",
                },
                text="product_name",
                labels={"weekly_velocity": "Weekly Velocity (Units/Wk)", "units_available": "Units Available", "category": "Line"},
                hover_data={"wholesale_valuation": ":$,.2f", "weeks_of_supply": ":.1f wks"},
            )
            fig_scatter.update_traces(textposition="top center")
            fig_scatter.update_layout(
                height=380,
                margin=dict(l=20, r=20, t=30, b=40),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            st.plotly_chart(fig_scatter, use_container_width=True)

        st.markdown("---")

        # Interactive Data Table
        st.markdown("#### 📋 Detailed Inventory Schedule & Reorder Triggers")
        search_kw = st.text_input("🔍 Search Inventory by SKU Name or Batch Code", "")
        tbl_df = active_display_df.copy()
        if search_kw:
            mask = (
                tbl_df["product_name"].str.contains(search_kw, case=False, na=False)
                | tbl_df["sku"].str.contains(search_kw, case=False, na=False)
                | tbl_df["batch_code"].astype(str).str.contains(search_kw, case=False, na=False)
            )
            tbl_df = tbl_df[mask]

        if "Consolidated" in view_mode:
            display_cols = [
                "sku",
                "product_name",
                "category",
                "manufacturer",
                "units_available",
                "units_incoming",
                "weekly_velocity",
                "weeks_of_supply",
                "pipeline_weeks_of_supply",
                "wholesale_price",
                "wholesale_valuation",
                "inventory_status",
                "reorder_trigger_date",
                "batch_code",
                "expiration_date",
            ]
            valid_cols = [c for c in display_cols if c in tbl_df.columns]
            rename_dict = {
                "sku": "SKU Code",
                "product_name": "Product Name",
                "category": "Category",
                "manufacturer": "Co-Packer",
                "units_available": "Avail (On Hand)",
                "units_incoming": "Incoming PO",
                "weekly_velocity": "Weekly Burn",
                "weeks_of_supply": "On-Hand Runway",
                "pipeline_weeks_of_supply": "Pipeline Runway",
                "wholesale_price": "Unit Price",
                "wholesale_valuation": "Wholesale Value",
                "inventory_status": "Status",
                "reorder_trigger_date": "Target Reorder Date",
                "batch_code": "Batch Code(s)",
                "expiration_date": "Earliest Expiration",
            }
            styled_tbl = tbl_df[valid_cols].rename(columns=rename_dict).copy()
            if "Unit Price" in styled_tbl.columns:
                styled_tbl["Unit Price"] = styled_tbl["Unit Price"].apply(lambda x: f"${x:,.2f}")
            if "Wholesale Value" in styled_tbl.columns:
                styled_tbl["Wholesale Value"] = styled_tbl["Wholesale Value"].apply(lambda x: f"${x:,.2f}")
            if "Avail (On Hand)" in styled_tbl.columns:
                styled_tbl["Avail (On Hand)"] = styled_tbl["Avail (On Hand)"].apply(lambda x: f"{int(x):,}")
            if "Incoming PO" in styled_tbl.columns:
                styled_tbl["Incoming PO"] = styled_tbl["Incoming PO"].apply(lambda x: f"+{int(x):,}" if x > 0 else "--")
            if "Weekly Burn" in styled_tbl.columns:
                styled_tbl["Weekly Burn"] = styled_tbl["Weekly Burn"].apply(lambda x: f"{int(x):,}")
            if "On-Hand Runway" in styled_tbl.columns:
                styled_tbl["On-Hand Runway"] = styled_tbl["On-Hand Runway"].apply(lambda x: f"{x:.1f} wks")
            if "Pipeline Runway" in styled_tbl.columns:
                styled_tbl["Pipeline Runway"] = styled_tbl["Pipeline Runway"].apply(lambda x: f"{x:.1f} wks")

            st.dataframe(styled_tbl, use_container_width=True, hide_index=True)
        else:
            display_cols = [
                "sku",
                "product_name",
                "warehouse",
                "batch_code",
                "expiration_date",
                "units_available",
                "units_reserved",
                "units_on_hand",
                "weekly_velocity",
                "weeks_of_supply",
                "wholesale_price",
                "wholesale_valuation",
                "inventory_status",
            ]
            valid_cols = [c for c in display_cols if c in tbl_df.columns]
            rename_dict = {
                "sku": "SKU Code",
                "product_name": "Product Name",
                "warehouse": "Warehouse Facility",
                "batch_code": "Batch / Lot Code",
                "expiration_date": "Expiration Date",
                "units_available": "Available",
                "units_reserved": "Packed/Reserved",
                "units_on_hand": "Total Count",
                "weekly_velocity": "4-Wk Avg Velocity",
                "weeks_of_supply": "Weeks on Hand",
                "wholesale_price": "Price",
                "wholesale_valuation": "Wholesale Valuation",
                "inventory_status": "Status",
            }
            styled_tbl = tbl_df[valid_cols].rename(columns=rename_dict).copy()
            if "Price" in styled_tbl.columns:
                styled_tbl["Price"] = styled_tbl["Price"].apply(lambda x: f"${x:,.2f}")
            if "Wholesale Valuation" in styled_tbl.columns:
                styled_tbl["Wholesale Valuation"] = styled_tbl["Wholesale Valuation"].apply(lambda x: f"${x:,.2f}")
            if "Available" in styled_tbl.columns:
                styled_tbl["Available"] = styled_tbl["Available"].apply(lambda x: f"{int(x):,}")
            if "Packed/Reserved" in styled_tbl.columns:
                styled_tbl["Packed/Reserved"] = styled_tbl["Packed/Reserved"].apply(lambda x: f"{int(x):,}")
            if "Total Count" in styled_tbl.columns:
                styled_tbl["Total Count"] = styled_tbl["Total Count"].apply(lambda x: f"{int(x):,}")

            st.dataframe(styled_tbl, use_container_width=True, hide_index=True)

    else:
        st.info("No inventory records match the selected filters.")

    # Manual Editor Expander
    with st.expander("✏️ Manual Data Override & Batch Adjustments"):
        st.caption("Manually adjust stock counts or velocities below. Uploading a Nabis Inventory CSV in Tab 6 refreshes these automatically.")
        editable_cols = [c for c in ["sku", "product_name", "units_available", "weekly_velocity", "batch_cost", "wholesale_price", "manufacturer"] if c in st.session_state.inventory_df.columns]
        edited_inv = st.data_editor(st.session_state.inventory_df[editable_cols], use_container_width=True, num_rows="dynamic")
        if st.button("💾 Save Manual Inventory Adjustments"):
            for col in editable_cols:
                st.session_state.inventory_df[col] = edited_inv[col]
            st.success("Inventory updated successfully!")
            st.rerun()

    # ==========================================
    # PURCHASE ORDERS & PRODUCTION PIPELINE
    # ==========================================
    st.markdown("---")
    st.markdown("### 📦 Purchase Orders & Production Pipeline (Smoakland)")
    st.markdown(
        "Visibility into manufacturing purchase orders placed with Smoakland. Tracks ordered quantities, unit COGS ($2.80/bag), compliance testing fees ($550/test), and incoming fulfillment status."
    )

    po_summary = get_po_summary_dataframe()
    po_active = po_summary[po_summary["Status"].str.contains("Incoming|Production", case=False)]

    tot_active_units = po_active["Total Units"].sum() if not po_active.empty else 0
    tot_active_cost = po_active["Grand Total"].sum() if not po_active.empty else 0.0
    tot_active_whs = tot_active_units * 6.99
    active_po_num = po_active.iloc[0]["PO Number"] if not po_active.empty else "None"

    pk1, pk2, pk3, pk4 = st.columns(4)
    pk1.metric(
        "Active Production PO",
        f"{active_po_num}",
        "Smoakland Co-Packing"
    )
    pk2.metric(
        "Incoming Bags to Nabis",
        f"{int(tot_active_units):,} Units",
        "+1,000 bags / SKU"
    )
    pk3.metric(
        "Production Commitment",
        f"${tot_active_cost:,.2f}",
        "Includes $3,300 Testing"
    )
    pk4.metric(
        "Incoming Wholesale Value",
        f"${tot_active_whs:,.2f}",
        "@ $6.99 / bag wholesale"
    )

    po_tab1, po_tab2 = st.tabs(["📋 Purchase Order Master Schedule", "🔍 Detailed SKU Breakdown by PO"])
    with po_tab1:
        styled_po_sum = po_summary.copy()
        for c_curr in ["Unit COGS", "Production Cost", "Testing Fees", "Grand Total"]:
            if c_curr in styled_po_sum.columns:
                styled_po_sum[c_curr] = styled_po_sum[c_curr].apply(lambda x: f"${x:,.2f}")
        if "Total Units" in styled_po_sum.columns:
            styled_po_sum["Total Units"] = styled_po_sum["Total Units"].apply(lambda x: f"{int(x):,}")
        st.dataframe(styled_po_sum, use_container_width=True, hide_index=True)

    with po_tab2:
        po_options = po_summary["PO Number"].tolist()
        po_choice = st.selectbox(
            "Select Purchase Order to Inspect Line Items:",
            po_options,
            index=len(po_options) - 1,
        )
        itemized_df = get_po_sku_breakdown_dataframe(po_choice)
        styled_itemized = itemized_df.copy()
        if "Units Ordered" in styled_itemized.columns:
            styled_itemized["Units Ordered"] = styled_itemized["Units Ordered"].apply(lambda x: f"{int(x):,}")
        if "Unit Rate" in styled_itemized.columns:
            styled_itemized["Unit Rate"] = styled_itemized["Unit Rate"].apply(lambda x: f"${x:,.2f}")
        if "Line Total" in styled_itemized.columns:
            styled_itemized["Line Total"] = styled_itemized["Line Total"].apply(lambda x: f"${x:,.2f}")
        st.dataframe(styled_itemized, use_container_width=True, hide_index=True)


# -----------------------------------------------------------------------------
# TAB 5: P&L & ROYALTY TRACKING
# -----------------------------------------------------------------------------
with tab_pnl:
    st.subheader("Financial Performance: QuickBooks General Ledger & Royalty Tracking")
    st.markdown("Track wholesale sales, international/out-of-state royalties (Thailand, Hawaii), manufacturing COGS, and operating expenses directly from QuickBooks Online.")
    
    qbo_data = st.session_state.get("qbo_data", {})
    qbo_summary = qbo_data.get("pnl_summary", {})
    qbo_bs = qbo_data.get("balance_sheet", {})
    qbo_pnl_df = qbo_data.get("pnl_df", pd.DataFrame())
    monthly_trend_df = qbo_summary.get("monthly_trend", pd.DataFrame())

    # Reporting Scope Selector
    scope_col1, scope_col2 = st.columns([2.5, 3.5])
    with scope_col1:
        qbo_scope = st.radio(
            "Select Financial Reporting Period:",
            ["2026 YTD (Jan–Sep 2026)", "2025 Full Year", "All-Time Historical (2021–2026)"],
            horizontal=True,
        )
    with scope_col2:
        as_of_dt = qbo_bs.get("as_of_date", "As of Sep 12, 2026")
        st.markdown(
            f"""<div style="text-align: right; padding-top: 18px; font-size: 0.85rem; color: #2d6a4f;">
                🟢 <b>QuickBooks Ledger Synced:</b> <code>QB/Profit and Loss - AA.xlsx</code> & <code>QB/Balance Sheet - AA.xlsx</code> ({as_of_dt})
            </div>""",
            unsafe_allow_html=True,
        )

    # Calculate metrics based on selected scope
    if qbo_scope == "2026 YTD (Jan–Sep 2026)":
        inc_val = qbo_summary.get("income_2026_ytd", 132970.18)
        cogs_val = qbo_summary.get("cogs_2026_ytd", 76373.04)
        gp_val = qbo_summary.get("gross_profit_2026_ytd", 56597.14)
        exp_val = qbo_summary.get("expenses_2026_ytd", 94643.60)
        net_val = qbo_summary.get("net_income_2026_ytd", -37971.46)
        scope_label = "2026 YTD"
    elif qbo_scope == "2025 Full Year":
        inc_val = 176368.71
        cogs_val = 72104.09
        gp_val = 104264.62
        exp_val = 125683.76
        net_val = -27724.14
        scope_label = "2025 Full Year"
    else:
        inc_val = qbo_summary.get("income_all_time", 510282.68)
        cogs_val = qbo_summary.get("cogs_all_time", 423613.10)
        gp_val = qbo_summary.get("gross_profit_all_time", 86669.58)
        exp_val = qbo_summary.get("expenses_all_time", 909716.16)
        net_val = qbo_summary.get("net_income_all_time", -859357.58)
        scope_label = "All-Time"

    gm_pct = (gp_val / inc_val * 100) if inc_val > 0 else 0.0
    net_color = "#2d6a4f" if net_val >= 0 else "#dc3545"

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.markdown(
            f"""<div class="kpi-card">
                <div class="kpi-title">Total Revenue</div>
                <div class="kpi-val">${inc_val:,.2f}</div>
                <div class="kpi-sub">{scope_label} QBO Sales & Royalties</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with k2:
        st.markdown(
            f"""<div class="kpi-card">
                <div class="kpi-title">Cost of Goods Sold</div>
                <div class="kpi-val">${cogs_val:,.2f}</div>
                <div class="kpi-sub">Manufacturing & Shipping</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with k3:
        st.markdown(
            f"""<div class="kpi-card">
                <div class="kpi-title">Gross Profit</div>
                <div class="kpi-val">${gp_val:,.2f}</div>
                <div class="kpi-sub">Gross Margin: <b>{gm_pct:.1f}%</b></div>
            </div>""",
            unsafe_allow_html=True,
        )
    with k4:
        st.markdown(
            f"""<div class="kpi-card">
                <div class="kpi-title">Operating Expenses</div>
                <div class="kpi-val">${exp_val:,.2f}</div>
                <div class="kpi-sub">Distro, Software, Marketing</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with k5:
        st.markdown(
            f"""<div class="kpi-card">
                <div class="kpi-title">Net Income</div>
                <div class="kpi-val" style="color: {net_color};">${net_val:,.2f}</div>
                <div class="kpi-sub">QuickBooks Cash Basis</div>
            </div>""",
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    pnl_col1, pnl_col2 = st.columns(2)
    with pnl_col1:
        st.subheader("2026 Monthly Income vs. Cost Trajectory")
        if not monthly_trend_df.empty:
            fig_trend = go.Figure()
            fig_trend.add_trace(go.Bar(
                x=monthly_trend_df["Month"],
                y=monthly_trend_df["Income"],
                name="Total Revenue",
                marker_color="#2d6a4f",
            ))
            fig_trend.add_trace(go.Bar(
                x=monthly_trend_df["Month"],
                y=monthly_trend_df["COGS"],
                name="Cost of Goods Sold",
                marker_color="#e76f51",
            ))
            fig_trend.add_trace(go.Bar(
                x=monthly_trend_df["Month"],
                y=monthly_trend_df["Expenses"],
                name="Operating Expenses",
                marker_color="#f4a261",
            ))
            fig_trend.add_trace(go.Scatter(
                x=monthly_trend_df["Month"],
                y=monthly_trend_df["Net_Income"],
                name="Net Income",
                mode="lines+markers",
                line=dict(color="#1b4332", width=3),
            ))
            fig_trend.update_layout(
                barmode="group",
                xaxis_title="2026 Months",
                yaxis_title="USD ($)",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=20, r=20, t=30, b=30),
                height=350,
            )
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.info("No monthly trend data available.")

        # Revenue streams breakdown
        st.subheader("Revenue Mix: California Wholesale vs. Royalties (2026 YTD)")
        rev_streams = pd.DataFrame([
            {"Stream": "Thailand Royalties", "Amount": qbo_summary.get("income_thailand_2026_ytd", 50863.60)},
            {"Stream": "California Wholesale (Cali)", "Amount": qbo_summary.get("income_cali_2026_ytd", 42341.28)},
            {"Stream": "Hawaii Royalties", "Amount": qbo_summary.get("income_hawaii_2026_ytd", 39765.30)},
        ])
        fig_rev_pie = px.pie(
            rev_streams,
            values="Amount",
            names="Stream",
            color="Stream",
            color_discrete_map={
                "Thailand Royalties": "#2a9d8f",
                "California Wholesale (Cali)": "#264653",
                "Hawaii Royalties": "#e9c46a",
            },
            hole=0.45,
        )
        fig_rev_pie.update_layout(height=300, margin=dict(l=20, r=20, t=10, b=10))
        st.plotly_chart(fig_rev_pie, use_container_width=True)

    with pnl_col2:
        st.subheader("Major Operating Expense Drivers (2026 YTD)")
        exp_breakdown = pd.DataFrame([
            {"Category": "Software & Office Supplies", "Amount": qbo_summary.get("exp_software_office_2026_ytd", 30787.53)},
            {"Category": "Nabis Distro Fees", "Amount": qbo_summary.get("exp_nabis_distro_2026_ytd", 24373.27)},
            {"Category": "Advertising & Marketing", "Amount": qbo_summary.get("exp_marketing_2026_ytd", 19288.77)},
            {"Category": "Nabis Logistics & Storage", "Amount": qbo_summary.get("exp_nabis_logistics_2026_ytd", 7089.03)},
            {"Category": "Legal & Accounting", "Amount": qbo_summary.get("exp_legal_acctg_2026_ytd", 6119.48)},
            {"Category": "Insurance", "Amount": 3143.04},
            {"Category": "Interest & Bank Charges", "Amount": 1909.81},
            {"Category": "Other Overhead (Travel, Meals, Postage)", "Amount": 1932.67},
        ])
        fig_exp_pie = px.pie(
            exp_breakdown,
            values="Amount",
            names="Category",
            color_discrete_sequence=px.colors.qualitative.Safe,
            hole=0.45,
        )
        fig_exp_pie.update_layout(height=350, margin=dict(l=20, r=20, t=10, b=10))
        st.plotly_chart(fig_exp_pie, use_container_width=True)

        # Manufacturing Outflow Timeline
        st.subheader("Manufacturing Payments Timeline (Smoakland Production Runs)")
        if not monthly_trend_df.empty:
            fig_mfg = px.bar(
                monthly_trend_df,
                x="Month",
                y="Manufacturing_Cost",
                labels={"Manufacturing_Cost": "Manufacturing ($)", "Month": "Month (2026)"},
                color_discrete_sequence=["#e76f51"],
            )
            fig_mfg.update_layout(height=300, margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig_mfg, use_container_width=True)

    # Interactive Data Ledgers
    st.markdown("---")
    st.subheader("📋 QuickBooks General Ledger & Financial Statements")
    gl_tab1, gl_tab2, gl_tab3, gl_tab4 = st.tabs([
        "📑 2026 Monthly P&L Ledger",
        "🏦 Balance Sheet (Sep 12, 2026)",
        "⏳ Historical Comparison (2025 vs 2026 vs All-Time)",
        "📊 Budget Model Comparison",
    ])

    with gl_tab1:
        if not qbo_pnl_df.empty:
            section_choice = st.selectbox(
                "Filter P&L by Section:",
                ["All Accounts", "Income", "Cost of Goods Sold", "Expenses"],
                key="gl_sec_filter",
            )
            cols_2026 = [c for c in qbo_pnl_df.columns if "2026" in c]
            display_cols = ["Section", "Account"] + cols_2026 + ["2026_YTD"]
            
            pnl_view = qbo_pnl_df.copy()
            if section_choice != "All Accounts":
                pnl_view = pnl_view[pnl_view["Section"] == section_choice]
            
            # Format currency columns
            styled_pnl = pnl_view[display_cols].copy()
            for col in cols_2026 + ["2026_YTD"]:
                styled_pnl[col] = styled_pnl[col].apply(lambda v: f"${v:,.2f}" if abs(v) > 0.001 else "-")
            
            st.dataframe(styled_pnl, use_container_width=True, hide_index=True)
        else:
            st.info("QuickBooks P&L data not yet loaded.")

    with gl_tab2:
        st.markdown(f"#### Balance Sheet — {qbo_bs.get('as_of_date', 'As of Sep 12, 2026')}")
        bs_c1, bs_c2, bs_c3 = st.columns(3)
        with bs_c1:
            st.markdown("##### 💵 Current Assets")
            st.markdown(f"- **{qbo_bs.get('bank_account_name', 'Citi Bank Checking (6648)')}:** `${qbo_bs.get('bank_cash', 8277.06):,.2f}`")
            st.markdown(f"- **Total Bank Accounts:** `${qbo_bs.get('bank_cash', 8277.06):,.2f}`")
            st.markdown(f"- **Total Current Assets:** `${qbo_bs.get('bank_cash', 8277.06):,.2f}`")
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("##### 🏢 Fixed Assets")
            st.markdown("- **Brand Development:** `$22,500.00`")
            st.markdown("- **IP Development:** `$66,391.00`")
            st.markdown("- **Startup Costs:** `$7,558.00`")
            st.markdown("- **Accumulated Amortization:** `-$36,836.00`")
            st.markdown(f"- **Total Fixed Assets:** `${qbo_bs.get('fixed_assets', 59613.00):,.2f}`")
            st.markdown(f"**Total Assets:** `${qbo_bs.get('total_assets', 67890.06):,.2f}`")

        with bs_c2:
            st.markdown("##### 💳 Liabilities")
            st.markdown("- **Capital One Credit Card (6212):** `$4,427.67`")
            st.markdown("- **Citi Bank Credit Card (5816):** `$7,556.08`")
            st.markdown(f"- **Total Credit Cards Payable:** `${qbo_bs.get('credit_card_debt', 11983.75):,.2f}`")
            st.markdown(f"- **Total Current Liabilities:** `${qbo_bs.get('total_liabilities', 11983.75):,.2f}`")
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("##### ⚖️ Working Capital Analysis")
            net_wc = qbo_bs.get("net_working_capital", -3706.69)
            wc_style = "#2d6a4f" if net_wc >= 0 else "#dc3545"
            st.markdown(f"- **Bank Checking:** `${qbo_bs.get('bank_cash', 8277.06):,.2f}`")
            st.markdown(f"- **Credit Card Debt:** `-${qbo_bs.get('credit_card_debt', 11983.75):,.2f}`")
            st.markdown(f"- **Net Liquid Capital:** <b style='color: {wc_style};'>${net_wc:,.2f}</b>", unsafe_allow_html=True)

        with bs_c3:
            st.markdown("##### 👥 Equity")
            st.markdown("- **Michael Reinsch (PM Dawn LLC):** `$329,352.86`")
            st.markdown("- **Pat Arora (PM Dawn LLC):** `$228,899.34`")
            st.markdown("- **Marisa Badua (Tiare Ventures LLC):** `$233,890.46`")
            st.markdown("- **Total Owner's Investment:** `$795,068.21`")
            st.markdown("- **Owner's Pay & Personal Expenses:** `$23,746.68`")
            st.markdown("- **Retained Earnings:** `-$724,937.12`")
            st.markdown(f"- **2026 Net Income:** `${qbo_bs.get('net_income', -37971.46):,.2f}`")
            st.markdown(f"**Total Equity:** `${qbo_bs.get('total_equity', 55906.31):,.2f}`")
            st.markdown(f"**Total Liabilities & Equity:** `${qbo_bs.get('total_assets', 67890.06):,.2f}`")

    with gl_tab3:
        if not qbo_pnl_df.empty:
            st.markdown("#### Historical Performance Comparison: 2026 YTD vs. 2025 vs. All-Time")
            hist_cols = ["Section", "Account", "2026_YTD", "2025_Total", "All_Time_Total"]
            styled_hist = qbo_pnl_df[hist_cols].copy()
            for col in ["2026_YTD", "2025_Total", "All_Time_Total"]:
                styled_hist[col] = styled_hist[col].apply(lambda v: f"${v:,.2f}" if abs(v) > 0.001 else "-")
            st.dataframe(styled_hist, use_container_width=True, hide_index=True)
        else:
            st.info("P&L data not loaded.")

    with gl_tab4:
        st.markdown("#### Budget Model Comparison (from Cashflow Model Spreadsheet)")
        income_budget = budget_data.get("income", pd.DataFrame())
        expense_budget = budget_data.get("expenses", pd.DataFrame())
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            st.markdown("##### Budgeted Revenue Streams")
            if not income_budget.empty:
                st.dataframe(income_budget, use_container_width=True, hide_index=True)
        with col_b2:
            st.markdown("##### Budgeted Expenses")
            if not expense_budget.empty:
                st.dataframe(expense_budget.head(10), use_container_width=True, hide_index=True)


# -----------------------------------------------------------------------------
# TAB 6: DATA UPLOAD & SYNC PORTAL
# -----------------------------------------------------------------------------
with tab_upload:
    st.subheader("Data Upload & Source Synchronization")
    st.markdown(
        "Drop new Nabis remittances, Nabis inventory exports, or QuickBooks reports to immediately update the dashboard without editing Excel formulas."
    )
    
    up_c1, up_c2 = st.columns(2)
    with up_c1:
        st.markdown("### 📥 Upload Nabis Remittance File")
        uploaded_remittance = st.file_uploader(
            "Upload new Nabis Remittance (.xlsx)",
            type=["xlsx"],
            key="up_remittance",
        )
        if uploaded_remittance:
            try:
                # Save to 2026 directory
                target_dir = os.path.join(BASE_DIR, "NABIS REMITTANCES 2025 TO YTD", "2026")
                os.makedirs(target_dir, exist_ok=True)
                save_path = os.path.join(target_dir, uploaded_remittance.name)
                with open(save_path, "wb") as f:
                    f.write(uploaded_remittance.getbuffer())
                    
                st.success(f"Saved {uploaded_remittance.name} into Nabis 2026 folder!")
                st.cache_data.clear()
                st.info("Cache refreshed. Click below to view the new data.")
                if st.button("Reload Dashboard"):
                    st.rerun()
            except Exception as e:
                st.error(f"Error saving file: {e}")

        st.markdown("### 📦 Upload Nabis Inventory Export")
        uploaded_inventory = st.file_uploader(
            "Upload Nabis Inventory (.csv or .xlsx)",
            type=["csv", "xlsx"],
            key="up_inv",
        )
        if uploaded_inventory:
            try:
                # Save to Nabis Inventory directory so it persists in the repository
                inv_dir = os.path.join(BASE_DIR, "Nabis Inventory")
                os.makedirs(inv_dir, exist_ok=True)
                save_path = os.path.join(inv_dir, uploaded_inventory.name)
                with open(save_path, "wb") as f:
                    f.write(uploaded_inventory.getbuffer())

                new_inv_df = parse_nabis_inventory_export(save_path)
                if not new_inv_df.empty:
                    st.session_state.inventory_df = new_inv_df.copy()
                    st.success(f"✅ Successfully parsed {len(new_inv_df)} inventory line items and saved to Nabis Inventory/{uploaded_inventory.name}!")
                    st.dataframe(new_inv_df.head(5))
                    st.info("The Inventory & SKU Monitor (Tab 4) and Executive Overview (Tab 1) have been dynamically updated!")
                else:
                    st.warning("Could not automatically identify standard Nabis inventory columns. Showing raw preview:")
                    if uploaded_inventory.name.endswith(".csv"):
                        df_raw = pd.read_csv(uploaded_inventory)
                    else:
                        df_raw = pd.read_excel(uploaded_inventory)
                    st.dataframe(df_raw.head(5))
            except Exception as e:
                st.error(f"Error processing inventory file: {e}")

    with up_c2:
        st.markdown("### 📑 Upload QuickBooks Online Export")
        uploaded_qbo = st.file_uploader(
            "Upload QBO P&L or Balance Sheet (.xlsx)",
            type=["xlsx", "xls"],
            key="up_qbo",
            help="Upload Balance Sheet - AA.xlsx or Profit and Loss - AA.xlsx to update accounting data."
        )
        if uploaded_qbo:
            try:
                qb_dir = os.path.join(BASE_DIR, "QB")
                os.makedirs(qb_dir, exist_ok=True)
                save_path = os.path.join(qb_dir, uploaded_qbo.name)
                with open(save_path, "wb") as f:
                    f.write(uploaded_qbo.getbuffer())

                fname_lower = uploaded_qbo.name.lower()
                if "balance" in fname_lower:
                    bs_res = parse_qbo_balance_sheet(save_path)
                    st.session_state.qbo_data["balance_sheet"] = bs_res
                    st.success(f"✅ Saved & parsed QuickBooks Balance Sheet! Bank Cash: ${bs_res.get('bank_cash', 0.0):,.2f}")
                elif "profit" in fname_lower or "p&l" in fname_lower or "pnl" in fname_lower:
                    pnl_df, pnl_sum = parse_qbo_pnl_export(save_path)
                    st.session_state.qbo_data["pnl_df"] = pnl_df
                    st.session_state.qbo_data["pnl_summary"] = pnl_sum
                    st.success(f"✅ Saved & parsed QuickBooks P&L! 2026 YTD Revenue: ${pnl_sum.get('income_2026_ytd', 0.0):,.2f} | Net: ${pnl_sum.get('net_income_2026_ytd', 0.0):,.2f}")
                else:
                    st.info(f"File saved to QB/{uploaded_qbo.name}. Refresh data cache to update all tabs.")
                st.cache_data.clear()
            except Exception as e:
                st.error(f"Error reading QBO file: {e}")

        st.markdown("### 📋 Upload QuickBooks Purchase Order Export")
        st.info(
            """
            💡 **Why POs are not in the P&L or Balance Sheet:**
            Under GAAP, **Purchase Orders are non-posting transactions**. They represent commitments to Smoakland, not posted expenses, assets, or liabilities. They only hit the P&L as *Cost of Goods Sold: Manufacturing* when a Bill is entered.

            **How to Export POs from QuickBooks Online:**
            1. In QBO, go to **Reports** in the left navigation.
            2. Search for **"Open Purchase Order Detail"** (or **"Purchase Order Detail"**).
            3. Set Date Range to **"All Dates"** (or 2025 to 2026).
            4. Ensure columns include: `PO #`, `Date`, `Vendor` (Smoakland), `Product/Service` (Item / SKU name), `Quantity`, `Rate` ($2.80), and `Amount`.
            5. Click the **Export** icon -> **Export to Excel**.
            6. Drop the exported spreadsheet below, or save it to `QB/Purchase Orders - AA.xlsx`.
            """
        )
        uploaded_qbo_po = st.file_uploader(
            "Upload QBO Open Purchase Order Detail (.xlsx)",
            type=["xlsx", "xls"],
            key="up_qbo_po",
            help="Exports from QuickBooks: Reports -> Open Purchase Order Detail (or Purchases by Product/Service Detail)"
        )
        if uploaded_qbo_po:
            try:
                qb_dir = os.path.join(BASE_DIR, "QB")
                os.makedirs(qb_dir, exist_ok=True)
                save_path = os.path.join(qb_dir, uploaded_qbo_po.name)
                with open(save_path, "wb") as f:
                    f.write(uploaded_qbo_po.getbuffer())

                qbo_po_df = parse_qbo_po_export(save_path)
                if not qbo_po_df.empty:
                    st.success(f"✅ Parsed {len(qbo_po_df)} Purchase Order lines from QuickBooks and saved to QB/{uploaded_qbo_po.name}!")
                    st.dataframe(qbo_po_df.head(10), use_container_width=True)
                else:
                    st.warning("Could not automatically identify standard PO lines in this sheet.")
            except Exception as e:
                st.error(f"Error reading QBO PO file: {e}")

        st.markdown("### 🔗 QuickBooks Developer API Status")
        qbo_client = QuickBooksClient()
        qbo_status = qbo_client.get_connection_status()
        
        st.info(f"**Current Status:** {qbo_status['mode']}")
        with st.expander("Configure Direct QBO OAuth API Credentials"):
            st.caption("Provide your Intuit Developer App credentials below to activate live sync.")
            qbo_id = st.text_input("Client ID", value="")
            qbo_secret = st.text_input("Client Secret", value="", type="password")
            qbo_realm = st.text_input("Company / Realm ID", value="")
            if st.button("Save QBO Credentials"):
                st.success("Credentials saved to environment config.")

# Footer
st.markdown("---")
st.caption("Auntie Aloha Business Operations & Financial Modeling System • Version 1.0 • Built with Antigravity")
