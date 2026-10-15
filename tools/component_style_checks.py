"""Verify class selectors and inline overrides in actual guide-generated PDFs."""
from hashlib import sha256
from pathlib import Path
import json
import re

from pypdf import PdfReader
from pypdf.generic import ContentStream


def styling_blocks(source, language):
    section = source.split('## Class names and styles\n', 1)[1].split('\n## ', 1)[0]
    blocks = re.findall(r'```' + language + r'\n(.*?)```', section, re.S)
    assert len(blocks) == 2
    return blocks


def inspect_style_pdfs(folder):
    folder = Path(folder)
    blue = (49 / 255, 93 / 255, 155 / 255)
    rust = (166 / 255, 66 / 255, 50 / 255)
    green = (36 / 255, 85 / 255, 65 / 255)
    records = {}
    for name in ['payment', 'payment-no-classes', 'notice', 'notice-no-classes', 'notice-no-inline']:
        path = folder / (name + '.pdf')
        reader = PdfReader(path)
        assert len(reader.pages) == 1, name
        page = reader.pages[0]
        text = ''.join(page.extract_text().split())
        assert 'Paidinfull' in text, (name, text)
        colors = []
        sizes = []
        for arguments, operation in ContentStream(page.get_contents(), reader).operations:
            if operation in [b'rg', b'RG']:
                colors.append(tuple(float(value) for value in arguments))
            if operation == b'Tf':
                sizes.append(float(arguments[1]))
        def has_color(expected):
            return any(len(color) == 3 and max(abs(a-b) for a,b in zip(color, expected)) < .003 for color in colors)
        def has_size(expected):
            return any(abs(size - expected) < .01 for size in sizes)
        if name == 'payment':
            assert has_color(blue) and has_size(18), (name, colors, sizes)
        if name == 'payment-no-classes':
            assert not has_color(blue) and not has_size(18), (name, colors, sizes)
        if name == 'notice':
            assert has_color(blue) and has_color(rust) and not has_color(green) and has_size(14), (name, colors, sizes)
        if name == 'notice-no-classes':
            assert not has_color(blue) and has_color(rust) and not has_size(14), (name, colors, sizes)
        if name == 'notice-no-inline':
            assert has_color(blue) and has_color(green) and not has_color(rust), (name, colors)
        records[name] = {'pdf_sha256': sha256(path.read_bytes()).hexdigest(), 'pages': 1,
            'text': text, 'rgb_colors': sorted(set(colors)), 'font_sizes': sorted(set(sizes))}
    for name in ['payment', 'notice']:
        assert (folder / (name + '.png')).read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
    result = {'ok': True, 'records': records, 'class_selectors_verified': True,
        'descendant_selector_verified': True, 'inline_border_override_verified': True,
        'controls_remove_classes_or_inline_style': True}
    (folder / 'verification.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    return result


PYTHON_RENDER = r'''
from importlib.resources import files
from pathlib import Path
import re
import fullbleed

engine = fullbleed.PdfEngine(font_files=[str(files('fullbleed_assets').joinpath('fonts/Inter-Variable.ttf'))])
for name, artifact in [('payment', Payment()), ('notice', StyledNotice())]:
    html, css = artifact.to_html(), artifact.to_css()
    Path(name + '.html').write_text(html, encoding='utf-8')
    Path(name + '.css').write_text(css, encoding='utf-8')
    Path(name + '.pdf').write_bytes(artifact.render_pdf(engine))
    Path(name + '.png').write_bytes(artifact.render_image_pages(engine, dpi=96)[0])
    def remove_classes(match):
        classes = [value for value in match[1].split() if value not in {'notice', 'is-paid', 'notice-title'}]
        return 'class="' + ' '.join(classes) + '"'
    control = re.sub(r'class="([^"]*)"', remove_classes, html)
    Path(name + '-no-classes.pdf').write_bytes(engine.render_pdf(control, css))
    if name == 'notice':
        assert 'ui-card notice is-paid' in html and 'border-color: #a64232' in html
        control = html.replace(' style="border-color: #a64232;"', '')
        assert control != html
        Path('notice-no-inline.pdf').write_bytes(engine.render_pdf(control, css))
'''


JAVASCRIPT_RENDER = r'''
import { writeFile } from 'node:fs/promises';
import { renderPdf } from 'fullbleed';
import { renderDocument } from 'fullbleed/ui';

for (const [name, artifact] of [['payment', payment], ['notice', styledNotice]]) {
  let input;
  const capture = async options => { input = options; return renderPdf(options); };
  const result = await renderDocument(artifact, capture, { previewDpi: 96 });
  await writeFile(name + '.html', input.html);
  await writeFile(name + '.css', input.css);
  await writeFile(name + '.pdf', result.pdf);
  await writeFile(name + '.png', result.previews[0]);
  const control = input.html.replace(/class="([^"]*)"/g, (_, names) =>
    'class="' + names.split(/\s+/).filter(value => !['notice', 'is-paid', 'notice-title'].includes(value)).join(' ') + '"');
  await writeFile(name + '-no-classes.pdf', (await renderPdf({ html: control, css: input.css })).pdf);
  if (name === 'notice') {
    if (!input.html.includes('ui-card notice is-paid') || !input.html.includes('border-color: #a64232')) throw Error('Missing forwarded styles');
    const withoutInline = input.html.replace(' style="border-color: #a64232;"', '');
    if (withoutInline === input.html) throw Error('Inline control did not change the input');
    await writeFile('notice-no-inline.pdf', (await renderPdf({ html: withoutInline, css: input.css })).pdf);
  }
}
'''
