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

st.title("📊 Market Risk Score Generator")

# Property name input
st.text_input("Property Name (for download file)", key="property_name", placeholder="e.g., Noma Flats, Spring Apartments")

# File uploads
col1, col2 = st.columns(2)

with col1:
    st.subheader("📄 CoStar Report")
    costar_file = st.file_uploader("Upload CoStar PDF", type="pdf", key="costar")

with col2:
    st.subheader("📋 Manual Data Document")
    manual_file = st.file_uploader("Upload manual data (Excel/PDF/Document)", type=["xlsx", "pdf", "docx"], key="manual")

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

                # Display scorecard as hierarchical structure (no repeated categories)
                st.markdown("### Scorecard: Category Details")

                for main_category, subcategories in scorecard_data.items():
                    st.markdown(f"#### {main_category}")

                    subcat_num = 1
                    for subcat, items in subcategories.items():
                        if isinstance(items, dict):
                            # Display subcategory name once
                            st.markdown(f"**{subcat_num}. {subcat}**")

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
                                # Use st.table() to remove column formatting options
                                st.table(df)

                            subcat_num += 1
                        else:
                            # Handle simple string items (no nested dict)
                            st.markdown(f"**{subcat_num}. {subcat}**")
                            st.write(items)
                            subcat_num += 1

                    st.markdown("---")

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

                property_name = st.session_state.get('property_name', 'Property')
                ws['A2'] = f"Property: {property_name}"
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
                property_name_clean = st.session_state.get('property_name', 'Property').replace(" ", "_")
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
