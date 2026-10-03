YOUR FULLBLEED PROJECT

This ZIP contains the HTML and CSS that were in the playground when you clicked
Download project, the bundled fonts and licenses, and a Python renderer.

RUN IT

Use Python 3.10 or newer in a virtual environment. Extract this ZIP into a folder,
open a terminal in that folder, and run:

    python -m pip install -r requirements.txt
    python render.py

Open output/document.pdf. PNG previews and render.json are in output as well.
Edit input.html or style.css, then run python render.py again.

The requirement pins Fullbleed {{ENGINE_VERSION}}, matching the browser demo.
Installing it needs an internet connection. Rendering with these bundled assets
runs locally; your HTML and CSS are not uploaded. No browser or system fonts are
needed by this Python project. Additional assets you reference must be supplied
separately. The local package can handle jobs beyond the browser demo's limits.

KEEP BUILDING

Guide: https://docs.fullbleed.dev/getting-started/quickstart/
Watch for file changes: https://docs.fullbleed.dev/guides/render-watch/
Python API: https://docs.fullbleed.dev/engine/pdf-engine/
CSS support: https://docs.fullbleed.dev/css-coverage/
Help and examples: https://github.com/fullbleed-engine/fullbleed-official/discussions

project.json records hashes for the downloaded source, runner, and font files.
It describes the original download; your edits will change those hashes. Review
the PDF and all previews after editing. A successful render is not a PDF standards
conformance assessment.

LICENSES

Starter templates and render.py: MIT (LICENSE.txt).
Fonts: SIL Open Font License 1.1 (the *-OFL.txt files in fonts/).
Font attribution and exact source revisions: fonts/font-sources.json.
