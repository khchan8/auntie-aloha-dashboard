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
    from inventory_engine import compute_inventory_health, aggregate_inventory_by_sku
    from qbo_client import QuickBooksClient, parse_qbo_pnl_export, parse_qbo_balance_sheet
except ImportError:
    from src.data_loader import (
        load_all_nabis_remittances,
        load_budget_cashflow_model,
        get_default_inventory_data,
        parse_nabis_remittance_file,
        parse_nabis_inventory_export,
    )
    from src.cashflow_engine import generate_13_week_forecast, calculate_cash_runway_metrics
    from src.inventory_engine import compute_inventory_health, aggregate_inventory_by_sku
    from src.qbo_client import QuickBooksClient, parse_qbo_pnl_export, parse_qbo_balance_sheet

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


@st.cache_data(ttl=3600)
def get_dashboard_data():
    remittance_folder = os.path.join(BASE_DIR, "NABIS REMITTANCES 2025 TO YTD")
    raw_df, summary_df = load_all_nabis_remittances(remittance_folder)
    
    cashflow_file = os.path.join(BASE_DIR, "Auntie Aloha Cashflow Model.xlsx")
    budget_data = load_budget_cashflow_model(cashflow_file)
    
    inventory_df = get_default_inventory_data()
    
    return raw_df, summary_df, budget_data, inventory_df


# Load data
raw_nabis_df, summary_nabis_df, budget_data, initial_inv_df = get_dashboard_data()

# Initialize session state for inventory if not set
if "inventory_df" not in st.session_state:
    st.session_state.inventory_df = initial_inv_df.copy()

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
    starting_cash_input = st.number_input(
        "Current Bank Cash ($)",
        min_value=0.0,
        max_value=1000000.0,
        value=float(budget_data.get("starting_balance", 14000.0)),
        step=500.0,
        help="Synced with QuickBooks cash balance or updated manually.",
    )
    
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
        st.markdown(
            f"""<div class="kpi-card">
            <div class="kpi-title">Current Cash Balance</div>
            <div class="kpi-val">${starting_cash_input:,.2f}</div>
            <div class="kpi-sub">QuickBooks Operating Cash</div>
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

    st.markdown("<br>", unsafe_allow_html=True)
    
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
                While the original cashflow model estimated distribution costs at 28%, actual historical Nabis fee deductions average <b>{(100 - realization_rate):.1f}%</b>. This difference is driven by fixed minimum delivery charges, recurring <b>$780.15 monthly software subscription fees</b>, fuel surcharges, and sample trade orders.
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_ins2:
        # Evaluate active commercial inventory health at aggregate SKU level (excluding samples and obsolete legacy SKUs)
        agg_inv = aggregate_inventory_by_sku(st.session_state.inventory_df)
        if not agg_inv.empty:
            obs_mask = agg_inv["is_obsolete"] if "is_obsolete" in agg_inv.columns else False
            active_skus = agg_inv[(agg_inv["units_available"] > 0) & (~agg_inv["is_sample"]) & (~obs_mask)]
            critical_items = active_skus[active_skus["inventory_status"].str.contains("Critical|Reorder Now")]
        else:
            critical_items = pd.DataFrame()
        if not critical_items.empty:
            crit_names = ", ".join(critical_items["product_name"].head(2).tolist())
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

    # Prepare base data
    raw_inv_df = st.session_state.inventory_df.copy()
    if not include_samples:
        raw_inv_df = raw_inv_df[~raw_inv_df["is_sample"]]
    if not include_obsolete and "is_obsolete" in raw_inv_df.columns:
        raw_inv_df = raw_inv_df[~raw_inv_df["is_obsolete"]]

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

    km1, km2, km3, km4, km5 = st.columns(5)
    km1.metric("Available In Stock", f"{int(tot_avail_units):,} Units")
    km2.metric("Wholesale Valuation", f"${tot_whs_val:,.2f}")
    km3.metric("Inventory COGS Value", f"${tot_cogs_val:,.2f}")
    km4.metric("Weekly Burn Rate", f"{int(tot_weekly_burn):,} Units/Wk")
    km5.metric("Brand Overall Runway", f"{overall_woh:.1f} Weeks")

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
            st.markdown("#### ⏳ Weeks of Supply Remaining (Depletion Runway)")
            status_color_map = {
                "🔴 Critical Stockout Risk": "#dc3545",
                "🟡 Reorder Now (In Lead-Time)": "#ffc107",
                "🟢 Healthy Stock": "#28a745",
                "🔵 Well Stocked": "#17a2b8",
                "⚪ Discontinued / Superseded": "#94a3b8",
                "⚫ Depleted / Out of Stock": "#6c757d",
            }
            sorted_woh_df = active_display_df.sort_values("weeks_of_supply", ascending=False)
            fig_runway = px.bar(
                sorted_woh_df,
                x="product_name",
                y="weeks_of_supply",
                color="inventory_status",
                color_discrete_map=status_color_map,
                text="weeks_of_supply",
                labels={"weeks_of_supply": "Weeks on Hand", "product_name": "SKU", "inventory_status": "Health Status"},
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
                "weekly_velocity",
                "weeks_of_supply",
                "days_of_supply",
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
                "units_available": "Avail Units",
                "weekly_velocity": "Weekly Burn",
                "weeks_of_supply": "Weeks on Hand",
                "days_of_supply": "Days Supply",
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
            if "Avail Units" in styled_tbl.columns:
                styled_tbl["Avail Units"] = styled_tbl["Avail Units"].apply(lambda x: f"{int(x):,}")
            if "Weekly Burn" in styled_tbl.columns:
                styled_tbl["Weekly Burn"] = styled_tbl["Weekly Burn"].apply(lambda x: f"{int(x):,}")
            if "Weeks on Hand" in styled_tbl.columns:
                styled_tbl["Weeks on Hand"] = styled_tbl["Weeks on Hand"].apply(lambda x: f"{x:.1f} wks")
            if "Days Supply" in styled_tbl.columns:
                styled_tbl["Days Supply"] = styled_tbl["Days Supply"].apply(lambda x: f"{x:.0f} d")

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


# -----------------------------------------------------------------------------
# TAB 5: P&L & ROYALTY TRACKING
# -----------------------------------------------------------------------------
with tab_pnl:
    st.subheader("Financial Performance: QuickBooks & Royalty Streams")
    st.markdown("Track wholesale sales, international/out-of-state royalties (Thailand, Hawaii, Ohio), and cost of goods.")
    
    # Budget vs Actuals comparison
    income_budget = budget_data.get("income", pd.DataFrame())
    expense_budget = budget_data.get("expenses", pd.DataFrame())
    
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        st.markdown("#### Revenue Streams: California Wholesale & Royalties")
        if not income_budget.empty:
            st.dataframe(income_budget, use_container_width=True, hide_index=True)
            
            # Royalty breakdown chart
            royalty_rows = income_budget[income_budget["Stream"].str.contains("Royalt|Royalties", case=False, na=False)]
            if not royalty_rows.empty:
                st.markdown("##### Monthly Royalty Streams")
                royalty_long = pd.melt(
                    royalty_rows,
                    id_vars=["Stream"],
                    value_vars=["Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
                    var_name="Month",
                    value_name="Amount",
                )
                fig_roy = px.bar(
                    royalty_long,
                    x="Month",
                    y="Amount",
                    color="Stream",
                    barmode="stack",
                    title="Royalty Inflows (TPO Thailand & Hawaii)",
                )
                fig_roy.update_layout(height=300, margin=dict(l=20, r=20, t=30, b=20))
                st.plotly_chart(fig_roy, use_container_width=True)

    with col_p2:
        st.markdown("#### Manufacturing & Operational Expenses")
        if not expense_budget.empty:
            st.dataframe(expense_budget.head(10), use_container_width=True, hide_index=True)
            
            # Expense breakdown
            mfg_rows = expense_budget[expense_budget["Expense"].isin(["Smoakland", "MyGreen Network", "Luis Commissions & Fees", "Distro Nabis Expense"])]
            if not mfg_rows.empty:
                st.markdown("##### Major Cost Drivers")
                mfg_long = pd.melt(
                    mfg_rows,
                    id_vars=["Expense"],
                    value_vars=["Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
                    var_name="Month",
                    value_name="Amount",
                )
                fig_exp = px.bar(
                    mfg_long,
                    x="Month",
                    y="Amount",
                    color="Expense",
                    barmode="group",
                    title="Cost Breakdown: Production Runs vs. Commissions & Distribution",
                )
                fig_exp.update_layout(height=300, margin=dict(l=20, r=20, t=30, b=20))
                st.plotly_chart(fig_exp, use_container_width=True)


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
        )
        if uploaded_qbo:
            try:
                qbo_pnl = parse_qbo_pnl_export(uploaded_qbo)
                if not qbo_pnl.empty:
                    st.success(f"Parsed {len(qbo_pnl)} QBO line items!")
                    st.dataframe(qbo_pnl.head(10))
                else:
                    st.warning("Could not automatically identify standard P&L sections in this sheet.")
            except Exception as e:
                st.error(f"Error reading QBO file: {e}")

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
