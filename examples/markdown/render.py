"""Render Markdown and local images with an editable print stylesheet."""
from hashlib import sha256
from html import escape
from importlib.metadata import version
from importlib.resources import files
from pathlib import Path
from urllib.parse import unquote, urlsplit
import argparse
import json
import sys

import fullbleed
from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parent
MAX_SOURCE_BYTES = 4_000_000
MAX_IMAGE_BYTES = 16 * 1024 * 1024


def read_text(path):
    if path.stat().st_size > MAX_SOURCE_BYTES:
        raise ValueError(f'Input exceeds {MAX_SOURCE_BYTES:,} bytes: {path.name}')
    data = path.read_bytes()
    if len(data) > MAX_SOURCE_BYTES:
        raise ValueError(f'Input exceeds {MAX_SOURCE_BYTES:,} bytes: {path.name}')
    return data.decode('utf-8-sig')


def markdown_html(source, directory):
    """Resolve only Markdown images beneath the document's own directory."""
    parser = MarkdownIt('js-default', {'linkify': False})
    tokens = parser.parse(source)
    bundle = fullbleed.AssetBundle()
    images = {}
    total_bytes = 0

    def visit(items):
        nonlocal total_bytes
        for token in items:
            if token.type == 'image':
                reference = token.attrGet('src') or ''
                url = urlsplit(reference)
                decoded = unquote(url.path)
                if url.scheme or url.netloc or url.query or url.fragment or '\\' in decoded:
                    raise ValueError(f'Use a local image path beneath the Markdown directory: {reference}')
                relative = Path(decoded)
                if relative.is_absolute() or relative.anchor or not decoded:
                    raise ValueError(f'Use a relative image path: {reference}')
                path = (directory / relative).resolve()
                if not path.is_relative_to(directory):
                    raise ValueError(f'Image is outside the Markdown directory: {reference}')
                if not path.is_file():
                    raise ValueError(f'Image does not exist: {reference}')
                suffix = path.suffix.lower()
                if suffix not in {'.png', '.jpg', '.jpeg', '.svg'}:
                    raise ValueError(f'Use a PNG, JPEG, or SVG image: {reference}')
                if path not in images:
                    if total_bytes + path.stat().st_size > MAX_IMAGE_BYTES:
                        raise ValueError('Referenced images exceed the 16 MiB example limit.')
                    data = path.read_bytes()
                    total_bytes += len(data)
                    if total_bytes > MAX_IMAGE_BYTES:
                        raise ValueError('Referenced images exceed the 16 MiB example limit.')
                    alias = f'markdown-image-{len(images) + 1}{suffix}'
                    kind = fullbleed.AssetKind.Svg if suffix == '.svg' else fullbleed.AssetKind.Image
                    bundle.add_file(str(path), kind, name=alias)
                    images[path] = {'path': path.relative_to(directory).as_posix(), 'alias': alias,
                                    'bytes': len(data), 'sha256': sha256(data).hexdigest()}
                token.attrSet('src', images[path]['alias'])
            if token.children:
                visit(token.children)

    visit(tokens)
    body = parser.renderer.render(tokens, parser.options, {})
    return body, bundle, images


def render(input_path, out, stylesheet, title, extra_fonts, previews):
    input_path, stylesheet, out = input_path.resolve(), stylesheet.resolve(), out.resolve()
    source, css = read_text(input_path), read_text(stylesheet)
    if not source.strip():
        raise ValueError('The Markdown file is empty.')
    body, bundle, images = markdown_html(source, input_path.parent)
    mono_source = json.loads((ROOT / 'fonts/source.json').read_text(encoding='utf-8'))
    mono = ROOT / 'fonts/IBMPlexMono-Regular.ttf'
    expected_font = next(item for item in mono_source['files'] if item['path'] == mono.name)
    if sha256(mono.read_bytes()).hexdigest() != expected_font['sha256']:
        raise ValueError('The bundled IBM Plex Mono font changed; restore it from the original project ZIP.')
    inter = Path(str(files('fullbleed_assets').joinpath('fonts/Inter-Variable.ttf')))
    fonts = [inter, mono, *(path.resolve() for path in extra_fonts)]
    for path in fonts:
        if not path.is_file():
            raise ValueError(f'Font does not exist: {path}')
    inputs = {input_path, stylesheet, *images, *fonts, (ROOT / 'fonts/source.json').resolve()}
    outputs = {(out / name).resolve() for name in ['document.pdf', 'document.html', 'document.css', 'render.json', 'glyph-report.json']}
    if inputs & outputs:
        raise ValueError('Choose an output directory that will not overwrite an input file.')
    html = f'<!doctype html><html lang="en"><head><title>{escape(title)}</title></head><body><main>{body}</main></body></html>'
    engine = fullbleed.PdfEngine(font_files=[str(path) for path in fonts], document_title=title,
                                document_lang='en', svg_form_xobjects=True)
    engine.register_bundle(bundle)
    pdf, missing = engine.render_pdf_with_glyph_report(html, css)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'glyph-report.json').write_text(json.dumps(missing, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if missing:
        raise ValueError('Missing glyphs; no new PDF written. See glyph-report.json and supply a font with --font.')
    pdf_path = out / 'document.pdf'
    pdf_path.write_bytes(pdf)
    (out / 'document.html').write_text(html, encoding='utf-8')
    (out / 'document.css').write_text(css, encoding='utf-8')
    digest = sha256(pdf).hexdigest()
    preview_dir = out / ('preview-' + digest[:12])
    if previews:
        engine.render_finalized_pdf_image_pages_to_dir(str(pdf_path), str(preview_dir), 110, 'page')
    report = {'fullbleed': version('fullbleed'), 'markdown_it_py': version('markdown-it-py'),
              'input_sha256': sha256(source.encode()).hexdigest(), 'css_sha256': sha256(css.encode()).hexdigest(),
              'pdf_sha256': digest, 'pdf_bytes': len(pdf), 'missing_glyphs': missing,
              'fonts': [{'file': path.name, 'sha256': sha256(path.read_bytes()).hexdigest()} for path in fonts],
              'images': list(images.values()),
              'previews': [path.relative_to(out).as_posix() for path in sorted(preview_dir.glob('*.png'))] if previews else []}
    (out / 'render.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'pdf': str(pdf_path), **report}, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path, help='UTF-8 Markdown file')
    parser.add_argument('--out', type=Path, default=Path('output'), help='Output directory (default: output)')
    parser.add_argument('--css', type=Path, default=ROOT / 'print.css', help='Replacement print stylesheet')
    parser.add_argument('--title', default='Markdown document', help='PDF metadata title')
    parser.add_argument('--font', type=Path, action='append', default=[], help='Additional local TTF font; repeat as needed')
    parser.add_argument('--no-preview', action='store_true', help='Generate the PDF without PNG previews')
    args = parser.parse_args()
    try:
        render(args.input, args.out, args.css, args.title, args.font, not args.no_preview)
    except (ValueError, OSError) as error:
        print(f'Error: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
