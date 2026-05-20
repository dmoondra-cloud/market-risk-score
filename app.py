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

# Custom CSS for professional styling with cool tones
st.markdown("""
<style>
    /* Button styling - Cool professional deep blue */
    div.stButton > button {
        background: linear-gradient(135deg, #1e3a8a 0%, #0f172a 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 12px 24px;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 2px 8px rgba(30, 58, 138, 0.2);
    }

    div.stButton > button:hover {
        background: linear-gradient(135deg, #1e40af 0%, #1e3a8a 100%);
        box-shadow: 0 4px 16px rgba(30, 58, 138, 0.35);
        transform: translateY(-2px);
    }

    /* Table styling - Cool professional colors */
    .dataframe {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }

    /* Dataframe header styling */
    .dataframe thead th {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%) !important;
        color: white !important;
        font-weight: 700 !important;
        padding: 14px !important;
        text-align: left !important;
        border-bottom: 2px solid #1e3a8a !important;
    }

    /* Dataframe row styling */
    .dataframe tbody td {
        padding: 12px 14px !important;
        border-color: #d1d5db !important;
    }

    .dataframe tbody tr:nth-child(even) {
        background-color: #f3f7fb !important;
    }

    .dataframe tbody tr:hover {
        background-color: #e0e7ff !important;
    }

    /* Main category styling */
    .main-category {
        background: linear-gradient(135deg, #1e3a8a 0%, #1e40af 100%);
        color: white;
        font-weight: 700;
        padding: 14px;
        margin: 20px 0 12px 0;
        border-radius: 6px;
        font-size: 16px;
        letter-spacing: 0.5px;
        box-shadow: 0 2px 8px rgba(30, 58, 138, 0.15);
    }

    /* Subcategory styling */
    .subcategory {
        background-color: #f0f4f9;
        color: #0f172a;
        font-weight: 600;
        padding: 10px 12px;
        margin: 12px 0 8px 0;
        border-left: 4px solid #1e3a8a;
        border-radius: 4px;
        font-size: 14px;
    }

    /* Variable and Value column distinction */
    .data-variable {
        color: #0f172a;
        font-weight: 500;
    }

    .data-value {
        color: #1e3a8a;
        font-weight: 600;
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

# Auto-recognize property name from CoStar filename
if costar_file:
    property_name_from_file = costar_file.name.replace('.pdf', '').replace('_', ' ')
    property_name_input = st.text_input(
        "Property Name (for download file)",
        value=property_name_from_file,
        placeholder="e.g., Noma Flats, Spring Apartments"
    )
else:
    property_name_input = st.text_input(
        "Property Name (for download file)",
        placeholder="e.g., Noma Flats, Spring Apartments"
    )

# Run button - 50% width on left, Download button on right
if costar_file and manual_file:
    run_col, download_col = st.columns(2)

    with run_col:
        run_clicked = st.button("🚀 Run Market Score", use_container_width=True)

    download_placeholder = download_col.empty()

    if run_clicked:

        with tempfile.TemporaryDirectory() as tmpdir:
            costar_path = os.path.join(tmpdir, "costar.pdf")

            with open(costar_path, "wb") as f:
                f.write(costar_file.getbuffer())

            try:
                # Extract from CoStar
                st.subheader("📊 Market Risk Score Results")

                with st.status("Extracting CoStar metrics...", expanded=True):
                    extractor = CoStarExtractor(costar_path)
                    metrics = extractor.extract_all_metrics()
                    st.write("✅ CoStar extraction complete")

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

                # Display scorecard as hierarchical structure with color coding
                st.markdown("### Scorecard: Category Details")

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

                            # Display variables under this subcategory
                            var_data = []
                            for item_name, item_value in items.items():
                                if item_value is None:
                                    display_value = "❌ Not found"
                                elif isinstance(item_value, float):
                                    display_value = f"{item_value:.2f}"
                                else:
                                    display_value = str(item_value)

                                var_data.append({
                                    "Variable": item_name,
                                    "Value": display_value
                                })

                            if var_data:
                                df = pd.DataFrame(var_data)
                                # Use dataframe with disabled interactions and custom styling
                                st.dataframe(
                                    df,
                                    use_container_width=True,
                                    hide_index=True,
                                    column_config={
                                        "Variable": st.column_config.TextColumn(width="medium"),
                                        "Value": st.column_config.TextColumn(width="medium"),
                                    },
                                    disabled=True
                                )

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

                # Show download button in the placeholder
                with download_placeholder:
                    st.download_button(
                        label="📥 Download Market Risk Score",
                        data=excel_file,
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )

            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                st.info("Make sure the PDF is a valid CoStar report.")

else:
    st.info("👆 Upload both documents to get started")
