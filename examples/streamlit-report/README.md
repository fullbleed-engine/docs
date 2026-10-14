# Streamlit sales report with Fullbleed

Filter a small sales dataset, prepare a designed PDF, and download the result.
The sample uses fictional Northstar Supply data: 36 weekly records, 2,628 orders,
and USD 222,099.30 in revenue. The unfiltered report has two A4 pages.

Use Python 3.11. From this directory:

```sh
python -m venv .venv
```

Activate it with `source .venv/bin/activate` on macOS/Linux or
`.venv\Scripts\Activate.ps1` in Windows PowerShell, then run:

```sh
python -m pip install -r requirements.txt
python -m streamlit run app.py --server.address 127.0.0.1
```

Open `http://127.0.0.1:8501`. Choose a date range, regions, and channel, then
select **Prepare PDF**. Check the prepared selection and preview before using
**Download prepared PDF**. Changing a committed input clears the prepared report;
prepare it again to download the new selection. Downloading does not rerun the app.

The download is a snapshot of the prepared selection, including its report name.
Finish editing a field before preparing the report. The viewer's page and zoom controls preserve
that snapshot. Reloading or disconnecting the browser can reset Streamlit's session.

## Use your data

Upload a UTF-8 CSV with these columns in this order:

```csv
date,region,channel,orders,revenue_usd
2026-07-06,East,Online,24,1392.00
```

- Dates use `YYYY-MM-DD`; both ends of the selected range are included.
- Region and channel names have 1–24 characters after trimming. Control
  characters are rejected. The bundled fonts must cover the characters.
- Order counts are integers from 0 through 100,000. Revenue is from 0 through
  USD 1,000,000 per record, with at most two decimal places and no currency symbols.
- The example accepts at most 250 records, 64 KiB, six regions, and six channels.
  Streamlit's upload transport limit is 1 MiB; the parser applies the smaller limit.

The app sums integer cents and displays exact amounts. Large headline numbers
are abbreviated; their exact values appear underneath and in the ledger total.
It does not calculate tax, deduplicate transactions, or convert currencies.
Rows are sorted by date, region, channel, and original record number. `R001`
identifies the first data record in the CSV, including after filtering.

## Change the print design

Edit `report.html` and `report.css`. They are read when the app reruns; no browser
JavaScript or remote assets participate in PDF generation. The print design is
independent of Streamlit's dashboard CSS. `report.py` escapes text before inserting
it into the template. Do not remove that escaping when connecting another source.

The HTML uses Python `string.Template` placeholders, such as `$name`, `$rows`,
`$revenue`, and `$region_bars`. Use `$$` for a literal dollar sign. Group bars
compare revenue against the largest group in that chart; exact amounts remain
selectable text. Rows and the table header flow across pages for longer data.

Fullbleed loads Inter from its wheel and the included DM Serif Display font.
The display font's SIL Open Font License is in `fonts/DMSerifDisplay-OFL.txt`;
Fullbleed's bundled font licenses accompany that package. Add fonts explicitly
in `render_report` for another writing system, then inspect the resulting PDF.

Render the same sample without starting Streamlit:

```sh
python report.py --out output
```

This writes `output/report.pdf` and the expanded HTML.
Use `--csv your-data.csv` for a different complete dataset. The app itself returns
PDF bytes in its current session, without writing generated reports to disk.
Streamlit's first-party `streamlit-pdf` component displays that same PDF in the
browser. It is a viewer; Fullbleed generates the document on the Python server.
The prepared PDF is limited to 8 MiB in this example.

## Integrate into an existing app

`load_sales`, `select_sales`, `document`, and `render_report` are independent of
Streamlit. The app stores prepared bytes in `st.session_state`, with a fingerprint
of the rendered HTML/CSS, and does not use a shared `st.cache_data` cache for reports.
The download explicitly uses `mime="application/pdf"` and `on_click="ignore"`.

This is a local example, not an authenticated document service. A hosted app runs
Fullbleed on its server and receives uploaded data. Add your application's access,
capacity and retention controls before handling real private records. The example
does not establish production capacity or PDF standards conformance.

Fullbleed is MIT licensed; this example's license is in `LICENSE`.
