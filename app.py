import streamlit as st
from costar_extractor import CoStarExtractor
from excel_filler import MarketScoreFiller
import tempfile
import os

st.set_page_config(page_title="Market Risk Score Generator", page_icon="📊", layout="wide")

st.title("📊 Market Risk Score Generator")
st.markdown("Auto-generate Market Risk Scores from CoStar reports. Upload a CoStar PDF and a Market Risk Score template.")

col1, col2 = st.columns(2)

with col1:
    st.subheader("📄 CoStar Report")
    costar_file = st.file_uploader("Upload CoStar PDF", type="pdf")

with col2:
    st.subheader("📋 Market Score Template")
    template_file = st.file_uploader("Upload Excel Template", type="xlsx")

if costar_file and template_file:
    st.divider()
    st.subheader("Processing...")

    with tempfile.TemporaryDirectory() as tmpdir:
        costar_path = os.path.join(tmpdir, "costar.pdf")
        template_path = os.path.join(tmpdir, "template.xlsx")

        with open(costar_path, "wb") as f:
            f.write(costar_file.getbuffer())

        with open(template_path, "wb") as f:
            f.write(template_file.getbuffer())

        try:
            with st.status("Extracting metrics...", expanded=True):
                extractor = CoStarExtractor(costar_path)
                metrics = extractor.extract_all_metrics()
                st.write("✅ Extraction complete")

            with st.status("Calculating scores...", expanded=True):
                demand_score = extractor.score_demand_strength(metrics)
                supply_score = extractor.score_supply_pressure(metrics)
                comp_score = extractor.score_competitive_positioning(metrics)
                financing_score = extractor.score_financing_risk(metrics)
                st.write("✅ Scores calculated")

                if demand_score:
                    st.metric("Demand Strength", f"{demand_score:.2f}/5")
                if supply_score:
                    st.metric("Supply Pressure", f"{supply_score:.2f}/5")

            with st.status("Filling workbook...", expanded=True):
                filler = MarketScoreFiller(template_path)
                category_scores = {
                    'demand_strength': demand_score,
                    'supply_pressure': supply_score,
                    'competitive_positioning': comp_score,
                    'financing_risk': financing_score
                }
                filler.fill_all_metrics(metrics, category_scores)
                output_path = os.path.join(tmpdir, "Market_Risk_Score_FILLED.xlsx")
                filler.save(output_path)
                st.write("✅ Workbook populated")

                with open(output_path, "rb") as f:
                    filled_data = f.read()

            st.success("✅ Complete!")
            st.download_button(
                label="📥 Download Filled Workbook",
                data=filled_data,
                file_name="Market_Risk_Score_FILLED.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            st.info("Make sure the PDF is a valid CoStar report and Excel matches the template.")

else:
    st.info("👆 Upload both files to get started")
