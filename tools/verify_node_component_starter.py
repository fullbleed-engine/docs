"""Install and run the actual published component download, including guide snippets."""
from hashlib import sha256
from pathlib import Path
import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
import zipfile

from pypdf import PdfReader
from component_style_checks import JAVASCRIPT_RENDER, inspect_style_pdfs, styling_blocks

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'docs/assets/node-components'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--node', default=shutil.which('node'))
    parser.add_argument('--out', type=Path, default=ROOT / 'target/node-component-starter')
    args = parser.parse_args()
    node = Path(args.node).resolve()
    npm = next(path for path in [node.parent / 'node_modules/npm/bin/npm-cli.js',
        node.parent.parent / 'lib/node_modules/npm/bin/npm-cli.js'] if path.is_file())
    out = args.out.resolve(); out.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, 'PATH': str(node.parent) + os.pathsep + os.environ['PATH']}
    manifest = json.loads((ASSETS / 'source.json').read_text(encoding='utf-8'))
    assert manifest['package'] == 'fullbleed@0.8.1'
    assert sha256((ASSETS / 'project.zip').read_bytes()).hexdigest() == manifest['zip_sha256']
    records = []
    with tempfile.TemporaryDirectory(prefix='component consumer with spaces ', dir=out) as temporary:
        project = Path(temporary)
        with zipfile.ZipFile(ASSETS / 'project.zip') as archive:
            assert set(archive.namelist()) == {'fullbleed-node-components/' + row['path'] for row in manifest['files']}
            for row in manifest['files']:
                assert Path(row['path']).name == row['path']
                data = archive.read('fullbleed-node-components/' + row['path'])
                assert sha256(data).hexdigest() == row['sha256'] and len(data) == row['bytes']
                (project / row['path']).write_bytes(data)

        def run(name, command, cwd=project):
            result = subprocess.run([str(node), *map(str, command)], cwd=cwd, env=env,
                capture_output=True, text=True, encoding='utf-8', timeout=180)
            (out / (name + '.log')).write_text(result.stdout + result.stderr, encoding='utf-8')
            assert result.returncode == 0, (name, result.stdout + result.stderr)

        run('install', [npm, 'ci', '--ignore-scripts', '--no-audit', '--no-fund'])
        installed = json.loads((project / 'node_modules/fullbleed/package.json').read_text(encoding='utf-8'))
        assert installed['version'] == '0.8.1' and installed['fullbleed']['engineVersion'] == '2.5.35'
        run('types', [npm, 'run', 'check'])
        for command in ['pdf', 'pdf:tsx']:
            run(command.replace(':', '-'), [npm, 'run', command])
        for variant in ['functions', 'tsx']:
            source = project / 'output' / variant
            destination = out / variant
            destination.mkdir(exist_ok=True)
            for name in ['invoice.pdf', 'page-1.png', 'invoice.html', 'invoice.css', 'verification.json']:
                shutil.copy2(source / name, destination / name)
            for name, public in [('invoice.pdf', 'invoice.pdf'), ('page-1.png', 'page-1.png')]:
                assert (source / name).read_bytes() == (ASSETS / public).read_bytes(), (variant, name)
            receipt = json.loads((source / 'verification.json').read_text(encoding='utf-8'))
            assert receipt['ok'] and receipt['pages'] == 1 and receipt['missingGlyphs'] == 0 and receipt['repeated_pdf_equal']
            text = PdfReader(source / 'invoice.pdf').pages[0].extract_text()
            assert all(value in text for value in ['Maple & Finch', '$8,100.00', 'Discovery & direction'])
            records.append({'variant': variant, 'pdf_sha256': sha256((source / 'invoice.pdf').read_bytes()).hexdigest(), 'text_verified': True})
        guide = (ROOT / 'docs/guides/javascript-components.md').read_text(encoding='utf-8')
        snippets = [('functions', re.findall(r'```javascript\n(.*?)```', guide, re.S)[0], 'mjs'),
                    ('tsx', re.findall(r'```tsx\n(.*?)```', guide, re.S)[0], 'tsx')]
        for name, code, extension in snippets:
            destination = out / ('guide-' + name); destination.mkdir(exist_ok=True)
            if name == 'tsx':
                code += "\nawait (await import('node:fs/promises')).writeFile('invoice.pdf', result.pdf);\n"
            script = project / ('guide.' + extension)
            script.write_text(code, encoding='utf-8')
            if extension == 'tsx':
                compiled = project / 'guide-tsx.mjs'
                run('compile-guide', [project / 'node_modules/esbuild/bin/esbuild', script,
                    '--bundle', '--packages=external', '--platform=node', '--format=esm', '--jsx=automatic', '--outfile=' + str(compiled)])
                script = compiled
            run('guide-' + name, [script], destination)
            reader = PdfReader(destination / 'invoice.pdf')
            assert len(reader.pages) == 1
            extracted = reader.pages[0].extract_text()
            # Per-glyph positioning for letter-spacing can produce extra reader
            # whitespace. Keep the raw extraction and compare all authored glyphs.
            compact = ''.join(extracted.split())
            assert all(''.join(value.split()) in compact for value in ['Maple & Finch', 'Design', '$120.00'])
            records.append({'guide': name, 'source_sha256': sha256(code.encode()).hexdigest(),
                'pdf_sha256': sha256((destination / 'invoice.pdf').read_bytes()).hexdigest(), 'text_verified': True,
                'extracted_text': extracted, 'whitespace_normalized_checks': True})
        style_source = '\n'.join(styling_blocks(guide, 'tsx'))
        style_module = project / 'guide-styles.tsx'
        style_module.write_text(style_source + '\nexport { payment, styledNotice };\n', encoding='utf-8')
        run('style-types', [project / 'node_modules/typescript/bin/tsc', '--ignoreConfig', '--noEmit', '--strict',
            '--target', 'ES2022', '--module', 'NodeNext', '--moduleResolution', 'NodeNext',
            '--jsx', 'react-jsx', '--skipLibCheck', style_module])
        script = project / 'guide-styles-render.tsx'
        script.write_text(style_source + JAVASCRIPT_RENDER, encoding='utf-8')
        compiled = project / 'guide-styles-render.mjs'
        run('compile-style-guide', [project / 'node_modules/esbuild/bin/esbuild', script,
            '--bundle', '--packages=external', '--platform=node', '--format=esm', '--jsx=automatic', '--outfile=' + str(compiled)])
        destination = out / 'guide-styles'; destination.mkdir(exist_ok=True)
        run('guide-styles', [compiled], destination)
        style_report = inspect_style_pdfs(destination)

        # Execute the exact downloadable guide example, then feed its complete
        # styled HTML back into the public engine with an empty CSS argument.
        export_section = guide.split('## Export HTML with or without styles\n', 1)[1]
        export_code = re.findall(r'```javascript\n(.*?)```', export_section, re.S)[0]
        export_module = project / 'guide-export.mjs'
        export_module.write_text(export_code + '\nexport { report, styledFragment };\n', encoding='utf-8')
        destination = out / 'guide-export'; destination.mkdir(exist_ok=True)
        run('guide-export', [export_module], destination)
        render_script = project / 'guide-export-render.mjs'
        render_script.write_text("""import assert from 'node:assert/strict';
import { readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { renderPdf } from 'fullbleed';
import { report, styledFragment } from './guide-export.mjs';
const html = await readFile('report.html', 'utf8');
const unstyled = await readFile('report-unstyled.html', 'utf8');
assert.equal(html, report.toHtml({ includeStyles: true }));
assert.equal(unstyled, report.toHtml({ includeStyles: false }));
assert.match(html, /<style>/);
assert.match(html, /\\.amount/);
assert.match(html, /#175c52/);
assert.match(unstyled, /class=\"amount\"/);
assert.doesNotMatch(unstyled, /<style\\b|\\sstyle=/i);
assert.doesNotMatch(html + unstyled, /<script\\b/i);
assert.match(styledFragment, /<style>/);
assert.match(styledFragment, /Northstar Studio/);
await writeFile('fragment.html', styledFragment);
const options = { defaultStyles: false, previewDpi: 96 };
const direct = await report.renderPdf(renderPdf, options);
const embedded = await renderPdf({ ...options, html, css: '' });
assert.equal(direct.pages, 1);
assert.equal(embedded.pages, direct.pages);
assert.equal(direct.missingGlyphs, 0);
assert.equal(embedded.missingGlyphs, 0);
assert.deepEqual(embedded.pdf, direct.pdf);
assert.deepEqual(embedded.previews, direct.previews);
await writeFile('report.pdf', embedded.pdf);
await writeFile('page-1.png', embedded.previews[0]);
const digest = data => createHash('sha256').update(data).digest('hex');
await writeFile('verification.json', JSON.stringify({
  ok: true, pages: embedded.pages, embeddedStylesPdfAndPreviewsEqual: true,
  styledHtml: digest(html), unstyledHtml: digest(unstyled),
  fragmentHtml: digest(styledFragment), pdf: digest(embedded.pdf),
  previews: embedded.previews.map(digest),
}, null, 2) + '\\n');
""", encoding='utf-8')
        run('guide-export-render', [render_script], destination)
        export_pdf = PdfReader(destination / 'report.pdf')
        assert len(export_pdf.pages) == 1
        export_text = ''.join(export_pdf.pages[0].extract_text().split())
        assert all(''.join(text.split()) in export_text for text in
                   ('Account summary', 'Northstar Studio', 'USD 1,200.00'))
        embedded_export_report = json.loads((destination / 'verification.json').read_text(encoding='utf-8'))
        assert embedded_export_report['ok'] and embedded_export_report['embeddedStylesPdfAndPreviewsEqual']
        embedded_export_report['guide_source_sha256'] = sha256(export_code.encode()).hexdigest()
        embedded_export_report['independent_text_verified'] = True
    report = {'ok': True, 'package': manifest['package'], 'engine': manifest['engine'],
              'zip_sha256': manifest['zip_sha256'], 'published_pdf_png_equal': True,
              'records': records, 'class_styling': style_report,
              'html_export': embedded_export_report}
    (out / 'verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
