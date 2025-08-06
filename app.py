import streamlit as st
import pandas as pd
from streamlit_quill import st_quill
import functions.data as db
from functions.export_utils import generate_report_html, convert_html_to_pdf, convert_html_to_png
from functions.func_summary import save_athlete_summary, get_athlete_summary, delete_athlete_summary
import streamlit.components.v1 as components

favicon_url = st.secrets.get("SUPABASE_FAVICON_URL", "assets/favicon.ico")

components.html(
    f"""<link rel="icon" href="{favicon_url}" type="image/x-icon" />""",
    height=0,
)

# --- PAGE SETUP ---
st.set_page_config(
    page_title="SLO Combine App",
    layout="wide",
)

# --- Shared Assets ---
st.logo("assets/code8perf_logo.png")

# --- SIDEBAR: Athlete Selector ---
roster_df = db.dfAthleteSignUp

if roster_df is not None and isinstance(roster_df, pd.DataFrame) and "Name" in roster_df.columns:
    selected_name = st.sidebar.selectbox("Select Athlete", options=roster_df["Name"].tolist())
    st.session_state["selected_name"] = selected_name

    if selected_name:
        st.sidebar.divider()

        # Summary Editor
        with st.sidebar.expander("📝 Athlete Summary", expanded=False):
            st.write(f"**Athlete:** {selected_name}")
            existing_summary = get_athlete_summary(selected_name)
            summary_content = st_quill(
                placeholder="Enter summary notes for the athlete...",
                html=True,
                value=existing_summary,
                key=f"summary_editor_{selected_name}"
            )

            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 Save", key="save_summary", use_container_width=True):
                    if summary_content and summary_content.strip():
                        if save_athlete_summary(selected_name, summary_content):
                            st.success("Summary saved!")
                            st.rerun()
                    else:
                        st.warning("Please enter some content before saving.")
            with col2:
                if st.button("🗑️ Delete", key="delete_summary", use_container_width=True):
                    if delete_athlete_summary(selected_name):
                        st.success("Summary deleted!")
                        st.rerun()

        # Export Options
        with st.sidebar.expander("📤 Export Report", expanded=False):
            if st.button("🖨️ Export PDF", key="export_pdf_btn"):
                with st.spinner("Generating PDF report..."):
                    try:
                        report_html = generate_report_html(selected_name)
                        pdf_bytes = convert_html_to_pdf(report_html)
                        st.sidebar.download_button(
                            label="📄 Download PDF",
                            data=pdf_bytes,
                            file_name=f"{selected_name.replace(' ', '_')}_Report.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                    except Exception as e:
                        st.sidebar.error(f"PDF export failed: {e}")

            if st.button("🖼️ Export PNG", key="export_png_btn"):
                with st.spinner("Generating PNG report..."):
                    try:
                        report_html = generate_report_html(selected_name)
                        png_bytes = convert_html_to_png(report_html)
                        st.sidebar.download_button(
                            label="🖼️ Download PNG",
                            data=png_bytes,
                            file_name=f"{selected_name.replace(' ', '_')}_Report.png",
                            mime="image/png",
                            use_container_width=True
                        )
                    except Exception as e:
                        st.sidebar.error(f"PNG export failed: {e}")

# --- SIDEBAR FOOTER ---
st.sidebar.markdown("---")
st.sidebar.text("Powered by Greenhouse Performance")

# --- PAGE DEFINITIONS ---
home_page = st.Page(page="views/home_dash.py", title="Report Home", icon=":material/widgets:", default=True)
hd_page = st.Page(page="views/hd_data.py", title="Force Plate Data", icon=":material/cruelty_free:")
swift_page = st.Page(page="views/swift_data.py", title="Swift Data", icon=":material/sprint:")
valor_page = st.Page(page="views/valor_data.py", title="Valor Data", icon=":material/sports_gymnastics:")
vert_jump_page = st.Page(page="views/vert_jump_data.py", title="Vertical Jump Data", icon=":material/sports_handball:")
broad_jump_page = st.Page(page="views/broad_jump_data.py", title="Broad Jump Data", icon=":material/linear_scale:")

# --- NAVIGATION ---
pg = st.navigation({
    "Report": [home_page],
    "Data": [hd_page, swift_page, valor_page, vert_jump_page, broad_jump_page],
})

# --- RUN PAGE ---
pg.run()
