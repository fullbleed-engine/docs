"""Execute the exact source ZIP and compare its PDF with the validated specimen."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'docs/assets/accessible-showcase'

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=ROOT/'target/accessible-showcase')
    args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((ASSETS/'source.json').read_text(encoding='utf-8'))
    archive=ASSETS/'project.zip'
    assert sha256(archive.read_bytes()).hexdigest()==manifest['zip_sha256']
    project=out/'fullbleed-accessible-showcase'
    with ZipFile(archive) as package:
        expected={'fullbleed-accessible-showcase/'+name for name in manifest['package_files']}
        assert set(package.namelist())==expected
        for name,digest in manifest['package_files'].items():
            data=package.read('fullbleed-accessible-showcase/'+name)
            assert sha256(data).hexdigest()==digest,name
            path=(project/name).resolve()
            assert path.is_relative_to(project.resolve())
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    output=out/'rendered'
    for script in ('render.py','verify.py'):
        subprocess.run([sys.executable,str(project/script),'--out',str(output)],cwd=project,check=True)
    actual=sha256((output/'common-ground-guide.pdf').read_bytes()).hexdigest()
    validated=json.loads((ASSETS/'validation.json').read_text(encoding='utf-8'))
    assert validated['external_validation']['compliant']
    assert actual==validated['pdf_sha256']==sha256((ASSETS/'common-ground-guide.pdf').read_bytes()).hexdigest()
    report={'ok':True,'source_files':len(manifest['source_files']),'pdf_sha256':actual,
            'matches_externally_validated_pdf':True,'external_validator_rerun':False}
    (out/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))

if __name__=='__main__':
    main()
