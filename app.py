import streamlit as st
from costar_extractor import CoStarExtractor
import tempfile
import os
import pandas as pd
from datetime import datetime
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

st.set_page_config(page_title="Market Risk Score Generator", page_icon="📊", layout="wide")

# Initialize session state for report persistence
if 'report_run' not in st.session_state:
    st.session_state.report_run = False
    st.session_state.report_data = None
    st.session_state.costar_file_id = None
    st.session_state.manual_file_id = None

# Formatting function for values
def format_value(value, unit_type=None):
    """Format values based on type"""
    if value is None or value == "":
        return "❌ Not found"
    if isinstance(value, float):
        if unit_type == "currency":  # Rents, prices
            return f"${value:,.0f}"
        elif unit_type == "percent":  # Percentages
            return f"{value:.2f}%"
        elif unit_type == "psf":  # Per square foot
            return f"${value:.2f}"
        else:
            return f"{value:.2f}"
    elif isinstance(value, int):
        if unit_type == "currency":
            return f"${value:,}"
        else:
            return f"{value:,}"
    return str(value)

# Custom CSS for professional app styling
st.markdown("""
<style>
    /* Overall app background - apply to all main containers */
    body, .stMainBlockContainer, [data-testid="stAppViewContainer"], .main {
        background: linear-gradient(135deg, #f0f4f8 0%, #e8ecf1 100%) !important;
    }

    /* Ensure container has background */
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #f0f4f8 0%, #e8ecf1 100%) !important;
    }

    .stMainBlockContainer {
        background: linear-gradient(135deg, #f0f4f8 0%, #e8ecf1 100%) !important;
    }

    /* Sidebar background */
    [data-testid="stSidebar"] {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    }

    /* Button styling - Professional deep blue gradient */
    div.stButton > button {
        background: linear-gradient(135deg, #1e3a8a 0%, #0f172a 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 14px 28px;
        font-weight: 700;
        font-size: 15px;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 4px 12px rgba(30, 58, 138, 0.25);
        letter-spacing: 0.3px;
    }

    div.stButton > button:hover:not(:disabled) {
        background: linear-gradient(135deg, #1e40af 0%, #1e3a8a 100%);
        box-shadow: 0 6px 20px rgba(30, 58, 138, 0.4);
        transform: translateY(-2px);
    }

    div.stButton > button:disabled {
        background: linear-gradient(135deg, #94a3b8 0%, #64748b 100%);
        color: #cbd5e1;
        cursor: not-allowed;
        opacity: 0.6;
    }

    /* Download button - match Run button styling */
    [data-testid="stDownloadButton"] button {
        background: linear-gradient(135deg, #1e3a8a 0%, #0f172a 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 14px 28px;
        font-weight: 700;
        font-size: 15px;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 4px 12px rgba(30, 58, 138, 0.25);
        letter-spacing: 0.3px;
    }

    [data-testid="stDownloadButton"] button:hover:not(:disabled) {
        background: linear-gradient(135deg, #1e40af 0%, #1e3a8a 100%);
        box-shadow: 0 6px 20px rgba(30, 58, 138, 0.4);
        transform: translateY(-2px);
    }

    [data-testid="stDownloadButton"] button:disabled {
        background: linear-gradient(135deg, #94a3b8 0%, #64748b 100%);
        color: #cbd5e1;
        cursor: not-allowed;
        opacity: 0.6;
    }

    /* Table styling - Professional and polished */
    .dataframe {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        border-collapse: collapse;
    }

    /* Dataframe header styling */
    .dataframe thead th {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%) !important;
        color: white !important;
        font-weight: 800 !important;
        padding: 16px 14px !important;
        text-align: left !important;
        border-bottom: 2px solid #1e3a8a !important;
        font-size: 13px !important;
        letter-spacing: 0.5px !important;
    }

    /* Dataframe row styling */
    .dataframe tbody td {
        padding: 14px 14px !important;
        border-color: #cbd5e1 !important;
        font-size: 14px !important;
        color: #1e293b !important;
        font-weight: 500 !important;
    }

    .dataframe tbody tr:nth-child(even) {
        background-color: #f8fafc !important;
    }

    .dataframe tbody tr:nth-child(odd) {
        background-color: #ffffff !important;
    }

    .dataframe tbody tr:hover {
        background-color: #e0e7ff !important;
        transition: background-color 0.2s ease;
    }

    /* Variable column - emphasis */
    .dataframe tbody td:nth-child(1) {
        font-weight: 600 !important;
        color: #0f172a !important;
    }

    /* Value column - emphasis */
    .dataframe tbody td:nth-child(2) {
        font-weight: 600 !important;
        color: #1e3a8a !important;
    }

    /* Manual input column - editable emphasis */
    .dataframe tbody td:nth-child(3) {
        font-weight: 500 !important;
        color: #0891b2 !important;
        background-color: #ecf0f1 !important;
    }

    /* Main category styling - LARGEST */
    .main-category {
        background: linear-gradient(135deg, #1e3a8a 0%, #1e40af 100%);
        color: white;
        font-weight: 800;
        padding: 18px;
        margin: 28px 0 18px 0;
        border-radius: 8px;
        font-size: 22px;
        letter-spacing: 1px;
        box-shadow: 0 6px 20px rgba(30, 58, 138, 0.3);
    }

    /* Subcategory styling - MEDIUM */
    .subcategory {
        background: linear-gradient(90deg, #e0e7ff 0%, #f0f4f9 100%);
        color: #0f172a;
        font-weight: 700;
        padding: 12px 14px;
        margin: 16px 0 12px 0;
        border-left: 5px solid #1e3a8a;
        border-radius: 4px;
        font-size: 16px;
        letter-spacing: 0.5px;
        box-shadow: 0 2px 6px rgba(30, 58, 138, 0.1);
    }

    /* Table header styling - SMALLER */
    .table-header {
        font-size: 13px;
        font-weight: 700;
        letter-spacing: 0.5px;
    }

    /* Input styling */
    input {
        border-radius: 6px !important;
        border: 2px solid #cbd5e1 !important;
        padding: 10px 12px !important;
        font-size: 14px !important;
    }

    input:focus {
        border-color: #1e3a8a !important;
        box-shadow: 0 0 0 3px rgba(30, 58, 138, 0.1) !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("📊 Market Risk Score Generator")

# File uploads
col1, col2 = st.columns(2)

with col1:
    st.subheader("📄 CoStar Report")
    costar_file = st.file_uploader("Upload CoStar PDF", type="pdf", key="costar")

with col2:
    st.subheader("📋 Manual Data Document")
    manual_file = st.file_uploader("Upload manual data (Excel/PDF/Document)", type=["xlsx", "pdf", "docx"], key="manual")

# Auto-recognize property name from CoStar filename (no UI input field)
if costar_file:
    property_name_input = costar_file.name.replace('.pdf', '').replace('_', ' ')
else:
    property_name_input = "Property"

# Run button - 50% width on left, Download button on right
run_col, download_col = st.columns(2)

with run_col:
    # Button is disabled if both files aren't uploaded
    run_clicked = st.button(
        "🚀 Run Market Score",
        use_container_width=True,
        disabled=(costar_file is None or manual_file is None)
    )

download_placeholder = download_col.empty()

# Track if files have changed
current_costar_id = id(costar_file) if costar_file else None
current_manual_id = id(manual_file) if manual_file else None

# Reset report if new files are uploaded
if (current_costar_id != st.session_state.costar_file_id or
    current_manual_id != st.session_state.manual_file_id):
    st.session_state.report_run = False
    st.session_state.report_data = None
    st.session_state.costar_file_id = current_costar_id
    st.session_state.manual_file_id = current_manual_id

# Show disabled download button initially
if not st.session_state.report_run:
    with download_placeholder:
        st.download_button(
            label="📥 Download Market Risk Score",
            data=b"",
            file_name="market_risk_score.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            disabled=True
        )

# Only proceed if both files exist AND run button was clicked AND report hasn't run yet
if costar_file and manual_file and run_clicked and not st.session_state.report_run:

        with tempfile.TemporaryDirectory() as tmpdir:
            costar_path = os.path.join(tmpdir, "costar.pdf")

            with open(costar_path, "wb") as f:
                f.write(costar_file.getbuffer())

            try:
                # Store execution flag
                st.session_state.report_run = True

                # Extract from CoStar
                st.subheader("📊 Market Risk Score Results")

                with st.status("Extracting CoStar metrics...", expanded=True):
                    extractor = CoStarExtractor(costar_path)
                    metrics = extractor.extract_all_metrics()
                    st.write("✅ CoStar extraction complete")

                    # Store metrics in session state for persistence
                    st.session_state.report_data = metrics

                    # Show extraction summary
                    found_metrics = sum(1 for v in metrics.values() if v is not None)
                    total_metrics = len(metrics)
                    st.write(f"📈 Found {found_metrics}/{total_metrics} metrics")

                    # Debugging: show which metrics were not found
                    missing = [k for k, v in metrics.items() if v is None]
                    if missing:
                        with st.expander("ℹ️ Debug: Metrics not found"):
                            st.write("**These metrics were not found in the CoStar PDF:**")
                            st.write(", ".join(missing))
                            st.write("This might be because:")
                            st.write("1. The PDF has different formatting or text layout")
                            st.write("2. The metric name uses different wording in the report")
                            st.write("3. The data is in a different section of the PDF")
                            st.info("📋 Tip: You can fill these missing values using the Manual Data document")

                # Define scorecard structure
                scorecard_data = {
                    "A. Demand Strength": {
                        "Employment & Wage Base": {
                            "Job Growth (%)": metrics.get('job_growth'),
                            "Local Unemployment Rate (%)": metrics.get('unemployment_rate'),
                            "Wage Growth vs Rent Growth": "⚠️ [From Manual Data]"
                        },
                        "Household Growth & In-Migration": {
                            "Household Growth (%)": "⚠️ [From Manual Data]",
                            "Population Growth (%)": metrics.get('population_growth')
                        },
                        "Net Absorption & Occupancy": {
                            "Net Absorption (units)": metrics.get('net_absorption'),
                            "Current Vacancy Rate (%)": metrics.get('current_vacancy_rate')
                        },
                        "Affordability Trajectory": "⚠️ [From Manual Data]",
                        "Bad Debts": "⚠️ [From Manual Data]"
                    },
                    "B. Supply Pressure": {
                        "Pipeline Volume": {
                            "Under Construction (units)": metrics.get('under_construction_units'),
                            "Pipeline Timing": "⚠️ [From Manual Data]"
                        },
                        "Lease-up Pace": {
                            "Deliveries Past 12M (units)": metrics.get('deliveries_12_months'),
                            "Lease-up Velocity": "⚠️ [From Manual Data]"
                        },
                        "Vacancy & Concessions Trend": {
                            "Current Vacancy (%)": metrics.get('current_vacancy_rate'),
                            "Concession Trend": "⚠️ [From Manual Data]"
                        },
                        "Barriers to Entry": "⚠️ [From Manual Data]"
                    },
                    "C. Competitive Positioning": {
                        "Effective Rent Comparables": {
                            "Avg Asking Rent ($)": metrics.get('avg_asking_rent'),
                            "Avg Effective Rent ($)": metrics.get('avg_effective_rent'),
                            "Rent per SF ($)": metrics.get('rent_per_sf')
                        },
                        "Micro-location Advantages": "⚠️ [From Manual Data]",
                        "Product & Amenity Differentiation": "⚠️ [From Manual Data]",
                        "Replacement Cost Gap": "⚠️ [From Manual Data]"
                    },
                    "D. Capital & Financing Risk": {
                        "Transaction Liquidity": {
                            "Sales Volume (12M)": metrics.get('sales_volume_12m'),
                            "Buyer Depth": "⚠️ [From Manual Data]"
                        },
                        "Cap Rate Trends": {
                            "Market Cap Rate (%)": metrics.get('cap_rate'),
                            "Rate Trend": "⚠️ [From Manual Data]"
                        },
                        "Market Rating": "⚠️ [From Manual Data]"
                    },
                    "E. Operating Cost Volatility": {
                        "Property Tax Reassessment": "⚠️ [From Manual Data]",
                        "Insurance Volatility": "⚠️ [From Manual Data]",
                        "Utilities Volatility": "⚠️ [From Manual Data]"
                    }
                }

                # Display scorecard as hierarchical structure with manual input
                st.markdown("### Scorecard: Category Details")

                # Use a form to prevent Enter from triggering reruns
                with st.form("manual_inputs_form"):
                    # Dictionary to store manual inputs
                    manual_inputs = {}

                    for main_category, subcategories in scorecard_data.items():
                        # Main category heading with color
                        st.markdown(f"""
                        <div class="main-category">
                        {main_category}
                        </div>
                        """, unsafe_allow_html=True)

                        subcat_num = 1
                        for subcat, items in subcategories.items():
                            if isinstance(items, dict):
                                # Subcategory with color
                                st.markdown(f"""
                                <div class="subcategory">
                                {subcat_num}. {subcat}
                                </div>
                                """, unsafe_allow_html=True)

                                # Display variables with manual input column
                                var_data = []
                                input_cols = {}

                                for item_name, item_value in items.items():
                                    # Format the extracted value
                                    if item_value is None:
                                        display_value = "❌ Not found"
                                        unit_type = None
                                    elif isinstance(item_value, str) and "[From Manual Data]" in item_value:
                                        display_value = item_value
                                        unit_type = None
                                    else:
                                        # Determine unit type for formatting
                                        unit_type = None
                                        if "rent" in item_name.lower() and "%" not in item_name.lower():
                                            if "per" in item_name.lower() or "psf" in item_name.lower() or "sf" in item_name.lower():
                                                unit_type = "psf"
                                            else:
                                                unit_type = "currency"
                                        elif "%" in item_name.lower() or "rate" in item_name.lower():
                                            unit_type = "percent"

                                        display_value = format_value(item_value, unit_type)

                                    var_data.append({
                                        "Variable": item_name,
                                        "Extracted Value": display_value,
                                        "Manual Input": ""
                                    })

                                    input_cols[item_name] = len(var_data) - 1

                                if var_data:
                                    # Display table with headers - centered
                                    head_col1, head_col2, head_col3 = st.columns([1.3, 1.1, 1.1])
                                    with head_col1:
                                        st.markdown("<b>Variable</b>")
                                    with head_col2:
                                        st.markdown("<div style='text-align: center;'><b>Extracted Value</b></div>", unsafe_allow_html=True)
                                    with head_col3:
                                        st.markdown("<div style='text-align: center;'><b>Manual Input</b></div>", unsafe_allow_html=True)

                                    # Display each row inline
                                    for idx, row in enumerate(var_data):
                                        col1, col2, col3 = st.columns([1.3, 1.1, 1.1])

                                        with col1:
                                            st.write(row["Variable"])

                                        with col2:
                                            st.markdown(f"<div style='text-align: center;'>{row['Extracted Value']}</div>", unsafe_allow_html=True)

                                        with col3:
                                            item_name = row["Variable"]
                                            manual_key = f"{main_category}_{subcat}_{item_name}".replace(" ", "_").replace("(", "").replace(")", "").replace("%", "").replace("$", "")

                                            # Determine unit type for this field
                                            unit_type = None
                                            if "rent" in item_name.lower() and "%" not in item_name.lower():
                                                if "per" in item_name.lower() or "psf" in item_name.lower() or "sf" in item_name.lower():
                                                    unit_type = "psf"
                                                else:
                                                    unit_type = "currency"
                                            elif "%" in item_name.lower() or "rate" in item_name.lower():
                                                unit_type = "percent"

                                            input_val = st.text_input(
                                                label=f"Input for {item_name}",
                                                value="",
                                                key=manual_key,
                                                label_visibility="collapsed"
                                            )
                                            manual_inputs[manual_key] = input_val

                                            # Show real-time formatted preview
                                            if input_val and input_val.strip():
                                                try:
                                                    formatted = format_value(float(input_val), unit_type)
                                                    st.write(f"✓ {formatted}")
                                                except (ValueError, TypeError):
                                                    st.write("⚠️ Invalid")

                                subcat_num += 1
                            else:
                                # Handle simple string items (no nested dict)
                                st.markdown(f"""
                                <div class="subcategory">
                                {subcat_num}. {subcat}
                                </div>
                                """, unsafe_allow_html=True)
                                st.write(items)
                                subcat_num += 1

                        st.markdown("")

                    # Submit button for form
                    submit_col1, submit_col2 = st.columns([1, 3])
                    with submit_col1:
                        st.form_submit_button("✅ Save Inputs", use_container_width=True)

                    # Store manual inputs
                    st.session_state['manual_inputs'] = manual_inputs

                # Summary
                st.info("✅ = Data from CoStar | ⚠️ = Requires manual data | ❌ = Not found in CoStar")

                # Create Excel file for download
                excel_file = BytesIO()
                wb = Workbook()
                ws = wb.active
                ws.title = "Market Risk Score"

                # Add property name and date
                ws['A1'] = "Market Risk Score Report"
                ws['A1'].font = Font(bold=True, size=14)

                ws['A2'] = f"Property: {property_name_input}"
                ws['A3'] = f"Date: {datetime.now().strftime('%m.%d.%Y')}"

                # Add extracted metrics
                row = 5
                ws['A5'] = "Extracted Metrics"
                ws['A5'].font = Font(bold=True, size=12)

                row = 6
                for metric_name, metric_value in metrics.items():
                    ws[f'A{row}'] = metric_name
                    if metric_value is None:
                        ws[f'B{row}'] = "Not found"
                    else:
                        ws[f'B{row}'] = metric_value
                    row += 1

                # Adjust column widths
                ws.column_dimensions['A'].width = 40
                ws.column_dimensions['B'].width = 20

                wb.save(excel_file)
                excel_file.seek(0)

                # Generate filename
                date_str = datetime.now().strftime('%m.%d.%Y')
                property_name_clean = property_name_input.replace(" ", "_") if property_name_input else "Property"
                filename = f"{property_name_clean}_Market Risk Score_{date_str}.xlsx"

                # Show download button in the placeholder (enabled after report runs)
                with download_placeholder:
                    st.download_button(
                        label="📥 Download Market Risk Score",
                        data=excel_file,
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )

            except Exception as e:
                st.session_state.report_run = False
                st.session_state.report_data = None
                st.error(f"❌ Error: {str(e)}")
                st.info("Make sure the PDF is a valid CoStar report.")

else:
    st.info("👆 Upload both documents to get started")
