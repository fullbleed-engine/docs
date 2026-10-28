"""Execute the actual ZIP, edited data and all C# component-guide snippets in fresh NuGet consumers."""
from hashlib import sha256
from importlib.metadata import version as library_version
from pathlib import Path
import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
import zipfile

from PIL import Image
from pypdf import PdfReader
from pypdf.generic import ContentStream
import pypdfium2 as pdfium

ROOT = Path(__file__).resolve().parents[1]


def inspect_pdf(path, expected, pages):
    reader = PdfReader(path, strict=True)
    assert len(reader.pages) == pages, (path, len(reader.pages), pages)
    text = '\n'.join(page.extract_text() for page in reader.pages)
    compact = lambda value: ''.join(value.split())
    for needle in expected:
        assert compact(needle) in compact(text), (path, needle)
    colors = []; sizes = []; independent = []; bounds = []; pixels = []
    for page in reader.pages:
        for operands, operation in ContentStream(page.get_contents(), reader).operations:
            if operation in (b'rg', b'RG'):
                colors.append(tuple(map(float, operands)))
            if operation == b'Tf':
                sizes.append(float(operands[1]))
    with pdfium.PdfDocument(path) as document:
        for number, page in enumerate(document, 1):
            textpage = page.get_textpage()
            try:
                independent.append(textpage.get_text_range())
                width, height = page.get_size()
                for index in range(textpage.count_chars()):
                    if not textpage.get_text_range(index, 1).strip():
                        continue
                    left, bottom, right, top = textpage.get_charbox(index)
                    assert -1 <= left <= right <= width + 1 and -1 <= bottom <= top <= height + 1, (path, number)
                    bounds.append([number, *[round(v, 3) for v in (left, bottom, right, top)]])
                bitmap = page.render(scale=96/72)
                try:
                    image = bitmap.to_pil().convert('RGB')
                    pixels.append(sha256(image.tobytes()).hexdigest())
                    image.save(path.with_name(f'{path.stem}-pdfium-{number}.png'))
                finally:
                    bitmap.close()
            finally:
                textpage.close()
                page.close()
    for needle in expected:
        assert compact(needle) in compact(''.join(independent)), (path, 'PDFium', needle)
    return {'pdfSha256': sha256(path.read_bytes()).hexdigest(), 'pages': pages, 'text': text,
            'pdfiumText': independent, 'pdfiumPixelsSha256': pixels,
            'glyphBoundsSha256': sha256(json.dumps(bounds).encode()).hexdigest(),
            'colors': sorted(set(colors)), 'fontSizes': sorted(set(sizes))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets', type=Path, default=ROOT/'docs/assets/dotnet-components')
    parser.add_argument('--package-source', default='https://api.nuget.org/v3/index.json')
    parser.add_argument('--out', type=Path, default=ROOT/'output/dotnet-components-verification')
    parser.add_argument('--refresh-assets', action='store_true')
    args = parser.parse_args()
    out = args.out.resolve(); out.mkdir(parents=True, exist_ok=False)
    assets = args.assets.resolve()
    manifest = json.loads((assets/'source.json').read_text())
    package_version = manifest['packageVersion']
    assert package_version == '0.2.4' and manifest['engineVersion'] == '2.5.40'
    archive_path = assets/'project.zip'
    assert sha256(archive_path.read_bytes()).hexdigest() == manifest['zipSha256']
    workspace = Path(tempfile.mkdtemp(prefix='fullbleed-csharp-download-')).resolve()
    (out/'workspace.json').write_text(json.dumps({'workspace':str(workspace)})+'\n')
    with zipfile.ZipFile(archive_path) as archive:
        expected = {'fullbleed-csharp-components/'+r['path'] for r in manifest['files']}
        assert set(archive.namelist()) == expected and len(archive.namelist()) == len(expected)
        for record in manifest['files']:
            name = 'fullbleed-csharp-components/'+record['path']
            target = (workspace/name).resolve()
            assert target.is_relative_to(workspace)
            data = archive.read(name)
            assert len(data) == record['bytes'] and sha256(data).hexdigest() == record['sha256']
            target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)
    project = workspace/'fullbleed-csharp-components'
    upstream = json.loads((project/'upstream.json').read_text())
    for record in upstream['files']:
        assert sha256((project/record['path']).read_bytes()).hexdigest() == record['sha256']
    env = {**os.environ, 'NUGET_PACKAGES':str(workspace/'packages'),
           'NUGET_HTTP_CACHE_PATH':str(workspace/'nuget-http-cache'), 'DOTNET_CLI_TELEMETRY_OPTOUT':'1',
           'DOTNET_CLI_WORKLOAD_UPDATE_NOTIFY_DISABLE':'true'}
    env.pop('FULLBLEED_NATIVE_LIBRARY', None)
    commands = []

    def run(label, command, cwd=project):
        result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True, encoding='utf-8', timeout=300)
        (out/(label+'.log')).write_text(result.stdout+result.stderr, encoding='utf-8')
        assert result.returncode == 0, (label, (result.stdout+result.stderr)[-2500:])
        commands.append({'name':label,'exitCode':0})
        return result.stdout

    run('restore-download', ['dotnet','restore','--locked-mode','--source',args.package_source])
    run('run-exact-download', ['dotnet','run','-c','Release','--no-restore','--',str(out/'invoice')])
    sample = inspect_pdf(out/'invoice/invoice.pdf', ['Maple & Finch','$1,870.00','TOTAL DUE'], 1)
    diagnostics = json.loads((out/'invoice/diagnostics.json').read_text())
    assert diagnostics['MissingGlyphs'] == []
    preview = out/'invoice/invoice_page1.png'
    with Image.open(preview) as image:
        assert image.width > 700 and image.height > 1000
        assert any(low != high for low, high in image.convert('RGB').getextrema())
    for generated, published in [('invoice.pdf','invoice.pdf'),('invoice_page1.png','page-1.png')]:
        data=(out/'invoice'/generated).read_bytes()
        if args.refresh_assets:
            (assets/published).write_bytes(data)
        else:
            assert sha256(data).hexdigest() == manifest['outputs'][published], published
            assert data == (assets/published).read_bytes(), published

    # The exact downloaded program ran above; now exercise edits using its original component methods.
    variants = '''using System.Text.Json;
using FullBleed.ComponentInvoice;
using FullBleed.DotNet;
var output = args[0];
Directory.CreateDirectory(output);
var example = InvoiceDocument.Example;
using var engine = new FullBleedEngine(new FullBleedEngineOptions {
    Assets = Directory.GetFiles(Path.Combine(AppContext.BaseDirectory, "Assets/fonts"), "*.ttf")
        .Order(StringComparer.Ordinal).Select(path => FullBleedAsset.FromPath(path, FullBleedAssetKind.Font)).ToList(),
});
var cases = new Dictionary<string, Invoice> {
    ["paid"] = example with { Paid = true, Accent = "#245541" },
    ["empty"] = example with { Items = [] },
    ["credit"] = example with { Items = [new("Project credit", "A credit against the original project.", 1, -50)] },
    ["escaped"] = example with { Customer = "A & <Client> \\"Café\\"" },
    ["many"] = example with { Items = Enumerable.Range(1, 40).Select(i => new InvoiceItem($"Deliverable {i:00}", "A documented unit of work, ready for handoff.", 1, 25)).ToArray() },
};
foreach (var entry in cases) {
    var document = InvoiceDocument.Create(entry.Value);
    var result = document.RenderPdfWithDiagnostics(engine);
    if (result.Diagnostics.MissingGlyphs.Count != 0) throw new Exception("Missing glyph");
    File.WriteAllBytes(Path.Combine(output, entry.Key + ".pdf"), result.Pdf);
}
File.WriteAllText(Path.Combine(output, "runtime.json"), JsonSerializer.Serialize(new {
    Framework = Environment.Version.ToString(), Features = FullBleedEngine.GetNativeFeatures()
}));
'''
    (project/'Program.cs').write_text(variants, encoding='utf-8')
    run('run-edited-data', ['dotnet','run','-c','Release','--no-restore','--',str(out/'variants')])
    cases = {'invoice': sample}
    for name, expected, pages in [('paid',['PAID IN FULL','TOTAL PAID','$1,870.00'],1),
                                  ('empty',['No billable items.','$0.00'],1),
                                  ('credit',['Project credit','-$50.00'],1),
                                  ('escaped',['A & <Client> "Café"'],1),
                                  ('many',['Deliverable 01','Deliverable 40','$1,000.00'],4)]:
        cases[name]=inspect_pdf(out/'variants'/(name+'.pdf'),expected,pages)
    assert re.findall(r'Deliverable(\d{2})',''.join(cases['many']['text'].split())) == [f'{n:02}' for n in range(1,41)]
    runtime=json.loads((out/'variants/runtime.json').read_text())
    assert runtime['Framework'].startswith('10.0.')
    assert runtime['Features']['BindingVersion']==package_version

    guide=(ROOT/'docs/guides/csharp-components.md').read_text(encoding='utf-8')
    blocks=re.findall(r'```csharp\n(.*?)```',guide,re.S)
    assert len(blocks)==6
    actual='\n'.join(blocks)+'''
payment.RenderPdfToFile(engine, "output/payment.pdf");
styledNotice.RenderPdfToFile(engine, "output/notice.pdf");
'''
    (project/'Program.cs').write_text(actual,encoding='utf-8')
    (out/'guide.cs').write_text(actual,encoding='utf-8')
    run('run-guide', ['dotnet','run','-c','Release','--no-restore'])
    shutil.copytree(project/'output',out/'guide')
    guide_cases={}
    for name, expected, pages in [('invoice',['Made for Maple & Finch','Design: $120.00','Review: $40.00'],1),
                                  ('payment',['Paid in full'],1),('notice',['Payment','Paid in full'],1),
                                  ('batch',['Payment','Paid in full'],2)]:
        guide_cases[name]=inspect_pdf(out/'guide'/(name+'.pdf'),expected,pages)
    def has_color(case,color):
        return any(max(abs(a-b) for a,b in zip(value,color))<.003 for value in case['colors'])
    assert 18 in guide_cases['payment']['fontSizes'] and has_color(guide_cases['payment'],(49/255,93/255,155/255))
    assert 14 in guide_cases['notice']['fontSizes'] and has_color(guide_cases['notice'],(166/255,66/255,50/255))
    quickstart = (ROOT/'docs/getting-started/dotnet.md').read_text(encoding='utf-8')
    font_section = quickstart.split('## Register fonts and inspect the result\n', 1)[1].split('\n## ', 1)[0]
    font_blocks = re.findall(r'```csharp\n(.*?)```', font_section, re.S)
    assert len(font_blocks) == 1
    font_block = font_blocks[0]
    (project/'Program.cs').write_text(font_block, encoding='utf-8')
    (out/'register-fonts.cs').write_text(font_block, encoding='utf-8')
    run('run-font-guide', ['dotnet','run','-c','Release','--no-restore'])
    shutil.copyfile(project/'output/invoice.pdf', out/'register-fonts.pdf')
    shutil.copyfile(project/'output/preview/invoice_page1.png', out/'register-fonts.png')
    font_case = inspect_pdf(out/'register-fonts.pdf', ['Maple & Finch','$1,870.00'], 1)
    assert font_case['pdfSha256'] == sample['pdfSha256']
    assert (out/'register-fonts.png').read_bytes() == preview.read_bytes()
    installed=workspace/'packages/fullbleed.dotnet'/package_version
    provenance=json.loads((installed/'native-provenance.json').read_text())
    engine=next(dep['version'] for dep in provenance['dependencies'] if dep['name']=='fullbleed')
    assert engine==manifest['engineVersion']
    report={'ok':True,'packageVersion':package_version,'engineVersion':engine,'runtime':runtime,
            'workspace':str(workspace),'freshNuGetCache':True,'nativeLibraryOverride':False,
            'packageSource':args.package_source,
            'packageSha256':sha256((installed/f'fullbleed.dotnet.{package_version}.nupkg').read_bytes()).hexdigest(),
            'zipSha256':manifest['zipSha256'],'upstreamCommit':upstream['commit'],
            'commands':commands,'cases':cases,'guideCases':guide_cases,'guideBlocks':len(blocks),
            'fontGuideMatchesSample':True,
            'previewSha256':sha256(preview.read_bytes()).hexdigest(),
            'readers':{name:library_version(name) for name in ('pypdf','pypdfium2','pillow')},
            'scope':'Exact downloaded source, five data edits and six actual guide blocks; text, page counts, glyph bounds, style colors and sizes, and native invoice preview. No complete language parity claim.'}
    (out/'verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'ok':True,'package':package_version,'cases':len(cases),'guideBlocks':len(blocks)}))


if __name__=='__main__':
    main()
