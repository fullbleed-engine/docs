# Python components in a notebook

Open `bootstrap_components.ipynb` in Colab or local Jupyter and choose **Run all**.
The first cell installs the published `fullbleed==2.6.0a5` wheel. This is an
experimental API, with documented CSS limits.

Edit the order data and accent colour, then rerun from the edited cell onward.
The example uses components, reusable styles and named parts without authored
HTML strings. It writes a PDF, styled and unstyled HTML, page previews, and a ZIP
containing the current outputs. All data is fictional; the sample omits taxes,
shipping and discounts.

The code needs a standard CPU runtime, a compatible CPython installation and
the network connection used to install its wheel. It needs no GPU or paid plan.
Colab may require Google sign-in and applies its own availability and usage
limits. Jupyter supplies the notebook display tools; these are not Fullbleed
package dependencies. Download the results before a hosted runtime expires.

See the [component guide](https://docs.fullbleed.dev/guides/bootstrap-components-preview/)
for font setup, class names, named parts and HTML export behaviour. Bootstrap
components are static in both outputs; the exports contain no Bootstrap JavaScript.

To run the repository's checks with Python 3.11 or later:

```sh
python -m pip install -r tools/component-notebook-requirements.txt
python tools/verify_component_notebook.py --channel alpha5 --check-downloads --out target/component-notebook
```

The verifier executes the actual notebook and changes its input cells for edited,
long and empty orders. It checks independent PDF text/bounds/colours, exported HTML,
repeat rendering and exact ZIP contents. It also checks a short rerun after the
long order, so old preview files cannot enter the new download. These Jupyter
checks do not test the hosted Colab runtime or its download UI.

The notebook is MIT licensed; see [LICENSE](LICENSE).

The item column returns `Strong(...)` components. The archived alpha 3 notebook and downloads remain available in `examples/component-notebook` and `docs/assets/component-notebook`.
