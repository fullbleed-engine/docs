# Main website source

`squarespace-home.html` is the maintained HTML code block for
[www.fullbleed.dev](https://www.fullbleed.dev/). Squarespace owns the surrounding
navigation, footer and page metadata. This directory is not deployed by MkDocs.

The homepage leads with component authoring, includes a runnable stable Python
example, and links to the component alpha notebook, paired Northstar/Common
Ground sources, and the accessible showcase with its retained validation reports.
The alpha is explicitly labeled; an ordinary install still selects the stable API.

`homepage-example.py` is the exact copyable example. With Python 3.10–3.14:

```sh
python -m pip install fullbleed
python website/homepage-example.py
```

It writes `order.pdf` in the current directory and registers the bundled Inter
font explicitly. The example was verified with the published 2.5.31 wheel:
one page, the expected text, embedded fonts, and identical PDF bytes on repeat
rendering. It does not claim PDF/UA conformance.

To update Squarespace, back up the current homepage code block and global code
injection, review the candidate in the existing public page shell, and replace
only the homepage block. Verify the saved page anonymously at desktop and mobile
widths, including real clipboard contents and linked PDF downloads. Do not paste
this block into global code injection. Keep the copyable example synchronized
with `homepage-example.py`.
