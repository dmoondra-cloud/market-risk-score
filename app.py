import streamlit as st
from costar_extractor import CoStarExtractor
import tempfile
import os
import pandas as pd

st.set_page_config(page_title="Market Risk Score Generator", page_icon="📊", layout="wide")

st.title("📊 Market Risk Score Generator")

# File uploads
col1, col2 = st.columns(2)

with col1:
    st.subheader("📄 CoStar Report")
    costar_file = st.file_uploader("Upload CoStar PDF", type="pdf", key="costar")

with col2:
    st.subheader("📋 Manual Data Document")
    manual_file = st.file_uploader("Upload manual data (Excel/PDF/Document)", type=["xlsx", "pdf", "docx"], key="manual")

# Run button
if costar_file and manual_file:
    if st.button("🚀 Run Market Score", use_container_width=True):

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

                # Display scorecard as structured table
                st.markdown("### Scorecard: Category Details")

                for main_category, subcategories in scorecard_data.items():
                    st.markdown(f"#### {main_category}")

                    table_data = []
                    for subcat, items in subcategories.items():
                        if isinstance(items, dict):
                            for item_name, item_value in items.items():
                                if item_value is None:
                                    display_value = "❌ Not found"
                                elif isinstance(item_value, float):
                                    display_value = f"{item_value:.2f}"
                                else:
                                    display_value = str(item_value)

                                table_data.append({
                                    "Subcategory": subcat,
                                    "Variable": item_name,
                                    "Value": display_value
                                })
                        else:
                            table_data.append({
                                "Subcategory": subcat,
                                "Variable": "-",
                                "Value": items
                            })

                    if table_data:
                        df = pd.DataFrame(table_data)
                        st.dataframe(df, use_container_width=True, hide_index=True)

                    st.markdown("---")

                # Summary
                st.info("✅ = Data from CoStar | ⚠️ = Requires manual data | ❌ = Not found in CoStar")

                # Download prepared template
                st.subheader("📥 Next Step")
                st.write("Review the extracted data above. Fill in the ⚠️ variables from your manual data document, then generate final scores.")

            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                st.info("Make sure the PDF is a valid CoStar report.")

else:
    st.info("👆 Upload both documents to get started")
