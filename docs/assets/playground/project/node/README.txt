YOUR FULLBLEED PROJECT — NODE.JS

This ZIP contains the HTML and CSS present when you clicked Download project.
The document is rendered locally. Use Node.js 22 or newer.

1. Extract the ZIP into a folder and open a terminal there.
2. Install the pinned dependencies:

   npm ci --ignore-scripts

3. Render your document:

   npm run render

Open output/document.pdf. PNG previews are in output/preview/, and
output/render.json records the engine version, page count and PDF hash.
Edit input.html or style.css and run npm run render again.

The package is fullbleed {{PACKAGE_VERSION}}, containing engine {{ENGINE_VERSION}}
to match this playground. package-lock.json pins its dependency integrity.
The renderer uses defaultStyles: false to preserve your original CSS cascade.
It loads the bundled font files from fonts/ and resolves paths beside render.mjs,
so you can also run node /path/to/this/project/render.mjs from another folder.

Static HTML/CSS is supported. Scripts inside your document do not execute and
remote document assets are not fetched. Use inline SVG for artwork. Local Node
rendering has its own configurable limits; the browser demo's six-page limit
does not apply to this project.

project.json records the downloaded file hashes. These describe the original
download; you can edit your HTML/CSS normally. License notices for the bundled
fonts are in fonts/. The project code is MIT licensed; see LICENSE.txt.

Documentation: https://docs.fullbleed.dev/getting-started/node/
