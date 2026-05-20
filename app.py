"""
Market Risk Score Generator
Streamlit app for auto-filling Market Risk Score workbooks from CoStar PDFs
"""

import streamlit as st
import tempfile
import os
from pathlib import Path
from costar_extractor import CoStarExtractor
from excel_filler import MarketScoreFiller


# Page config
st.set_page_config(
    page_title="Market Risk Score Generator",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📊 Market Risk Score Generator")
st.markdown("""
Generate automated Market Risk Scores from CoStar reports.
Upload a CoStar PDF and a Market Risk Score template to auto-populate scores.
""")

# Sidebar
st.sidebar.header("Instructions")
st.sidebar.markdown("""
1. **Upload CoStar PDF** - The underwriting report for the property
2. **Upload Market Score Template** - Your Excel template (Stage 2 Market Score)
3. **Generate Report** - System will extract metrics and fill the workbook
4. **Download** - Get your completed market score workbook

### Metrics Auto-Filled
✅ **Employment & Wage Base** (Job Growth, Unemployment)
✅ **Household & Population Growth**
✅ **Vacancy & Absorption Trends**
✅ **Pipeline & Deliveries**
✅ **Rent Comparables**
✅ **Sales Activity & Liquidity**
✅ **Cap Rates**

⚠️ **Manual Input Required**
- Property Tax Reassessment Cadence
- Insurance Volatility
- Utilities Volatility
- Replacement Cost Gap
- Bad Debts
- Wage Growth (vs Rent Growth)
- Affordability Trajectory
""")

# Main app
col1, col2 = st.columns(2)

with col1:
    st.subheader("📄 CoStar Report")
    costar_file = st.file_uploader(
        "Upload CoStar PDF",
        type="pdf",
        help="Upload the CoStar underwriting report"
    )

with col2:
    st.subheader("📋 Market Score Template")
    template_file = st.file_uploader(
        "Upload Market Score Template",
        type="xlsx",
        help="Upload your Stage 2 Market Score Excel template"
    )

if costar_file and template_file:
    st.divider()

    # Create temporary files
    with tempfile.TemporaryDirectory() as tmpdir:
        # Save uploaded files
        costar_path = os.path.join(tmpdir, "costar.pdf")
        template_path = os.path.join(tmpdir, "template.xlsx")

        with open(costar_path, "wb") as f:
            f.write(costar_file.getbuffer())

        with open(template_path, "wb") as f:
            f.write(template_file.getbuffer())

        # Process
        st.subheader("Processing...")
        progress_bar = st.progress(0)

        try:
            # Step 1: Extract CoStar data
            with st.status("Extracting CoStar metrics...", expanded=True):
                progress_bar.progress(20)
                extractor = CoStarExtractor(costar_path)
                metrics = extractor.extract_all_metrics()
                st.write("✅ Extraction complete")

                # Display extracted metrics
                with st.expander("View Extracted Metrics"):
                    metric_cols = st.columns(3)
                    idx = 0
                    for key, value in metrics.items():
                        if value is not None:
                            with metric_cols[idx % 3]:
                                st.metric(key.replace('_', ' ').title(), f"{value:.2f}" if isinstance(value, float) else value)
                            idx += 1

            progress_bar.progress(50)

            # Step 2: Calculate scores
            with st.status("Calculating category scores...", expanded=True):
                progress_bar.progress(70)

                demand_score = extractor.score_demand_strength(metrics)
                supply_score = extractor.score_supply_pressure(metrics)
                comp_score = extractor.score_competitive_positioning(metrics)
                financing_score = extractor.score_financing_risk(metrics)

                category_scores = {
                    'demand_strength': demand_score,
                    'supply_pressure': supply_score,
                    'competitive_positioning': comp_score,
                    'financing_risk': financing_score
                }

                st.write("✅ Scores calculated")

                # Display calculated scores
                score_cols = st.columns(2)
                if demand_score:
                    with score_cols[0]:
                        st.metric("Demand Strength", f"{demand_score:.2f}/5", delta="Category Score")
                if supply_score:
                    with score_cols[1]:
                        st.metric("Supply Pressure", f"{supply_score:.2f}/5", delta="Category Score")
                if comp_score:
                    with score_cols[0]:
                        st.metric("Competitive Positioning", f"{comp_score:.2f}/5", delta="Category Score")
                if financing_score:
                    with score_cols[1]:
                        st.metric("Financing Risk", f"{financing_score:.2f}/5", delta="Category Score")

            progress_bar.progress(80)

            # Step 3: Fill workbook
            with st.status("Filling Excel workbook...", expanded=True):
                progress_bar.progress(90)

                filler = MarketScoreFiller(template_path)
                filler.fill_all_metrics(metrics, category_scores)

                output_path = os.path.join(tmpdir, "Market_Risk_Score_FILLED.xlsx")
                filler.save(output_path)

                st.write("✅ Workbook populated")

                # Read filled file for download
                with open(output_path, "rb") as f:
                    filled_data = f.read()

            progress_bar.progress(100)

            st.divider()
            st.success("✅ Market Risk Score generated successfully!")

            # Download button
            st.download_button(
                label="📥 Download Filled Workbook",
                data=filled_data,
                file_name="Market_Risk_Score_FILLED.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

            # Summary
            st.subheader("Summary")
            summary_cols = st.columns(2)

            with summary_cols[0]:
                st.info(f"""
                **Metrics Extracted:** {sum(1 for v in metrics.values() if v is not None)}

                **Categories Scored:** {sum(1 for v in category_scores.values() if v is not None)}
                """)

            with summary_cols[1]:
                st.warning("""
                **Still Need Manual Input:**
                - Property Tax Cadence
                - Insurance Risk
                - Utilities Volatility
                - Replacement Cost
                - Bad Debts
                """)

        except Exception as e:
            st.error(f"❌ Error processing files: {str(e)}")
            st.error("Make sure the PDF is a valid CoStar report and the Excel file is the correct template format.")

else:
    st.info("👆 Upload both files above to get started")
