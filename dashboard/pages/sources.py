import streamlit as st
import pandas as pd


SOURCES = [
    {"Source": "Schools Week", "URL": "https://schoolsweek.co.uk/", "Status": "Automated", "Notes": ""},
    {"Source": "Department for Education (DfE)", "URL": "https://www.gov.uk/government/organisations/department-for-education", "Status": "Automated", "Notes": ""},
    {"Source": "EPI (Education Policy Institute)", "URL": "https://epi.org.uk/", "Status": "Automated", "Notes": ""},
    {"Source": "FFT Education Datalab", "URL": "https://ffteducationdatalab.org.uk/", "Status": "Automated", "Notes": ""},
    {"Source": "FED (Foundation for Education Development)", "URL": "https://fed.education/", "Status": "Automated", "Notes": ""},
    {"Source": "Chartered College of Teaching", "URL": "https://chartered.college/", "Status": "Under review", "Notes": ""},
    {"Source": "NFER (National Foundation for Educational Research)", "URL": "https://www.nfer.ac.uk/", "Status": "Under review", "Notes": ""},
    {"Source": "Nuffield Foundation", "URL": "https://www.nuffieldfoundation.org/", "Status": "Under review", "Notes": ""},
    {"Source": "EEF (Education Endowment Foundation)", "URL": "https://educationendowmentfoundation.org.uk/", "Status": "Under review", "Notes": ""},
    {"Source": "The Guardian Education", "URL": "https://www.theguardian.com/education", "Status": "Under review", "Notes": ""},
]

STATUS_COLORS = {
    "Automated": "#70ad47",
    "Under review": "#ed7d31",
}


def render():
    st.title("Newsletter Sources")
    st.markdown("Sources currently included in the automated pipeline, plus sources under review for future inclusion.")

    st.markdown("")

    sources_df = pd.DataFrame(SOURCES)

    status_counts = sources_df["Status"].value_counts()
    col1, col2, col3 = st.columns(3)
    col1.metric("Total sources", len(sources_df))
    col2.metric("Automated", status_counts.get("Automated", 0))
    col3.metric("Under review", status_counts.get("Under review", 0))

    st.subheader("Currently in the pipeline")
    for _, row in sources_df[sources_df["Status"] == "Automated"].iterrows():
        status_badge = f"<span style='background-color:{STATUS_COLORS['Automated']};color:white;padding:2px 8px;border-radius:4px;font-size:0.8em;'>Automated</span>"
        st.markdown(
            f"<a href='{row['URL']}' target='_blank'>{row['Source']}</a> {status_badge}",
            unsafe_allow_html=True,
        )

    st.subheader("Under review for inclusion")
    for _, row in sources_df[sources_df["Status"] == "Under review"].iterrows():
        status_badge = f"<span style='background-color:{STATUS_COLORS['Under review']};color:white;padding:2px 8px;border-radius:4px;font-size:0.8em;'>Under review</span>"
        notes_html = f" \u00b7 <em>{row['Notes']}</em>" if row["Notes"] else ""
        st.markdown(
            f"<a href='{row['URL']}' target='_blank'>{row['Source']}</a> {status_badge}{notes_html}",
            unsafe_allow_html=True,
        )

    st.markdown("")
    st.caption("**Automated** = articles from this source are pulled into the pipeline automatically each week. **Under review** = source is being evaluated for inclusion in a future update.")
