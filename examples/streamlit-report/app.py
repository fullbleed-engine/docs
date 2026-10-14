"""A local Streamlit data app with explicit preparation and PDF downloads."""
from hashlib import sha256
import streamlit as st

from report import ROOT, document, fingerprint, load_sales, money, render_report, select_sales, totals

st.set_page_config(page_title="Sales brief · Fullbleed", page_icon="📄", layout="wide")


def invalidate():
    st.session_state.pop("prepared_report", None)


st.caption("FULLBLEED × STREAMLIT")
st.title("Sales report studio")
st.write("Filter the sales records, prepare the report, and download a PDF with the same selection.")

with st.sidebar:
    st.header("Report data")
    uploaded = st.file_uploader("Sales CSV", type=["csv"], on_change=invalidate,
                               help="UTF-8, at most 64 KiB and 250 records. Use the sample's columns.")
    sample = (ROOT / "sales.csv").read_bytes()
    st.download_button("Download sample CSV", sample, "sales.csv", "text/csv", on_click="ignore")
    st.caption("The included Northstar Supply data is fictional.")

try:
    rows = load_sales(uploaded.getvalue() if uploaded is not None else sample)
except ValueError as exc:
    invalidate()
    st.error(str(exc))
    st.stop()

first, last = min(r.day for r in rows), max(r.day for r in rows)
available_regions = sorted({r.region for r in rows})
available_channels = sorted({r.channel for r in rows})
# Dataset-specific widget keys avoid carrying stale options through an invalid
# upload, where Streamlit removes widgets that were not rendered in that run.
data_key = sha256(uploaded.getvalue() if uploaded is not None else sample).hexdigest()
if st.session_state.get("dataset_key") != data_key:
    invalidate()
    st.session_state.dataset_key = data_key

with st.sidebar:
    st.header("Selection")
    window = st.date_input("Date range", value=(first, last), min_value=first, max_value=last,
                           key="window_" + data_key, on_change=invalidate)
    regions = st.multiselect("Regions", available_regions, default=available_regions,
                             key="regions_" + data_key, on_change=invalidate)
    channel = st.selectbox("Channel", ["", *available_channels], key="channel_" + data_key, on_change=invalidate,
                           format_func=lambda value: "All channels" if not value else "Only " + value)
    name = st.text_input("Report name", "Northstar Supply / Quarterly review", max_chars=48, on_change=invalidate)

if len(window) != 2 or not regions:
    invalidate()
    st.info("Choose a complete date range and at least one region.")
    st.stop()
selected = select_sales(rows, window[0], window[1], regions, channel or None)
if not selected:
    invalidate()
    st.info("No records match these filters. Change the selection to prepare a report.")
    st.stop()
orders, revenue = totals(selected)
for column, title, value in zip(st.columns(3), ["Revenue", "Orders", "Records"],
                                [money(revenue), f"{orders:,}", f"{len(selected):,}"]):
    column.metric(title, value)
st.dataframe([{"Row": f"R{r.row:03}", "Date": r.day.isoformat(), "Region": r.region,
               "Channel": r.channel, "Orders": r.orders, "Revenue (USD)": money(r.cents).removeprefix("USD ")}
              for r in selected], hide_index=True, height=280, width="stretch")

try:
    html, css = document(selected, name, window[0], window[1], regions,
                         channel or None)
except ValueError as exc:
    invalidate()
    st.error(str(exc))
    st.stop()
prepared = st.session_state.get("prepared_report")
if prepared and prepared["signature"] != fingerprint(html, css):
    invalidate()

if st.button("Prepare PDF", type="primary"):
    invalidate()
    try:
        with st.spinner("Laying out your report…"):
            result = render_report(html, css)
        result["summary"] = f"{name} · {window[0].isoformat()} to {window[1].isoformat()} · {', '.join(regions)} · {channel or 'All channels'} · {len(selected)} records"
        st.session_state.prepared_report = result
    except ValueError as exc:
        st.error(str(exc))
    except Exception:
        st.error("The report could not be prepared. Check the local template and try again.")

prepared = st.session_state.get("prepared_report")
if prepared:
    st.subheader("Prepared report")
    st.caption(prepared["summary"])
    st.download_button("Download prepared PDF", prepared["pdf"], "sales-brief.pdf", "application/pdf",
                       on_click="ignore", type="primary")
    st.pdf(prepared["pdf"], height=720, key="pdf_" + prepared["signature"],
           alt="Sales report for the prepared selection")
else:
    st.caption("Prepare a PDF after changing the data or selection. Downloads describe the prepared selection shown above them.")

st.divider()
st.caption("A local example powered by Fullbleed. Edit report.html and report.css to make the print design yours.")
