# 🌺 Auntie Aloha Business Dashboard

An interactive operations and financial intelligence dashboard for **Auntie Aloha**, unifying:
- **13-Week Cash Flow & Runway Forecasting**
- **Nabis Wholesale Remittance & Realization Analysis**
- **Inventory Depletion & Manufacturing Reorder Triggers**
- **QuickBooks Online P&L, Royalties & Production Accounting**

---

## 🚀 Quickstart

### Run Locally (Windows)
Double-click `run_dashboard.bat`, or run:
```bash
pip install -r requirements.txt
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

### Deploy to Streamlit Community Cloud
1. Sign in to [share.streamlit.io](https://share.streamlit.io) with GitHub.
2. Select repository `khchan8/auntie-aloha-dashboard`, branch `main`, and main file `app.py`.
3. Click **Deploy**.

---

## 📁 Repository Structure

```
├── app.py                      # Main Streamlit web dashboard
├── requirements.txt            # Python dependencies (Streamlit, Plotly, Pandas, etc.)
├── run_dashboard.bat           # 1-click Windows launcher
├── src/
│   ├── data_loader.py          # Parsers for Nabis remittances, inventory & QBO exports
│   ├── cashflow_engine.py      # 13-week cash flow and scenario simulation engine
│   ├── inventory_engine.py     # Inventory health, burn rates, days of supply (DOH)
│   └── qbo_client.py           # QuickBooks Online API hooks and report parsers
├── Auntie Aloha Cashflow Model.xlsx
├── Auntie Aloha Email Sources Summary.md
└── NABIS REMITTANCES 2025 TO YTD/
    ├── 2025/                   # Historical 2025 Nabis bi-weekly remittance statements
    └── 2026/                   # 2026 YTD Nabis statements and fee details
```
