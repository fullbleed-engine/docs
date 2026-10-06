"""Fetch a pinned font and prepare its static regular face once, before rendering."""
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path
from urllib.request import urlopen
import json

ROOT = Path(__file__).resolve().parent


def matches(path, spec):
    return (path.is_file() and path.stat().st_size == spec['bytes']
            and sha256(path.read_bytes()).hexdigest() == spec['sha256'])


def prepare():
    source = json.loads((ROOT / 'font-source.json').read_text(encoding='utf-8'))
    directory = ROOT / 'fonts'
    directory.mkdir(exist_ok=True)
    license_path = directory / 'OFL.txt'
    if sha256(license_path.read_bytes()).hexdigest() != source['license_sha256']:
        raise SystemExit('The bundled font license does not match the pinned source.')
    output = directory / source['output']['file']
    if matches(output, source['output']):
        print('Regular font already prepared and verified.')
        return output
    if version('fonttools') != source['preparation']['version']:
        raise SystemExit('Install the pinned requirements-fonts.txt before preparing fonts.')
    from fontTools.ttLib import TTFont
    from fontTools.varLib.instancer import instantiateVariableFont

    cache = directory / 'source'
    cache.mkdir(exist_ok=True)
    downloaded = cache / 'NotoSansSC-variable.ttf'
    if not matches(downloaded, source):
        print('Downloading Noto Sans SC (17.8 MB) from the pinned Google Fonts commit...', flush=True)
        with urlopen(source['url'], timeout=60) as response:
            data = response.read(source['bytes'] + 1)
        if len(data) != source['bytes'] or sha256(data).hexdigest() != source['sha256']:
            raise SystemExit('Font download size or SHA-256 does not match the pinned source.')
        downloaded.write_bytes(data)
    print('Preparing the regular (400) face; this can take about a minute...', flush=True)
    font = TTFont(downloaded, recalcTimestamp=False)
    instance = instantiateVariableFont(font, {'wght': 400}, inplace=True, updateFontNames=True)
    temporary = directory / 'NotoSansSC-Regular.prepared.ttf'
    try:
        instance.save(temporary)
        instance.close()
        if not matches(temporary, source['output']):
            raise SystemExit('Prepared font differs from the verified static face.')
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
    print('Regular font prepared; its complete character repertoire is retained.')
    return output


if __name__ == '__main__':
    prepare()
