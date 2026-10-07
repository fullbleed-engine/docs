"""Pinned, maintainer-only veraPDF checks for downloadable PDF specimens."""
from hashlib import sha256
import io
import json
from pathlib import Path
import subprocess
from urllib.request import urlopen
import zipfile

URL = 'https://software.verapdf.org/rel/1.30/verapdf-greenfield-1.30.2-installer.zip'
INSTALLER_SHA256 = '6cc6341cb1af644044054b81f00a6590a7918abb18f762243de115258bcad838'


def validator(cache):
    cache.mkdir(parents=True, exist_ok=True)
    installer = cache / 'verapdf-1.30.2.zip'
    if not installer.exists():
        with urlopen(URL, timeout=120) as response:
            data = response.read()
        assert sha256(data).hexdigest() == INSTALLER_SHA256
        installer.write_bytes(data)
    assert sha256(installer.read_bytes()).hexdigest() == INSTALLER_SHA256
    classes = cache / 'classes'
    if not (classes / 'org/verapdf/apps/GreenfieldCliWrapper.class').is_file():
        with zipfile.ZipFile(installer) as archive:
            jars = [name for name in archive.namelist() if name.endswith('.jar')]
            assert len(jars) == 1
            jar_bytes = archive.read(jars[0])
        with zipfile.ZipFile(io.BytesIO(jar_bytes)) as jar:
            packs = [name for name in jar.namelist() if name.endswith('pack-veraPDF CLI')]
            assert len(packs) == 1
            pack_bytes = jar.read(packs[0])
        with zipfile.ZipFile(io.BytesIO(pack_bytes)) as pack:
            for info in pack.infolist():
                assert (classes / info.filename).resolve().is_relative_to(classes.resolve())
            pack.extractall(classes)
    return classes


def check(pdf, profile, classpath, out):
    pdf = Path(pdf).resolve()
    classpath = Path(classpath).resolve()
    out.mkdir(parents=True, exist_ok=True)
    version = subprocess.check_output(['java', '-cp', str(classpath), 'org.verapdf.apps.GreenfieldCliWrapper', '--version'], text=True)
    assert version.startswith('veraPDF 1.30.2\n'), version
    with (out / 'verapdf.json').open('w', encoding='utf-8') as stdout, (out / 'verapdf.stderr.txt').open('w', encoding='utf-8') as stderr:
        result = subprocess.run(['java', '-cp', str(classpath), 'org.verapdf.apps.GreenfieldCliWrapper',
            '--format', 'json', '--maxfailuresdisplayed', '-1', '-f', profile, pdf.name],
            cwd=pdf.parent, stdout=stdout, stderr=stderr, timeout=120)
    report = json.loads((out / 'verapdf.json').read_text(encoding='utf-8'))['report']['jobs'][0]['validationResult'][0]
    assert result.returncode == 0 and report['jobEndStatus'] == 'normal'
    assert report['compliant'] and report['details']['failedChecks'] == 0
    return {'version': '1.30.2', 'profile': profile, 'failedChecks': 0,
            'installerUrl': URL, 'installerSha256': INSTALLER_SHA256}
