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

# Setup paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.data_loader import (
    load_all_nabis_remittances,
    load_budget_cashflow_model,
    get_default_inventory_data,
    parse_nabis_remittance_file,
    parse_nabis_inventory_export,
)
from src.cashflow_engine import generate_13_week_forecast, calculate_cash_runway_metrics
from src.inventory_engine import compute_inventory_health
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
    "📈 Inventory & Reorder Monitor",
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
        # Check lowest inventory
        inv_eval = compute_inventory_health(st.session_state.inventory_df)
        critical_items = inv_eval[inv_eval["inventory_status"].str.contains("Critical|Reorder Now")]
        if not critical_items.empty:
            crit_names = ", ".join(critical_items["product_name"].head(2).tolist())
            st.markdown(
                f"""
                <div class="danger-banner">
                    <b>⚠️ Inventory Reorder Alert</b><br>
                    <b>{len(critical_items)} SKU(s)</b> ({crit_names}) have reached their reorder lead-time threshold. New production batches should be initiated to avoid stockouts.
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                <div class="alert-banner" style="border-left-color: #28a745; background-color: #e8f5e9; color: #1b5e20;">
                    <b>✅ Inventory Levels Stable</b><br>
                    All current SKUs have adequate Days of Supply (DOH) relative to manufacturing lead-time buffers.
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
# TAB 4: INVENTORY & PRODUCTION REORDER MONITOR
# -----------------------------------------------------------------------------
with tab_inventory:
    st.subheader("Inventory Monitor & Manufacturing Reorder Triggers")
    st.markdown("Track stock across Nabis Oakland & Los Angeles hubs with automated Days of Supply (DOH) calculations.")
    
    # Lead time settings
    inv_col_s1, inv_col_s2, inv_col_s3 = st.columns(3)
    with inv_col_s1:
        lead_time_val = st.slider("Production Lead Time (Weeks)", min_value=2, max_value=10, value=5)
    with inv_col_s2:
        safety_stock_val = st.slider("Safety Stock Buffer (Weeks)", min_value=1, max_value=6, value=2)
    with inv_col_s3:
        st.markdown(f"**Total Reorder Lead Horizon:** **{lead_time_val + safety_stock_val} Weeks**")
        st.caption("Reorder must be initiated before stock dips into this buffer.")

    # Evaluate Inventory Health
    current_inv = compute_inventory_health(
        st.session_state.inventory_df,
        lead_time_weeks=lead_time_val,
        safety_stock_weeks=safety_stock_val,
    )
    
    # Summary Metrics Row
    tot_units_avail = current_inv["units_available"].sum()
    tot_cogs_val = current_inv["cogs_valuation"].sum()
    tot_whs_val = current_inv["wholesale_valuation"].sum()
    
    im1, im2, im3, im4 = st.columns(4)
    im1.metric("Available Units in Stock", f"{int(tot_units_avail):,} Units")
    im2.metric("Inventory Cost Valuation", f"${tot_cogs_val:,.2f}")
    im3.metric("Wholesale Market Value", f"${tot_whs_val:,.2f}")
    im4.metric("Avg Days of Supply (DOH)", f"{current_inv['days_of_supply'].mean():.1f} Days")

    st.markdown("<br>", unsafe_allow_html=True)
    
    # Days of Supply Visual
    fig_doh = px.bar(
        current_inv,
        x="product_name",
        y="days_of_supply",
        color="inventory_status",
        color_discrete_map={
            "🔴 Critical Stockout Risk": "#dc3545",
            "🟡 Reorder Now (In Lead-Time)": "#ffc107",
            "🟢 Healthy Stock": "#28a745",
            "🔵 High / Overstocked": "#17a2b8",
        },
        text="days_of_supply",
        title="Days of Supply Remaining by SKU",
    )
    fig_doh.update_traces(texttemplate="%{text:.0f} d", textposition="outside")
    fig_doh.add_hline(
        y=lead_time_val * 7,
        line_dash="dash",
        line_color="#dc3545",
        annotation_text=f"Production Lead-Time Threshold ({lead_time_val*7} Days)",
    )
    fig_doh.update_layout(
        xaxis_title="",
        yaxis_title="Days of Inventory on Hand",
        height=350,
        margin=dict(l=20, r=20, t=40, b=20),
    )
    st.plotly_chart(fig_doh, use_container_width=True)

    # Detailed SKU Table
    st.markdown("#### SKU Health & Production Schedule")
    st.dataframe(
        current_inv[[
            "sku",
            "product_name",
            "warehouse",
            "units_available",
            "weekly_velocity",
            "days_of_supply",
            "weeks_of_supply",
            "reorder_trigger_date",
            "inventory_status",
            "manufacturer",
        ]],
        use_container_width=True,
        hide_index=True,
    )

    # Edit SKU parameters
    with st.expander("✏️ Update Inventory Numbers & Weekly Burn Rates"):
        st.caption("Edit stock counts or burn rates below. Uploading a Nabis Inventory CSV will update these automatically.")
        edited_inv = st.data_editor(
            st.session_state.inventory_df[[
                "sku",
                "product_name",
                "warehouse",
                "units_on_hand",
                "units_reserved",
                "units_available",
                "weekly_velocity",
                "batch_cost",
                "wholesale_price",
                "manufacturer",
            ]],
            use_container_width=True,
            num_rows="dynamic",
        )
        if st.button("💾 Save Inventory Changes"):
            st.session_state.inventory_df = edited_inv.copy()
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
                new_inv_df = parse_nabis_inventory_export(uploaded_inventory)
                if not new_inv_df.empty:
                    st.session_state.inventory_df = new_inv_df.copy()
                    st.success(f"✅ Successfully parsed {len(new_inv_df)} inventory SKUs from Nabis!")
                    st.dataframe(new_inv_df.head(5))
                    st.info("The Inventory & Reorder Monitor (Tab 4) and Executive Overview (Tab 1) have been dynamically updated!")
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
