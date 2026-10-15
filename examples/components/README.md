# Fullbleed Python components

Requires Python 3.10 or newer. This is a complete fictional invoice built with
named components, ordinary Python functions and Python style mappings.

```sh
python -m venv .venv
# Activate .venv for your shell, then:
python -m pip install -r requirements.txt
python invoice.py
```

Open output/invoice.pdf or output/page-1.png. Change data.json, the reusable
functions in invoice.py, or the StyleSheet in styles.py. Set paid to true to see
conditional content. Generated HTML/CSS is also saved for inspection.

The Inter font is included in the Fullbleed package. No font download or system
font is required. See https://docs.fullbleed.dev/guides/python-components/.
